#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Coordinate framework-style agents through Cairn — offline demo (a fake LLM, no deps).

Shows `cairn.adapters.as_worker_fn`: wrap any `invoke(prompt)->str` (your LLM call, a LangChain
runnable's `.invoke`, a CrewAI agent) and let Cairn coordinate N of them via the blackboard with
minimal per-agent context. Run: python examples/adapter_demo.py
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cairn import run_swarm, Worker
from cairn.adapters import as_worker_fn

FACTS = ["bounded coordination is auditable", "minimal context cuts tokens ~54%",
         "the blackboard removes the conversation channel"]


def fake_llm(prompt: str) -> str:
    """Stand-in for a real model / LangChain runnable / CrewAI agent. Adds one new fact, else DONE."""
    for f in FACTS:
        if f not in prompt:                 # the prompt carries the bounded board digest
            return f
    return "DONE"


if __name__ == "__main__":
    result = run_swarm(as_worker_fn(fake_llm),
                       [Worker("a", "summarize Cairn"), Worker("b", "summarize Cairn")],
                       max_rounds=6)
    print("traces:")
    for t in result.traces:
        print("  ", t.line())
    print(f"\nclosed: {result.closed_reason} | total_value {result.total_value()}")
    print("→ agents coordinated through the blackboard (minimal context) and self-terminated.")
