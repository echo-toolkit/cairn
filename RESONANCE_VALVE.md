# Cairn — Resonance Valve (turn-axis token cutter)

> Cairn's **second mechanism**. The first (minimal-context + stigmergic blackboard) cuts the
> tokens each agent *carries per turn* (context-axis). The valve cuts *how many turns the session
> runs* (turn-axis). Orthogonal; together a two-axis token cutter.
>
> A senior agent that distinguishes **plateau** from **swell** in a multi-agent session and closes
> both at the right moment, ending wasted turns and the tokens they burn.
> Metaphor origin: synchronised pendulums (Huygens) + gong acoustics (strike → cacophony → swell).
> The metaphor produced the design; the product no longer depends on it.
>
> **Deliberately out of scope:** any "intelligence emergence" claim — see §6. The target is
> measurable token saving, not a revolution.

---

## 0. Base model — who is what

| Component | Role | Does | Does NOT |
|---|---|---|---|
| **Human** | Ground | Sets intent + material, starts, approves the swell | Produce content, micro-manage |
| **Senior agent** | The hand on the gong / the valve | Watches the gradient, closes at the right moment (swell or plateau) | Produce content, impose direction, answer |
| **Worker agents** | Pendulums / gong modes | Vibrate, run their own turn | — |

**Critical distinction (the product's real value):** the senior **produces no content** — it only
times the coupling/turns and makes the close decision. An orchestrator that stays out of the content
is what separates this from the "lead that manages everything" approach in existing frameworks.
The human transmits, the senior watches/cuts, the agents vibrate.

This is exactly Cairn's existing **gardener Senior**: it does not assign tasks, it distils and only
intervenes — and now it has a *measurable* close function instead of a heuristic one.

---

## 1. Senior discipline (5 principles)

1. **The senior does not produce, it times.** Its only job: watch the turns and decide when to close.
   No content, no direction, no answers. If it hears its own voice, it has erred.
2. **Intent is the open condition.** Until the human says "we start here, the material is this, the
   need is in this direction," the system does not stand up. No intent → the system sleeps. This is
   the first breaker against the token monster — aimless listening = an endless, always-burning loop.
3. **An unready turn is not fed.** If pushback arrives (agents going defensive, hardening positions,
   repeating): cut/wait. Insistence burns tokens.
4. **There are exactly two ways to close.** Either it resonated and finished (swell), or it did not
   resonate and was released (plateau/dispersal). **There is no forever-spinning middle state** — the
   token monster is precisely that "spinning in the middle."
5. **An over-long session is closed.** After the gradient flattens, every extra turn burns tokens and
   produces no benefit (chatter). The senior sees the flat gradient and cuts.

---

## 2. The human-ground's two contacts

- **Start (gate / breaker):** sets intent + material. No intent → the swarm never starts. The token
  budget is set here.
- **End (referee):** approves the closed session's output, or says "redo."
- **In between, it does not interfere.** Turn-by-turn watching is the senior's job.

---

## 3. Measurement function — the valve logic

The senior reads one scalar per turn: **resonance/convergence level R(t)**. The decision hangs not on
**R itself but on its derivative (dR/dt)**.

### 3.1 R(t) — Cairn's cheap proxy (NO embedding, Rule 2: protect the wallet)

The original design measured R with embedding distance. Cairn's blackboard is already file-based, so
R is read from the blackboard at **zero marginal cost**:

```
R = 0.5 × anchor_overlap + 0.5 × new_contribution_signal
```

1. **Anchor overlap**: the share of workers that have converged onto a common finding/anchor
   (read from the event log: `claimed`/`done` lines + convergence onto an `ADVISE` anchor).
2. **New-contribution signal**: how much genuinely new, unique, verified output landed this round vs
   the last (the worker's own honest `done` line: `N entry (M new-unique / K repeat)`). Falling new
   contribution = the gradient is flattening.

> **Independence gate deliberately REMOVED (for now).** "Did the agents converge from the ground or
> from citation?" was the door to the emergence claim, not the saving product. For saving, correctly
> seeing the gradient flatten is enough — whether the convergence is "real" does not matter. Absent in
> v1; returns if we revisit emergence (§6).

### 3.2 Decision table (on dR/dt)

| State | Meaning | Action |
|---|---|---|
| dR/dt > 0, rising | Converging | Continue, watch |
| dR/dt ≈ 0, **R high** | **Swell** | **Close — success** (trigger judge-pass) |
| dR/dt ≈ 0, **R low** | **Plateau** | **Cut — did not resonate** (reframe/close) |
| dR/dt < 0 | Dispersal / drowning | **Cut** |

"Over-long gong" = R not climbing but turns continue → every extra turn burns tokens, no benefit → **cut.**

### 3.3 Thresholds + patience window w (the HEART)

```
dR/dt   = R(t) − R(t-1)
cut_if  = dR/dt ≤ ε  for w consecutive turns     # ε ≈ 0
```

- **w is the system's single real tuning knob.**
  - w too small → cuts early → "you killed my swell, half a result."
  - w too large → cuts late → the saving promise rots.
- **w can be derived from intent:** narrow intent → small w; broad exploration → large w.
- **Default:** ε ≈ 0, w = 2 (forgive one bad turn, cut on the second).
- The A/B's real job: **optimising w = optimising the product.** Everything else is around it.

**Cairn implementation:** the senior is stateless per audit turn (`claude -p`), so the valve state lives
on the blackboard — `_intercom_live.md` open-dispatch line carries `🎛️ valve: flat k/2`. Each flat audit
turn k++; new unique contribution resets k=0; at k≥2 the senior closes per the swell/plateau split.
File-based state fits the stigmergic architecture exactly.

**Post-backtest correction (v2.1 — `resonance_valve.py`, `RESONANCE_VALVE_PROOF2.md`):** the literal
`dR/dt`-flat trigger above (v1) FAILED on real data — at real convergence R *jumps* (one-turn step,
e.g. judge-pass R 0.5→1.0), and a rising derivative reset the patience counter so the valve missed the
close. **The close trigger is therefore NEW-CONTRIBUTION flat, not dR/dt-flat**: `new_unique ≤ ε` for
`w` turns. R's *level* at the trigger still selects swell (R high) vs plateau (R low). Plus a **bounded
warmup**: until the first contribution arrives the valve is inactive, but only up to `warmup_limit`
turns — a dispatch that never produces anything (total dispersal) is cut as a "no-traction plateau"
rather than waiting forever. The dR/dt framing in §3.2–3.3 is the intuition; the robust trigger is
new-contribution flat. `w`, `eps`, `R_high`, `warmup_limit` are empirical — tuned by the live A/B
(§4), not from the desk.

---

## 4. A/B measurement — produces the product and the sales number at once

- **Main variable:** w (1 / 2 / 3) and cut threshold ε. Secondary: R weights (0.5/0.5 → other).
- **Metrics:**
  - (a) **Tokens per session** — the main sales number ("cuts tokens by X%").
  - (b) **Referee approval rate** — did early cutting drop quality?
  - (c) **Wasted (chatter) turn count** — the waste the valve caught.
  - (d) **Baseline comparison** — same task without the valve vs. with it.
- **Target:** the (w, ε) set that drops tokens/chatter most while keeping referee approval high.
- **Output:** product validated AND marketing number (% saving) produced. Same work. This becomes
  **PROOF2** — the turn-axis sibling of PROOF1 (the 54%/65% context-axis benchmark in
  `_dispatch_004_benchmark.md`). Two proofs, one product.

---

## 5. Packaging / revenue channel

- Easiest form: **wrapper / middleware** — a thin layer over existing frameworks (CrewAI, LangGraph,
  AutoGen) that watches the session and makes the close decision.
- Sales line: *"A cutter that distinguishes plateau from swell in multi-agent sessions and closes both
  at the right moment — ends wasted turns and the tokens they burn. Drops your bill by X%."*
- The customer already uses those frameworks; we sell the bill-cutting add-on.
- **Same IP regime as Cairn:** AGPLv3 + commercial license. Same ICP (solo/indie swarm builder). The
  valve is Cairn's turn-axis bill-cutter; minimal-context is the context-axis one. One product, two
  levers, two reproducible proofs.

---

## 6. Parked: emergence (a topic for another time)

This version focuses on token saving. The "intersection-intelligence emergence" claim is deliberately
deferred because, until two risks are proven, the claim hangs in the air:
1. **Model homogeneity** — agents derived from the same base model "converging independently": real
   intersection, or the shared prior surfacing twice? True independence needs different model families.
2. **Consensus ≠ emergence** — the convergence mechanic can collapse to the safest common denominator
   (the average), not "the surprise point none of them started at."

Parts that return if we revisit emergence: the **independence gate** (removed from §3.1), a multi-model
setup, and an A/B measure of "is the swell output *qualitatively* different from a single-agent
baseline, or just safer?" Frozen for now.

---

## 7. Token-warning rule (project constant)

A multi-turn, multi-agent system = high token risk. Flag BEFORE these kick in: system-prompt growth,
multi-turn call increase, web-search addition, max_tokens increase, model upgrade, parallel-agent count
increase. The senior's "do not feed the unready" and "cut on a flat gradient" disciplines are not
aesthetic — they are direct cost control, and they are the product itself.

---

## Integration status (live in our own SWARM v0.7)

The valve is wired into our own gardener Senior — not just specced:
- `Dev/_senior_loop.sh` — Senior step 6 is the RESONANCE VALVE (R proxy → dR/dt → w=2 → swell/plateau
  close), separate from the pathology STOP (step 7).
- `Dev/_swarm/.claude/CLAUDE.md` — workers report `N entry (M new-unique / K repeat)` to feed R.
- `Dev/_intercom_live.md` — `🎛️ RESONANCE VALVE STATE` block carries `flat k/2` per open dispatch.

Cairn v1 packages this as a framework-agnostic library + the PROOF2 benchmark harness.

Origin: `Desktop/swarm-senior-resonance.md` (Turkish design doc, 30 May 2026) — translated to English
and reframed as Cairn's second mechanism here (deliverable-English discipline).
