# PROOF2 (in progress) — Resonance Valve backtest

> **What is optimised: YIELD = information value ÷ effort (tokens).** NOT one-sided token cutting.
> Tokens are the cost; the goal is reaching valuable information cheaply. The valve must not kill a
> swell (lose value) nor run into chatter (waste tokens) — both lower yield. Optimum = the crest of
> the swell.
>
> PROOF1 measured the **context-axis** mechanism (minimal-context: 54% fewer tokens, 65% lower cost,
> controlled A/B). PROOF2 is the **turn-axis** mechanism (the valve). This file is its **first step**:
> a backtest of the formula on real past-dispatch data + synthetic cases — zero extra swarm quota. It
> answers *"does the close fire at the right moment, protecting value while cutting waste?"*, NOT yet
> *"how many real tokens does it save?"* (that needs the live A/B).
>
> Code: `resonance_valve.py` (runnable, `python3 resonance_valve.py`).

## The formula evolved through 4 iterations, each fixing a failure the real data exposed

This is the value of testing, not a weakness. The desk-written theory broke on first contact with
real data — repeatedly — and each break taught the fix.

| Version | Failure mode the data exposed | Fix |
|---|---|---|
| **v1** `dR/dt` flat (spec-literal) | At real convergence R **jumps** (judge-pass: R 0.5→1.0 one turn). Rising dR/dt reset patience → valve never closed. Spec assumed a gradual plateau; real convergence is a **step**. | trigger = new-contribution flat, not dR/dt |
| **v2** new-count flat + warmup | A dispatch producing **zero** contributions sat in WARMUP forever → never cut. | bounded warmup → no-traction cut |
| **v2.1** | volume-blind: counts entries, not their **value** → a turn of 5 marginal repeats looks as "productive" as one high-value anchor | (motivated v3) |
| **v3** value-weighted R + value trigger + **double-gate adaptive w** | — wins the main cases; one honest trade-off remains (below) | operator design, 31 May 2026 |

## v3 design (operator, 31 May 2026)

1. **Value-weighted contribution** — the close trigger watches the *value* of new contributions, not
   their count. One late high-value anchor keeps the flow alive; five marginal repeats do not.
2. **Double-gate adaptive w** — while value still flows (recent momentum), w stretches +1 (be patient,
   the swell is coming, don't kill it); once value goes quiet, w holds at base (cut, stop wasting).
3. **Value-weighted R** — R folds in accrued information value (`min(1, cum_value/VALUE_FULL)`), not
   just convergence. High R = converged AND valuable.

**Yield proxy** = cumulative value / turns spent (live A/B replaces turns with billable tokens).

## v3 backtest results (w=2, eps_val=0.5, R_high=0.55, VALUE_FULL=5)

| Scenario | Source | Verdict | Yield effect |
|---|---|---|---|
| **DISPATCH #005** | real | tracked the late high-value find (T3) as RISING, did not cut; ended naturally | 0 turns cut, no value lost |
| #005 + 3 chatter | synthetic | SWELL-CLOSE at T5 (value dried up) | **yield 0.86 → 1.20 (+40%)** |
| plateau / no traction | synthetic | PLATEAU-CUT at T3 | correctly cut a worthless run |
| **volume↓value, late spike** | synthetic | cut at T3, **MISSED the T4 high-value find** | **yield 0.96 → 0.27 (−72%)** ⚠️ |

## The honest trade-off (the central finding)

The 4th scenario is a **failure**, kept in the suite on purpose. A run of low-but-real exploration
(value 0.4/turn, below `eps_val=0.5`) was read as "no traction" and cut just before a late high-value
find landed. v3 lost value there; v2.1 (counting volume) would have kept running and caught it — at the
cost of burning tokens on the worthless volume.

This is exactly the balance the operator named: **protecting late value ↔ cutting waste is sensitive to
`eps_val` / `VALUE_FULL` / `w`, and the right line is domain-specific.** It cannot be set from the desk.
Lower `eps_val` to save that late find → real chatter (value ~0.1–0.2) starts looking "valuable" and
waste creeps back. There is no single safe constant; there is a calibration the live A/B must find.

A valve also cannot see the future: a high-value spike arriving *after* two dead turns will be cut,
because past momentum is all it has. That is an accepted bound (it is a valve, not an oracle) — most
dead-turn runs are genuinely chatter.

## Honest limits (what the backtest does NOT prove)

1. **Backtest ≠ token/yield measurement.** It shows the close fires sensibly and that yield *can* rise
   (+40% on chatter, on a turn-count proxy). It does **not** measure real token/$ yield — that is the
   live A/B. The product claim stays "improves multi-agent yield; measured number pending."
2. **Parameters are empirical.** `eps_val`, `VALUE_FULL`, `w`, `R_high`, `warmup_limit` are tuned by
   real-run data, not the desk — the 4 iterations + the trade-off above prove this.
3. **Overlap with mechanism #1.** Our own swarm is already low-chatter (minimal-context). The valve's
   marginal yield-gain on our disciplined swarm may be small; its real value is on sprawling LangGraph/
   CrewAI/AutoGen sessions. The live A/B must measure marginal yield *over* minimal-context.

## Counterfactual result — yield on a sprawling baseline (cheap, zero new quota)

Operator chose the cost-protective path: **measured token/turn × an intentional-long valve-less
baseline.** Token/turn = **69,877** (real, DISPATCH #004: 9,014,101 billable input / 129 turns). The
baseline (12 turns: value flows ~5 turns, converges, then 6 chatter turns) is **synthetic in
turn-count** — our own swarm is low-chatter and rarely sprawls, but others' LangGraph/CrewAI sessions
do; this is that regime. (`resonance_valve.py`, `counterfactual()`.)

| metric | valve OFF (baseline) | valve ON (v3) |
|---|---:|---:|
| turns | 12 | 7 (closed T7) |
| billable input tokens | 838,521 | 489,137 |
| information value delivered | 7.5 | **7.5** |
| **yield (value / M-token)** | 8.94 | **15.33** |

- **Turns cut: 5 / 12 (42%). Tokens saved: 349,384 (42%).**
- **Value lost to early close: 0.0** — the cut turns were the chatter, not the value. This is the
  whole point: yield rose **without** sacrificing information.
- **Yield: +71%** (value per token), with value held flat. The headline is yield, not "fewer tokens."

**Honest scope of this counterfactual:** token/turn is measured; the baseline turn-count AND the
per-turn value scores (0–4) are assigned, not measured. It shows the valve *would* convert chatter
turns into yield on a sprawling run, at a real token unit cost. It does NOT replace a live A/B where
value is judge-scored on a real task and the run length is real, not assumed. Directional, not final.

## Live run — DISPATCH #006 (executed 31 May 2026, real swarm, valve-ON)

A real 2-worker swarm dispatch was run (Cairn distribution-channel research — real floor value, and
open-ended enough to let the valve fire). Senior = live (this session). Real tokens measured from
session JSONLs (`_bench_006.py`).

**Measured:** 2 workers, **68 worker-turns, 4,609,888 billable input tokens, 67,792 / turn** — this
matches #004's 69,877/turn within 3%, so **the counterfactual's token unit is validated on a fresh run.**

**Valve behaviour — the honest headline:** the valve **never fired.** Audit-turn sequence: T2 DHC-1
done (value 18) → RISING; T3 DHC-2 done (value 10, a *new* self-claimed angle — emergence) → RISING;
T4 both workers went **idle on their own** ("yeni tur açmıyorum, idle") and the run exited. The valve
was still at `FLAT 1/3` (double-gate kept it patient) when the workers self-terminated. **0 chatter
turns, 0 turns to cut.**

**What this proves (live confirmation of the overlap caveat):** on our own disciplined swarm
(minimal-context + sharp filter + workers that stop when value ends), there is **no chatter for the
valve to cut** — the workers self-regulate before the valve would even close. Mechanism #1
(minimal-context) and worker self-discipline already prevent the waste mechanism #2 (the valve) is
built to remove. **The valve's value is NOT on our dogfood swarm; it is on external sprawling sessions**
(the counterfactual's intentional-long baseline: LangGraph/CrewAI runs that *don't* self-terminate).
Claiming the valve saves tokens on our own swarm would be false — it doesn't, because there's nothing
to save.

**Honest product position after the live run:**
- Counterfactual (sprawling baseline, validated token unit): **+71% yield, 42% turns cut, 0 value lost**
  — the citable figure, scoped to *sprawling external swarms*.
- Live dogfood: valve idle (0 cut) — our swarm doesn't need it; minimal-context already does the job.
- So Cairn's two mechanisms are **sequenced, not additive on the same workload**: minimal-context for
  disciplined swarms; the valve for the sprawling ones. Sell the valve to teams whose agents *don't*
  self-terminate — not as a second saving on top of minimal-context.
- Bonus: the run was not wasted quota — it produced 10 value-scored real distribution channels for
  Cairn (`_dispatch_006_distribution.md`), actual floor work.

## Next step — full A/B only if a buyer needs it

Identical real task, two arms; measure **value AND tokens**, report **yield = value/token**:
- **Arm A (valve OFF):** runs to natural/fixed close.
- **Arm B (valve ON, v3):** Senior closes via the valve.
- **Metrics:** (a) information value delivered (judge-scored), (b) billable tokens, (c) **yield = a/b**,
  (d) value lost to early close (the §trade-off, watched directly). Optimise (w, eps_val, VALUE_FULL)
  for max yield at no value-loss.
- **Cost-protective variant:** one valve-ON run + counterfactual on cut turns. Cheaper, directional.

The headline is not "X% fewer tokens" — it is "X% more value per token," with value-loss held at zero.
