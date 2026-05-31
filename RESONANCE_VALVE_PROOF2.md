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

## Next step — live A/B (the real PROOF2), now yield-framed

Identical real task, two arms; measure **value AND tokens**, report **yield = value/token**:
- **Arm A (valve OFF):** runs to natural/fixed close.
- **Arm B (valve ON, v3):** Senior closes via the valve.
- **Metrics:** (a) information value delivered (judge-scored), (b) billable tokens, (c) **yield = a/b**,
  (d) value lost to early close (the §trade-off, watched directly). Optimise (w, eps_val, VALUE_FULL)
  for max yield at no value-loss.
- **Cost-protective variant:** one valve-ON run + counterfactual on cut turns. Cheaper, directional.

The headline is not "X% fewer tokens" — it is "X% more value per token," with value-loss held at zero.
