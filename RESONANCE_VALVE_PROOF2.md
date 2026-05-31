# PROOF2 (in progress) — Resonance Valve backtest

> PROOF1 measured the **context-axis** mechanism (minimal-context: 54% fewer tokens, 65% lower cost,
> controlled A/B). PROOF2 is the **turn-axis** mechanism (the valve). This file is its **first step**:
> a backtest of the formula on real past-dispatch data — zero extra swarm quota. It answers *"does the
> close formula fire at the right moment?"*, NOT yet *"how many real tokens does it save?"* (that needs
> the live A/B below).
>
> Code: `resonance_valve.py` (runnable, `python3 resonance_valve.py`).

## Why a backtest first

The R(t)/dR/dt/w design in `RESONANCE_VALVE.md` was **theory**. Before claiming any saving we turned it
into runnable code and ran it against real data (DISPATCH #005's reconstructed audit-turn sequence from
`_intercom_live.md`) + synthetic chatter and plateau cases. The point: catch the formula's failure modes
on the desk, cheaply, before spending swarm quota on a live A/B.

## What the backtest found — the formula needed 3 iterations

Each iteration was driven by a real failure the data exposed (this is the value of testing, not a
weakness to hide):

| Version | Failure mode the data exposed | Fix |
|---|---|---|
| **v1** — `dR/dt` flat for w turns (spec-literal) | At real convergence, R **jumps** (judge-pass: R 0.5→1.0 in one turn). A rising dR/dt reset the patience counter, so the valve read the close moment as "still rising" and never closed. The spec assumed a *gradual* plateau; real convergence is a **step**. | Close trigger = **new-contribution flat**, not dR/dt. |
| **v2** — new-contribution flat + warmup | A dispatch that produces **zero** new contributions (total dispersal, no traction) sat in WARMUP forever → never cut. The exact case the valve exists to cut. | **Bounded warmup**: past `warmup_limit` turns with no contribution → cut as "no-traction plateau". |
| **v2.1** | — all three cases correct | ✓ |

## v2.1 backtest results (w=2, eps=0.02, R_high=0.55, warmup_limit=3)

| Scenario | Source | Valve verdict | Turns cut |
|---|---|---|---|
| **DISPATCH #005** | real (reconstructed) | tracked correctly to T4 (judge-pass, FLAT 1/2); session ended naturally at T4 with no chatter | 0 — **confirms natural close, no harm** |
| #005 + 3 chatter turns | synthetic | SWELL-CLOSE at T5 | **2 / 7 (~29%)** |
| total dispersal (no traction) | synthetic | PLATEAU-CUT at T3 (no-traction) | 1 / 4 (~25%) |

**w-sensitivity (chatter case) — w is the single product knob:**
- w=1 → cuts 3 turns (aggressive; risks killing a real swell — see honest limits)
- w=2 → cuts 2 turns (default, safe)
- w=3 → cuts 1 turn (conservative)

## Honest limits (what the backtest does NOT prove)

1. **Backtest ≠ token measurement.** It proves the formula fires at a sensible turn. It does **not**
   measure real token/$ saving — turns aren't uniform in cost, and the chatter/plateau turn-counts are
   on synthetic continuations, not a measured live run. The % saving headline must come from the live
   A/B below.
2. **The formula is empirical, not settled.** Three iterations, each surfacing a new edge case on real
   data. `w`, `eps`, `R_high`, `warmup_limit` are **not** tunable from the desk — they need real-run
   data. This is exactly why the live A/B is required, not optional.
3. **Overlap with mechanism #1.** Our own SWARM v0.7 is already low-chatter (minimal-context + sharp
   filter → workers stay busy; PROOF1 run noted idle-judge never triggered). So the valve's marginal
   saving **on our own disciplined swarm may be small** — its real value is on the sprawling, long-loop
   multi-agent sessions others run on LangGraph/CrewAI/AutoGen. The live A/B must measure marginal
   saving *over* minimal-context, not in isolation, or the two mechanisms will look like they
   double-count.

## Next step — live A/B (the real PROOF2)

Run an identical real task two ways, measure billable input tokens + turns + judge-approval:
- **Arm A (valve OFF):** swarm runs to natural/fixed close.
- **Arm B (valve ON, w=2):** Senior closes via the valve.
- **Metrics:** (a) tokens/session, (b) judge-approval (did early close drop quality?), (c) chatter turns
  caught, (d) baseline delta.

**Cost-protective option (floor-aware):** instead of 2× full runs, do ONE valve-ON run and measure the
turns the valve actually cut + a counterfactual estimate (cut turns × mean turn token). Cheaper, gives
a directional % rather than a clean A/B number. Operator chooses A/B-clean vs counterfactual-cheap.

Until the live number lands, the product claim is *"cuts wasted multi-agent turns; measured saving
pending"* — not a fabricated %.
