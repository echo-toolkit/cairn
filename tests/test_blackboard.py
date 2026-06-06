# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the passive stigmergic blackboard + Trace."""
from cairn import Blackboard, Trace


def test_trace_line_includes_agent_kind_value():
    line = Trace(agent="a", kind="finding", text="hello", value=2.0).line()
    assert "[a|finding|v2]" in line
    assert line.rstrip().endswith("hello")


def test_trace_anchored_marker():
    assert "*" in Trace(agent="a", anchored=True, text="x").line()
    assert "*" not in Trace(agent="a", anchored=False, text="x").line()


def test_append_len_and_total_value():
    b = Blackboard()
    b.append(Trace(agent="a", value=1.5))
    b.append(Trace(agent="b", value=2.5))
    assert len(b) == 2
    assert b.total_value() == 4.0


def test_findings_filters_by_kind():
    b = Blackboard()
    b.append(Trace(agent="a", kind="claim"))
    b.append(Trace(agent="a", kind="finding", text="f"))
    assert len(b.findings()) == 1


def test_digest_is_bounded_and_keeps_newest():
    b = Blackboard()
    for i in range(100):
        b.append(Trace(agent=f"w{i}", text="x" * 50, value=1.0))
    d = b.digest(max_chars=200, recent=20)
    assert len(d) <= 200          # bounded — the token lever
    assert "w99" in d             # newest preserved


def test_persistence_roundtrip(tmp_path):
    p = tmp_path / "bb.jsonl"
    b = Blackboard(path=str(p))
    b.append(Trace(agent="a", text="persisted", value=1.0))
    reloaded = Blackboard(path=str(p))
    assert len(reloaded) == 1
    assert reloaded.traces[0].text == "persisted"
    assert reloaded.traces[0].value == 1.0
