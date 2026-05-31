"""Cairn — Resonance Valve: the turn-axis token cutter, as RUNNABLE code (not just spec).

Turns the R(t)/dR/dt/w theory in RESONANCE_VALVE.md into a testable function, then
BACKTESTS it on real past-dispatch data + a synthetic chatter case. This is PROOF2's
cheap first step (zero extra swarm quota): does the formula catch the right close moment?

R(t) cheap proxy (NO embedding — read from the file blackboard):
    R = 0.5 * anchor_overlap + 0.5 * semantic_closeness
      anchor_overlap   = share of active workers converged on a common anchor (0..1)
      semantic_closeness = 1/(1+new_unique)  -> high when few new uniques arrive (converging)

Close logic (on the derivative):
    dR/dt = R(t) - R(t-1)
    flat if dR/dt <= eps for w consecutive audit turns
    at close: R high  -> SWELL   (converged, finish + judge-pass)
              R low   -> PLATEAU  (dispersed, cut/reframe)
    new uniques rising again -> reset the flat counter (work is still being produced)

Run: python3 resonance_valve.py
"""
from dataclasses import dataclass, field
from typing import Optional

EPS = 0.02            # dR/dt <= EPS counts as "flat"
W = 2                 # patience window (forgive one bad turn, cut on the second)
R_HIGH = 0.55         # at-close R above this = SWELL, below = PLATEAU


@dataclass
class TurnObs:
    """One Senior audit turn, as read from the blackboard."""
    label: str
    active_workers: int
    anchored_workers: int   # how many converged on the common anchor this turn
    new_unique: int         # genuinely new verified entries added this turn

    @property
    def anchor_overlap(self) -> float:
        return self.anchored_workers / self.active_workers if self.active_workers else 0.0

    @property
    def semantic_closeness(self) -> float:
        return 1.0 / (1.0 + self.new_unique)


def compute_R(obs: TurnObs) -> float:
    return 0.5 * obs.anchor_overlap + 0.5 * obs.semantic_closeness


@dataclass
class ValveState:
    """trigger='dR'  -> v1, literal to the spec (dR/dt flat for w turns).
       trigger='new' -> v2, fixed after backtest: the close trigger is NEW-CONTRIBUTION
                        flat (new_unique<=0 for w turns), robust to R's step-jump at
                        convergence; plus a warmup gate so the start (no work yet) is not
                        mistaken for a plateau. R level (high/low) still picks swell vs plateau."""
    w: int = W
    eps: float = EPS
    r_high: float = R_HIGH
    trigger: str = "new"
    warmup_limit: int = 3        # max turns to wait for first contribution; past it = dead-start
    r_prev: Optional[float] = None
    flat_k: int = 0
    warmup_k: int = 0
    warmed: bool = False
    decisions: list = field(default_factory=list)
    closed_at: Optional[str] = None
    closed_reason: Optional[str] = None

    def feed(self, obs: TurnObs) -> str:
        if self.closed_at is not None:
            return "ALREADY-CLOSED"
        R = compute_R(obs)
        dR = None if self.r_prev is None else R - self.r_prev

        if self.trigger == "dR":
            if self.r_prev is None:
                decision = "OPEN"
            elif obs.new_unique > 0 and dR > self.eps:
                self.flat_k = 0; decision = "RISING"
            elif dR <= self.eps:
                self.flat_k += 1
                decision = self._close_or_wait(obs, R)
            else:
                self.flat_k = 0; decision = "RISING"
        else:  # trigger == "new"  (v2.1)
            if not self.warmed:
                if obs.new_unique > 0:
                    self.warmed = True; self.flat_k = 0; decision = "RISING"
                else:
                    self.warmup_k += 1
                    if self.warmup_k >= self.warmup_limit:   # never got traction -> dead start
                        self.closed_at, self.closed_reason = obs.label, "plateau (no traction)"
                        decision = "PLATEAU-CUT"
                    else:
                        decision = "WARMUP"      # work hasn't started yet; bounded patience
            elif obs.new_unique > 0:
                self.flat_k = 0; decision = "RISING"   # fresh contribution resets patience
            else:
                self.flat_k += 1                 # no new contribution this turn
                decision = self._close_or_wait(obs, R)

        self.r_prev = R
        self.decisions.append((obs.label, round(R, 3), None if dR is None else round(dR, 3),
                               f"{self.flat_k}/{self.w}", decision))
        return decision

    def _close_or_wait(self, obs, R):
        if self.flat_k >= self.w:
            if R >= self.r_high:
                self.closed_at, self.closed_reason = obs.label, "swell (converged)"
                return "SWELL-CLOSE"
            self.closed_at, self.closed_reason = obs.label, "plateau (dispersed)"
            return "PLATEAU-CUT"
        return f"FLAT {self.flat_k}/{self.w}"


def run(seq, w=W, eps=EPS, r_high=R_HIGH, trigger="new"):
    st = ValveState(w=w, eps=eps, r_high=r_high, trigger=trigger)
    for obs in seq:
        st.feed(obs)
    return st


def report(title, seq, natural_close_idx, **kw):
    st = run(seq, **kw)
    print(f"\n{'='*70}\n{title}\n{'='*70}")
    print(f"{'turn':<22}{'R':>7}{'dR':>8}{'flat':>7}  decision")
    for label, R, dR, flat, dec in st.decisions:
        dRs = "—" if dR is None else f"{dR:+.3f}"
        print(f"{label:<22}{R:>7.3f}{dRs:>8}{flat:>7}  {dec}")
    # where would the valve close vs where the session naturally ran to?
    valve_close = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[4] or "CUT" in d[4]), None)
    total = len(seq)
    if valve_close is not None:
        saved = (natural_close_idx) - valve_close
        print(f"\n  valve closes at turn {valve_close+1}/{total} ({st.closed_reason})")
        print(f"  session naturally ran to turn {natural_close_idx+1}/{total}")
        if saved > 0:
            print(f"  -> would CUT {saved} chatter turn(s) "
                  f"(~{100*saved/(natural_close_idx+1):.0f}% of turns)")
        elif saved == 0:
            print(f"  -> valve confirms the natural close at the SAME turn (0 wasted, no harm)")
        else:
            print(f"  -> valve closes {-saved} turn(s) EARLY (risk: killed swell — check approval)")
    else:
        print(f"\n  valve never closed within {total} turns (w too large, or still rising)")
    return st


# ---------------------------------------------------------------------------
# REAL DATA — DISPATCH #005 (grant geo+thematic expansion), from _intercom_live.md
# event log. Audit-turn sequence reconstructed from claimed/done/anchor/judge events.
# ---------------------------------------------------------------------------
DISPATCH_005 = [
    # 4 workers claim 4 separate angles — fully dispersed, no anchor, no output yet
    TurnObs("T1 4×claimed",        active_workers=4, anchored_workers=0, new_unique=0),
    # DHC-1 done: 1 verified + ANCHOR proposed (PROOF1 token-efficiency route to B/D)
    TurnObs("T2 DHC1 done+anchor",  active_workers=4, anchored_workers=1, new_unique=1),
    # DHC-3 done: 3 verified + SITUATIONAL FLAG (NGI0 2nd-submission) — others orient to it
    TurnObs("T3 DHC3 done+flag",    active_workers=4, anchored_workers=3, new_unique=3),
    # Senior JUDGE PASS: dedupe + winnable-first ranking, no new entries (synthesis)
    TurnObs("T4 judge-pass",        active_workers=4, anchored_workers=4, new_unique=0),
]
# Senior actually CLOSED at T4 (judge-pass). natural_close_idx = 3 (0-based).

# ---------------------------------------------------------------------------
# SYNTHETIC — same dispatch but with 3 chatter turns AFTER convergence (no valve):
# workers keep re-posting, zero new uniques, anchor already settled. The case the
# valve is built to cut. Illustrative (mechanism demo), not measured proof.
# ---------------------------------------------------------------------------
DISPATCH_005_CHATTER = DISPATCH_005 + [
    TurnObs("T5 chatter",  active_workers=4, anchored_workers=4, new_unique=0),
    TurnObs("T6 chatter",  active_workers=4, anchored_workers=4, new_unique=0),
    TurnObs("T7 chatter",  active_workers=4, anchored_workers=4, new_unique=0),
]
# Without a valve this would run to T7. natural_close_idx = 6 (0-based).

# ---------------------------------------------------------------------------
# SYNTHETIC — a PLATEAU: workers never converge (stay dispersed), new uniques dry up.
# Should be CUT (low R), not closed as success.
# ---------------------------------------------------------------------------
DISPATCH_PLATEAU = [
    TurnObs("T1 dispersed", active_workers=4, anchored_workers=0, new_unique=0),
    TurnObs("T2 dispersed", active_workers=4, anchored_workers=1, new_unique=0),
    TurnObs("T3 dispersed", active_workers=4, anchored_workers=1, new_unique=0),
    TurnObs("T4 dispersed", active_workers=4, anchored_workers=0, new_unique=0),
]


if __name__ == "__main__":
    print("CAIRN RESONANCE VALVE — formula backtest (PROOF2 first step)")
    print(f"params: w={W}, eps={EPS}, R_high={R_HIGH}")

    print("\n########## v2 (new-contribution trigger + warmup — post-backtest fix) ##########")
    report("REAL — DISPATCH #005 (did the valve catch the natural close?)",
           DISPATCH_005, natural_close_idx=3, trigger="new")
    report("SYNTHETIC — #005 + 3 chatter turns (what the valve cuts)",
           DISPATCH_005_CHATTER, natural_close_idx=6, trigger="new")
    report("SYNTHETIC — plateau (should CUT as fail, not close as success)",
           DISPATCH_PLATEAU, natural_close_idx=3, trigger="new")

    # v1 vs v2 on the chatter case — show why the fix matters
    print(f"\n{'='*70}\nv1 (dR/dt, spec-literal) vs v2 (new-contribution) — chatter case\n{'='*70}")
    for trig, name in (("dR", "v1 dR/dt"), ("new", "v2 new-contrib")):
        st = run(DISPATCH_005_CHATTER, trigger=trig)
        vc = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[4] or "CUT" in d[4]), None)
        where = f"turn {vc+1}/7 ({st.closed_reason})" if vc is not None else "never closed"
        print(f"  {name:<16}: {where}")

    # w-sensitivity (v2, chatter case) — w IS the product knob
    print(f"\n{'='*70}\nW-SENSITIVITY (v2, chatter case) — w is the single tuning knob\n{'='*70}")
    for w in (1, 2, 3):
        st = run(DISPATCH_005_CHATTER, w=w, trigger="new")
        vc = next((i for i, d in enumerate(st.decisions) if "CLOSE" in d[4] or "CUT" in d[4]), None)
        if vc is not None:
            print(f"  w={w}: closes at turn {vc+1}/7 ({st.closed_reason}) -> cuts {6-vc} chatter turn(s)")
        else:
            print(f"  w={w}: never closed within 7 turns")
