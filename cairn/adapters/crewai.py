# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — CrewAI adapter.  © 2026 Tağmaç Çankaya
"""Coordinate CrewAI agents through Cairn's blackboard.

`from_crewai(agent)` wraps a CrewAI `Agent` as a Cairn `agent_fn`: each round it runs a one-off
`Task` whose description is Cairn's MINIMAL prompt (the agent's task + the bounded board digest),
so N CrewAI agents coordinate via the passive blackboard instead of a full shared transcript.

    from cairn import run_swarm, Worker
    from cairn.adapters import from_crewai
    run_swarm(from_crewai(my_crew_agent), [Worker("a", "angle A"), Worker("b", "angle B")])

crewai is an OPTIONAL dependency — imported lazily inside the wrapper.
`pip install "cairn-coordination[crewai]"`.
"""
from __future__ import annotations
from .base import as_worker_fn


def from_crewai(agent, *, expected_output: str = "one concise finding, or DONE",
                task_kwargs: dict | None = None, **kw):
    """Wrap a CrewAI Agent as a Cairn agent_fn (one Task per round, minimal Cairn prompt)."""
    def invoke(prompt: str):
        from crewai import Task                       # lazy — only when actually used
        task = Task(description=prompt, agent=agent,
                    expected_output=expected_output, **(task_kwargs or {}))
        return agent.execute_task(task)               # returns the output string
    return as_worker_fn(invoke, **kw)
