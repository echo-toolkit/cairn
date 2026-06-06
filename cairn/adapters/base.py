# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — framework-agnostic adapter glue.  © 2026 Tağmaç Çankaya
"""Turn any `invoke(prompt: str) -> str` callable into a Cairn `agent_fn(ctx) -> Trace | None`.

This is the bridge that lets you coordinate agents from ANY framework (LangChain / LangGraph /
CrewAI / a plain function) through Cairn's blackboard. The key: the prompt is built MINIMALLY from
the context (task + the bounded board digest), never the full transcript — that IS the token lever.
The framework-specific wrappers (`from_langchain`, `from_crewai`) are thin shims over this.
"""
from __future__ import annotations
from typing import Callable, Optional

from ..blackboard import Trace
from ..core import WorkerContext

# An agent signals "I have nothing new" with one of these (→ it goes idle / self-terminates).
DONE_MARKERS = ("DONE", "NOTHING NEW", "NO FURTHER", "[DONE]", "N/A")


def default_build_prompt(ctx: WorkerContext) -> str:
    """A deliberately minimal prompt: this agent's task + a bounded digest of others' traces."""
    board = (ctx.board or "").strip()
    others = f"\n\nNotes others have already left on the shared board:\n{board}" if board else ""
    return (f"Your task: {ctx.task}{others}\n\n"
            f"Add ONE concise, new finding that advances the task — do not repeat what is already "
            f"on the board. If you have nothing new to add, reply with exactly: DONE")


def default_parse(text: str, ctx: WorkerContext) -> Optional[Trace]:
    """Wrap the agent's text as a finding; return None (self-terminate) on a DONE marker / empty."""
    t = (text or "").strip()
    if not t or any(m in t.upper()[:48] for m in DONE_MARKERS):
        return None
    return Trace(agent=ctx.agent, kind="finding", text=t, value=1.0)


def _to_text(out) -> str:
    """Normalize a framework return value to text (str · LangChain AIMessage.content · CrewAI .raw)."""
    if isinstance(out, str):
        return out
    for attr in ("content", "raw", "output", "result"):
        v = getattr(out, attr, None)
        if isinstance(v, str):
            return v
    return str(out)


def as_worker_fn(
    invoke: Callable[[str], object],
    *,
    build_prompt: Callable[[WorkerContext], str] = default_build_prompt,
    parse: Callable[[str, WorkerContext], Optional[Trace]] = default_parse,
) -> Callable[[WorkerContext], Optional[Trace]]:
    """Wrap any `invoke(prompt) -> str|message` as a Cairn `agent_fn(ctx) -> Trace | None`.

    Pass the result to `run_swarm`. Override `build_prompt` to change what context the agent sees,
    or `parse` to do real value-scoring / your own self-terminate logic.
    """
    def agent_fn(ctx: WorkerContext) -> Optional[Trace]:
        out = invoke(build_prompt(ctx))
        return parse(_to_text(out), ctx)
    return agent_fn
