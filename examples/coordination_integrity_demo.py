#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Coordination integrity: why naive shared state silently loses agent work — and Cairn's fix.

The wound (voiced across CrewAI #4111, AutoGen issues, Hacker News): when N agents write to shared
state, last-write-wins silently overwrites work, and when something breaks you can't tell what
happened. A2A and MCP leave this shared-state layer for you to build. Cairn's passive APPEND-ONLY
blackboard IS that layer: every agent's contribution is a durable, attributable, auditable trace —
nothing is overwritten.

Run: python examples/coordination_integrity_demo.py   (offline, no deps)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cairn import Blackboard, Trace

# Three agents each find one fact for a shared research task. The 2nd is mission-critical —
# and it gets silently overwritten by the agent that writes after it (last-write-wins).
FINDINGS = [
    ("scout-pricing", "competitor raised prices 12% last week"),
    ("scout-legal",   "their new ToS forbids resale — this blocks our plan"),   # critical
    ("scout-tech",    "their API now rate-limits at 100 req/min"),
]

print("Three agents each contribute one finding to a shared task.\n")

# --- NAIVE shared state: last-write-wins (what A2A / MCP leave you to hand-roll) -----------
print("=== NAIVE shared state (a single shared slot) ===")
shared = {}
for agent, finding in FINDINGS:
    shared["result"] = finding                 # each agent overwrites the one shared slot
print("final shared state:", shared)
print(f"→ {len(FINDINGS) - 1} of {len(FINDINGS)} findings SILENTLY LOST — including the critical")
print("  legal blocker. No record of who wrote what, or when. Split-brain, undebuggable.\n")

# --- CAIRN: passive append-only blackboard -------------------------------------------------
print("=== CAIRN append-only blackboard ===")
board = Blackboard()
for agent, finding in FINDINGS:
    board.append(Trace(agent=agent, kind="finding", text=finding, value=1.0))
print(f"all {len(board)} findings preserved — full auditable trace:")
for t in board.traces:
    print("   ", t.line())
print("→ nothing overwritten; every contribution is a durable, ordered, attributable record —")
print("  the 'append-only event log' teams keep reinventing. It's Cairn's core primitive.")
