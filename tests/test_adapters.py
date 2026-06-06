# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the framework adapters — fully offline (no LangChain/CrewAI/LLM needed)."""
from cairn import run_swarm, Worker
from cairn.core import WorkerContext
from cairn.adapters import (as_worker_fn, default_build_prompt, default_parse,
                            from_langchain, from_crewai)

BOARD_MARK = "already left on the shared board"   # appears in the prompt once the board is non-empty


def ctx(task="find X", board="", rnd=1):
    return WorkerContext(agent="a", task=task, board=board, round=rnd)


def test_build_prompt_is_minimal_and_instructive():
    p = default_build_prompt(ctx(task="find X", board="[b|finding|v1] something"))
    assert "find X" in p and "something" in p and "DONE" in p


def test_build_prompt_empty_board_omits_section():
    assert "shared board" not in default_build_prompt(ctx(board=""))


def test_parse_done_and_empty_self_terminate():
    assert default_parse("DONE", ctx()) is None
    assert default_parse("", ctx()) is None
    assert default_parse("  N/A ", ctx()) is None
    t = default_parse("a real finding", ctx())
    assert t and t.text == "a real finding" and t.value == 1.0 and t.kind == "finding"


def test_to_text_extracts_message_content():
    class Msg:
        content = "from content"          # mimic a LangChain AIMessage
    t = as_worker_fn(lambda p: Msg())(ctx())
    assert t.text == "from content"


def test_as_worker_fn_coordinates_and_self_terminates():
    def invoke(prompt):
        return "DONE" if BOARD_MARK in prompt else "a finding"
    r = run_swarm(as_worker_fn(invoke), [Worker("a", "A"), Worker("b", "B")], max_rounds=5)
    assert len(r.traces) >= 1
    assert r.closed_reason != "max-rounds reached"     # agents self-terminate via DONE


def test_from_langchain_duck_typed_runnable():
    class FakeRunnable:
        def __init__(self):
            self.calls = []
        def invoke(self, payload):
            self.calls.append(payload)
            return "DONE" if BOARD_MARK in str(payload) else "lc finding"
    fr = FakeRunnable()
    r = run_swarm(from_langchain(fr), [Worker("a", "A")], max_rounds=4)
    assert any("lc finding" in t.text for t in r.traces)
    assert fr.calls                                     # the runnable was actually invoked


def test_from_langchain_input_key_wraps_dict():
    seen = {}
    class FakeGraph:
        def invoke(self, payload):
            seen["payload"] = payload
            return "DONE"
    run_swarm(from_langchain(FakeGraph(), input_key="messages"), [Worker("a", "A")], max_rounds=1)
    assert isinstance(seen["payload"], dict) and "messages" in seen["payload"]


def test_from_crewai_importable_and_callable():
    # crewai isn't installed here; the wrapper imports it lazily, so just confirm it's usable
    assert callable(from_crewai)
