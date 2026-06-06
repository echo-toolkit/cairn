# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — LangChain / LangGraph adapter.  © 2026 Tağmaç Çankaya
"""Coordinate LangChain / LangGraph agents through Cairn's blackboard.

`from_langchain(runnable)` wraps anything with `.invoke(...)` (a chat model, a chain, a compiled
LangGraph graph) as a Cairn `agent_fn`. Each round the runnable is invoked with a MINIMAL prompt
(this agent's task + the bounded board digest), instead of re-passing the full multi-agent transcript.

    from cairn import run_swarm, Worker
    from cairn.adapters import from_langchain
    run_swarm(from_langchain(my_chat_model), [Worker("a", "angle A"), Worker("b", "angle B")])

langchain is an OPTIONAL dependency — only needed if you build the `runnable` (this module imports
nothing from langchain itself; `.invoke` is duck-typed). `pip install "cairn-coordination[langchain]"`.
"""
from __future__ import annotations
from .base import as_worker_fn


def from_langchain(runnable, *, input_key: str | None = None, **kw):
    """Wrap a LangChain/LangGraph Runnable (anything with `.invoke`) as a Cairn agent_fn.

    input_key: if the runnable expects a dict input (e.g. a prompt-template chain or a LangGraph
    state graph), the minimal prompt is passed as `{input_key: prompt}`; otherwise the prompt
    string is passed directly. Extra kwargs (build_prompt / parse) pass through to as_worker_fn.
    """
    def invoke(prompt: str):
        payload = {input_key: prompt} if input_key else prompt
        return runnable.invoke(payload)
    return as_worker_fn(invoke, **kw)
