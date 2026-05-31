"""Cairn — Resonance Valve: the turn-axis YIELD optimiser, as RUNNABLE code.

NOT a one-sided token cutter. The thing being optimised is YIELD = information value / effort.
Tokens are the cost side; information value is the goal. The valve must not kill a swell (lose
value) nor run into chatter (waste tokens) — both lower yield. Optimum = the crest of the swell.

Three ideas, combined (operator design, 31 May 2026):
  1. VALUE-WEIGHTED contribution — the close trigger watches the *value* of new contributions, not
     their *count*. One late high-value anchor (e.g. DISPATCH #005's NGI0 flag) keeps the flow alive;
     five marginal repeats do not. Volume ≠ value (the gong: few synced modes = a pure tone, beats
     many dispersed modes).
  3. DOUBLE GATE (adaptive w) — while value is still rising/flowing, w stretches (be patient, the
     swell is coming, don't kill it); once value flattens, w tightens (cut, stop burning). The
     patience window breathes with the value of the flow, it is not fixed.
  + VALUE-WEIGHTED R — R (which picks swell vs plateau at close) folds in accrued information value,
    not just convergence. High R = converged AND valuable. Low R = dispersed or worthless.

Versions kept for the iteration story / comparison:
  trigger="dR"    v1  — dR/dt flat (spec-literal; missed the convergence step-jump)
  trigger="new"   v2.1 — new-contribution-count flat + bounded warmup (volume-blind to value)
  trigger="value" v3  — value-weighted R + value trigger + double-gate adaptive w  (DEFAULT)

Run: python3 resonance_valve.py
"""
from dataclasses import dataclass, field
from typing import Optional

EPS = 0.02            # dR/dt <= EPS counts as "flat" (v1)
EPS_VAL = 0.5         # contribution value <= EPS_VAL counts as "no valuable flow" (v3)
W = 2                 # base patience window
R_HIGH = 0.55         # at-close R above this = SWELL, below = PLATEAU
VALUE_FULL = 5.0      # cumulative value considered "enough information accrued" (R normaliser)
WARMUP_LIMIT = 3      # max turns to wait for first contribution before declaring no-traction

# Real measured per-turn cost, from DISPATCH #004 (`_dispatch_004_benchmark.md`):
# 9,014,101 billable input tokens / 129 turns. Used as the counterfactual token unit so the
# saving is grounded in a real run, not invented. (Our own swarm is low-chatter, so the
# *long baseline* turn-count is synthetic — a sprawling valve-less session — while the
# token-per-turn is measured. Honest hybrid; see RESONANCE_VALVE_PROOF2.md.)
MEASURED_BILLABLE_INPUT_PER_TURN = 9_014_101 / 129  # ≈ 69,876


@dataclass
class TurnObs:
    """One Senior audit turn, as read from the blackboard."""
    label: str
    active_workers: int
    anchored_workers: int   # how many converged on the common anchor this turn
    new_unique: int         # count of new verified entries this turn (v2.1 signal)
    value: float = 0.0      # VALUE-weight of this turn's new contributions (v3 signal).
                            # 0 = chatter/repeat; high = a high-value find / convergence anchor.

    @property
    def anchor_overlap(self) -> float:
        return self.anchored_workers / self.active_workers if self.active_workers else 0.0

    @property
    def semantic_closeness(self) -> float:
        return 1.0 / (1.0 + self.new_unique)


def compute_R(obs: TurnObs, cum_value: float = 0.0, value_weighted: bool = True) -> float:
    """value_weighted (v3): R = 0.5*convergence + 0.5*(accrued information value, normalised).
       else (v1/v2.1): R = 0.5*convergence + 0.5*semantic_closeness (volume proxy)."""
    if value_weighted:
        value_norm = min(1.0, cum_value / VALUE_FULL)
        return 0.5 * obs.anchor_overlap + 0.5 * value_norm
    return 0.5 * obs.anchor_overlap + 0.5 * obs.semantic_closeness


@dataclass
class ValveState:
    w: int = W
    eps: float = EPS
    eps_val: float = EPS_VAL
    r_high: float = R_HIGH
    warmup_limit: int = WARMUP_LIMIT
    trigger: str = "value"           # "dR" | "new" | "value"
    r_prev: Optional[float] = None
    flat_k: int = 0
    warmup_k: int = 0
    warmed: bool = False
    cum_value: float = 0.0
    last_value: float = 0.0          # previous turn's value (for double-gate momentum)
    decisions: list = field(default_factory=list)
    closed_at: Optional[str] = None
    closed_reason: Optional[str] = None

    def _w_eff(self, obs: TurnObs) -> int:
        """DOUBLE GATE: while value is still flowing (recent momentum), stretch w (be patient,
           don't kill a swell); once value has gone quiet, hold at base w (cut, stop wasting)."""
        if self.trigger != "value":
            return self.w
        momentum = (self.last_value + obs.value) > self.eps_val   # value arrived recently?
        return self.w + 1 if momentum else self.w

    def feed(self, obs: TurnObs) -> str:
        if self.closed_at is not None:
            return "ALREADY-CLOSED"
        vw = (self.trigger == "value")
        if vw:
            self.cum_value += obs.value
        R = compute_R(obs, self.cum_value, value_weighted=vw)
        dR = None if self.r_prev is None else R - self.r_prev
        w_eff = self._w_eff(obs)

        if self.trigger == "dR":                       # v1
            if self.r_prev is None:
                decision = "OPEN"
            elif obs.new_unique > 0 and dR > self.eps:
                self.flat_k = 0; decision = "RISING"
            elif dR <= self.eps:
                self.flat_k += 1; decision = self._close_or_wait(obs, R, self.w)
            else:
                self.flat_k = 0; decision = "RISING"

        elif self.trigger == "new":                    # v2.1
            if not self.warmed:
                if obs.new_unique > 0:
                    self.warmed = True; self.flat_k = 0; decision = "RISING"
                else:
                    self.warmup_k += 1
                    decision = self._dead_start(obs) if self.warmup_k >= self.warmup_limit else "WARMUP"
            elif obs.new_unique > 0:
                self.flat_k = 0; decision = "RISING"
            else:
                self.flat_k += 1; decision = self._close_or_wait(obs, R, self.w)

        else:                                          # v3 — value-weighted + double gate
            if not self.warmed:
                if obs.value > self.eps_val:
                    self.warmed = True; self.flat_k = 0; decision = "RISING(value)"
                else:
                    self.warmup_k += 1
                    decision = self._dead_start(obs) if self.warmup_k >= self.warmup_limit else "WARMUP"
            elif obs.value > self.eps_val:
                self.flat_k = 0
                decision = "RISING(value)"             # valuable flow continues -> reset patience
            else:
                self.flat_k += 1                       # no valuable contribution this turn
                decision = self._close_or_wait(obs, R, w_eff)   # adaptive window

        self.last_value = obs.value
        self.r_prev = R
        self.decisions.append((obs.label, round(R, 3), None if dR is None else round(dR, 3),
                               f"{self.flat_k}/{w_eff}", round(obs.value, 1), decision))
        return decision

    def _close_or_wait(self, obs, R, w_eff):
        if self.flat_k >= w_eff:
            if R >= self.r_high:
                self.closed_at, self.closed_reason = obs.label, "swell (converged + valuable)"
                return "SWELL-CLOSE"
            self.closed_at, self.closed_reason = obs.label, "plateau (low value)"
            return "PLATEAU-CUT"
        return f"FLAT {self.flat_k}/{w_eff}"

    def _dead_start(self, obs):
        self.closed_at, self.closed_reason = obs.label, "plateau (no traction)"
        return "PLATEAU-CUT"


def run(seq, w=W, eps=EPS, r_high=R_HIGH, trigger="value"):
    st = ValveState(w=w, eps=eps, r_high=r_high, trigger=trigger)
    for obs in seq:
        st.feed(obs)
    return st


def _yield(seq, upto_idx):
    """YIELD proxy = cumulative information value / turns spent (effort), through turn upto_idx.
       Real product metric replaces 'turns' with billable tokens in the live A/B."""
    turns = upto_idx + 1
    value = sum(o.value for o in seq[:turns])
    return value / turns if turns else 0.0


def report(title, seq, natural_close_idx, **kw):
    st = run(seq, **kw)
    print(f"\n{'='*74}\n{title}\n{'='*74}")
    print(f"{'turn':<22}{'R':>7}{'val':>6}{'flat':>7}  decision")
    for label, R, dR, flat, val, dec in st.decisions:
        print(f"{label:<22}{R:>7.3f}{val:>6.1f}{flat:>7}  {dec}")
    valve_close = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[5] or "CUT" in d[5]), None)
    total = len(seq)
    if valve_close is not None:
        y_valve = _yield(seq, valve_close)
        y_natural = _yield(seq, natural_close_idx)
        saved = natural_close_idx - valve_close
        print(f"\n  valve closes at turn {valve_close+1}/{total} ({st.closed_reason})")
        print(f"  YIELD at valve-close = {y_valve:.2f} value/turn  |  at natural close = {y_natural:.2f}")
        def _pct(a, b):
            return "n/a" if b == 0 else f"{'+' if a>=b else ''}{100*(a-b)/b:.0f}%"
        if saved > 0:
            print(f"  -> cuts {saved} low-value turn(s); yield {y_natural:.2f} -> {y_valve:.2f} "
                  f"({_pct(y_valve, y_natural)} yield)")
        elif saved == 0:
            print(f"  -> confirms natural close (same turn); no value lost, no tokens wasted")
        else:
            print(f"  -> closes {-saved} turn(s) EARLY — RISK of lost value; yield "
                  f"{y_natural:.2f} -> {y_valve:.2f} (check what was dropped)")
    else:
        print(f"\n  valve never closed within {total} turns")
    return st


# ---------------------------------------------------------------------------
# REAL — DISPATCH #005 (from _intercom_live.md). value = information value of the turn:
# T2 anchor proposed (mid), T3 NGI0 flag = highest-value find, T4 judge synthesis (no NEW info).
# ---------------------------------------------------------------------------
DISPATCH_005 = [
    TurnObs("T1 4×claimed",        4, 0, new_unique=0, value=0.0),
    TurnObs("T2 DHC1 done+anchor",  4, 1, new_unique=1, value=2.0),
    TurnObs("T3 DHC3 done+flag",    4, 3, new_unique=3, value=4.0),   # late but most valuable
    TurnObs("T4 judge-pass",        4, 4, new_unique=0, value=0.0),
]  # Senior closed at T4. natural_close_idx = 3.

DISPATCH_005_CHATTER = DISPATCH_005 + [
    TurnObs("T5 chatter", 4, 4, new_unique=0, value=0.0),
    TurnObs("T6 chatter", 4, 4, new_unique=0, value=0.0),
    TurnObs("T7 chatter", 4, 4, new_unique=0, value=0.0),
]  # natural_close_idx = 6.

DISPATCH_PLATEAU = [
    TurnObs("T1 dispersed", 4, 0, new_unique=0, value=0.0),
    TurnObs("T2 dispersed", 4, 1, new_unique=0, value=0.0),
    TurnObs("T3 dispersed", 4, 1, new_unique=0, value=0.0),
    TurnObs("T4 dispersed", 4, 0, new_unique=0, value=0.0),
]  # natural_close_idx = 3.

# The case v3 exists for: VOLUME high but VALUE low, then one late high-value find.
# v2.1 (counts volume) keeps running on the worthless volume; v3 (weighs value) sees the
# dead patch, but the double-gate keeps it patient enough that the late anchor still lands
# because value flowed on the immediately-preceding turn.
VALUE_VS_VOLUME = [
    TurnObs("T1 claimed",          4, 0, new_unique=0, value=0.0),
    TurnObs("T2 5 marginal",       4, 1, new_unique=5, value=0.4),   # lots of entries, little value
    TurnObs("T3 5 marginal",       4, 1, new_unique=5, value=0.4),
    TurnObs("T4 1 HIGH-value",     4, 3, new_unique=1, value=4.0),   # the find that matters
    TurnObs("T5 judge-pass",       4, 4, new_unique=0, value=0.0),
]  # natural_close_idx = 4.


# Intentional-long baseline: a sprawling valve-LESS multi-agent session — value flows for the
# first ~5 turns, converges, then 6 turns of chatter (workers re-posting, zero new value). This is
# the regime the valve exists for and the kind of run others have on LangGraph/CrewAI; our own
# disciplined swarm rarely produces it, so the turn-count is synthetic (token/turn is measured).
LONG_BASELINE = [
    TurnObs("T1 claimed",        4, 0, new_unique=0, value=0.0),
    TurnObs("T2 first finds",    4, 1, new_unique=2, value=1.5),
    TurnObs("T3 anchor",         4, 2, new_unique=3, value=3.0),
    TurnObs("T4 develop",        4, 3, new_unique=2, value=2.0),
    TurnObs("T5 taper",          4, 3, new_unique=1, value=1.0),
    TurnObs("T6 judge-ish",      4, 4, new_unique=0, value=0.0),
    TurnObs("T7 chatter",        4, 4, new_unique=0, value=0.0),
    TurnObs("T8 chatter",        4, 4, new_unique=0, value=0.0),
    TurnObs("T9 chatter",        4, 4, new_unique=0, value=0.0),
    TurnObs("T10 chatter",       4, 4, new_unique=0, value=0.0),
    TurnObs("T11 chatter",       4, 4, new_unique=0, value=0.0),
    TurnObs("T12 chatter",       4, 4, new_unique=0, value=0.0),
]  # natural (valve-less) close = T12. natural_close_idx = 11.


def counterfactual(seq, natural_idx, tpt=MEASURED_BILLABLE_INPUT_PER_TURN, **kw):
    st = run(seq, **kw)
    vc = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[5] or "CUT" in d[5]), None)
    if vc is None:
        print("  valve never closed — no counterfactual saving"); return
    tv, tb = vc + 1, natural_idx + 1
    cut = tb - tv
    tok_v, tok_b = tv * tpt, tb * tpt
    val_v = sum(o.value for o in seq[:tv])
    val_b = sum(o.value for o in seq[:tb])
    yv, yb = val_v / tok_v, val_b / tok_b
    print(f"  valve closes T{tv}/{tb} ({st.closed_reason})")
    print(f"  turns cut: {cut}  |  tokens: {tok_b:,.0f} -> {tok_v:,.0f}  (saved {cut*tpt:,.0f}, "
          f"{100*cut/tb:.0f}%)")
    print(f"  value delivered: {val_b:.1f} -> {val_v:.1f}  (value lost to early close: {val_b-val_v:.1f})")
    print(f"  YIELD (value/token): {yb*1e6:.2f} -> {yv*1e6:.2f} per-M  ({'+' if yv>=yb else ''}{100*(yv-yb)/yb:.0f}%)")


# LIVE — DISPATCH #006 (real run, 31 May 2026). Senior audit-turn sequence from the actual
# 2-worker run. Real tokens: 68 worker-turns, 4,609,888 billable input, 67,792/turn (matches
# #004's 69,877 within 3% — the counterfactual unit is validated). value = total value the audit
# turn delivered (DHC-1 done value 18; DHC-2 done value 10; then both self-idle).
DISPATCH_006_LIVE = [
    TurnObs("T1 2×claimed",  2, 0, new_unique=0, value=0.0),
    TurnObs("T2 DHC1 done",  2, 1, new_unique=6, value=18.0),
    TurnObs("T3 DHC2 done",  2, 2, new_unique=4, value=10.0),
    TurnObs("T4 both idle",  2, 2, new_unique=0, value=0.0),   # workers self-terminated; run exited
]  # natural close = T4 (workers stopped themselves). natural_close_idx = 3.


if __name__ == "__main__":
    print("CAIRN RESONANCE VALVE v3 — yield optimiser (value ÷ effort), not a one-sided cutter")
    print(f"params: w={W}, eps_val={EPS_VAL}, R_high={R_HIGH}, VALUE_FULL={VALUE_FULL}")

    report("LIVE — DISPATCH #006 (real 2-worker run: did the valve need to fire?)",
           DISPATCH_006_LIVE, natural_close_idx=3, trigger="value")
    report("REAL — DISPATCH #005 (track the valuable late find, don't kill it)",
           DISPATCH_005, natural_close_idx=3, trigger="value")
    report("SYNTHETIC — #005 + 3 chatter turns (value dried up -> cut)",
           DISPATCH_005_CHATTER, natural_close_idx=6, trigger="value")
    report("SYNTHETIC — plateau / no traction (low value -> cut as fail)",
           DISPATCH_PLATEAU, natural_close_idx=3, trigger="value")
    report("SYNTHETIC — high VOLUME low VALUE, then a late high-value find",
           VALUE_VS_VOLUME, natural_close_idx=4, trigger="value")

    # v2.1 (volume) vs v3 (value) on the volume-vs-value case — why value-weighting matters
    print(f"\n{'='*74}\nv2.1 (counts volume) vs v3 (weighs value) — the volume-vs-value case\n{'='*74}")
    for trig, name in (("new", "v2.1 volume"), ("value", "v3 value")):
        st = run(VALUE_VS_VOLUME, trigger=trig)
        vc = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[5] or "CUT" in d[5]), None)
        where = f"turn {vc+1}/5 ({st.closed_reason})" if vc is not None else "never closed (ran full)"
        print(f"  {name:<14}: {where}")

    # w-sensitivity (v3, chatter case)
    print(f"\n{'='*74}\nW-SENSITIVITY (v3, chatter case) — base w; double-gate adds +1 while value flows\n{'='*74}")
    for w in (1, 2, 3):
        st = run(DISPATCH_005_CHATTER, w=w, trigger="value")
        vc = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[5] or "CUT" in d[5]), None)
        if vc is not None:
            print(f"  w={w}: closes turn {vc+1}/7 ({st.closed_reason}) -> cuts {6-vc} chatter turn(s)")
        else:
            print(f"  w={w}: never closed within 7 turns")

    # COUNTERFACTUAL — real measured token/turn (#004) × intentional-long valve-less baseline
    print(f"\n{'='*74}\nCOUNTERFACTUAL — yield on a sprawling baseline")
    print(f"(token/turn = {MEASURED_BILLABLE_INPUT_PER_TURN:,.0f}, measured #004; long baseline synthetic)\n{'='*74}")
    report("intentional-long baseline (value front, 6 chatter turns)", LONG_BASELINE,
           natural_close_idx=11, trigger="value")
    print()
    counterfactual(LONG_BASELINE, natural_idx=11, trigger="value")
