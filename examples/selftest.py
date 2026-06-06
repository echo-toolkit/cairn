# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — offline self-test (no LLM, no cost).  © 2026 Tağmaç Çankaya
"""Proves the v1 library works end-to-end with a deterministic fake agent_fn:
workers coordinate through the blackboard (no conversation channel), the gardener
times the close, and idle workers self-terminate. Run: python examples/selftest.py

Real usage replaces `fake_agent` with a function that builds a prompt from `ctx`
(minimal!) and calls your model — see README / the docstring in cairn/__init__.py.
"""
import sys
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from cairn import run_swarm, Worker, Trace, Gardener

ANCHOR = "auditable"   # the shared concept workers converge on, purely via the board


def fake_agent(ctx):
    """Deterministic stand-in for an LLM agent. Emits a claim, then a finding, then an
    anchored finding once it sees the shared anchor on the board, then goes idle."""
    board = ctx.board
    if ctx.round == 1:
        return Trace(agent=ctx.agent, kind="claim", text=f"taking {ctx.task}", value=0.0)
    if ctx.round == 2:
        # first real finding; the first worker seeds the anchor, others may not see it yet
        seeds_anchor = ctx.agent == "scout-1"
        txt = f"{ctx.task}: bounded coordination is {ANCHOR}" if seeds_anchor else f"{ctx.task}: a finding"
        return Trace(agent=ctx.agent, kind="finding", text=txt, value=2.0, anchored=False)
    if ctx.round == 3:
        # stigmergy: converge on the anchor if another worker already left it on the board
        if ANCHOR in board:
            return Trace(agent=ctx.agent, kind="finding",
                         text=f"{ctx.task}: confirming {ANCHOR} (anchored to scout-1)",
                         value=1.5, anchored=True)
        return Trace(agent=ctx.agent, kind="finding", text=f"{ctx.task}: still exploring", value=0.5)
    return None   # round >= 4: nothing new -> idle (self-terminate)


def main():
    workers = [Worker("scout-1", "angle: cost"),
               Worker("scout-2", "angle: oversight"),
               Worker("scout-3", "angle: reliability")]

    result = run_swarm(fake_agent, workers, max_rounds=8, gardener=Gardener(trigger="value"))

    print("=== Cairn v0.1 self-test — bounded blackboard coordination ===\n")
    print("BLACKBOARD (traces left, no conversation channel):")
    for t in result.traces:
        print("  " + t.line())
    print("\nGARDENER decisions (turn / R / value / flat / decision):")
    for label, R, dR, flat, val, dec in result.gardener.valve.decisions:
        print(f"  {label:<5} R={R:<5} val={val:<5} flat={flat:<6} {dec}")
    print(f"\n  rounds run     : {result.rounds}")
    print(f"  closed because : {result.closed_reason}")
    print(f"  total value    : {result.total_value()}")
    print(f"  traces         : {len(result.traces)}")

    # assertions — the library behaves as designed
    assert result.rounds < 8, "should close/self-terminate before max_rounds"
    assert any(t.anchored for t in result.traces), "stigmergic convergence should occur via the board"
    assert result.total_value() > 0, "value should accrue"
    print("\n  ✓ PASS — workers coordinated via the blackboard, converged on the anchor,")
    print("    and the run ended on its own (gardener close / self-termination), not at max_rounds.")


if __name__ == "__main__":
    main()
