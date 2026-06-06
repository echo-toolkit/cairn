# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the resonance valve (turn-axis close timing)."""
from cairn import ValveState, TurnObs, compute_R


def test_turnobs_anchor_overlap():
    assert TurnObs("r", active_workers=4, anchored_workers=2, new_unique=2).anchor_overlap == 0.5
    assert TurnObs("r", active_workers=0, anchored_workers=0, new_unique=0).anchor_overlap == 0.0


def test_compute_R_value_weighted_full():
    o = TurnObs("r", active_workers=2, anchored_workers=2, new_unique=1, value=0.0)
    # anchor_overlap=1.0, cum_value>=VALUE_FULL -> 0.5*1 + 0.5*1 = 1.0
    assert compute_R(o, cum_value=5.0) == 1.0


def test_warmup_dead_start_cuts_no_traction():
    v = ValveState(warmup_limit=2)
    v.feed(TurnObs("r1", 2, 0, 0, value=0.0))
    d = v.feed(TurnObs("r2", 2, 0, 0, value=0.0))
    assert v.closed
    assert "PLATEAU" in d


def test_rising_on_value_does_not_close():
    v = ValveState()
    d = v.feed(TurnObs("r1", 2, 1, 2, value=3.0))
    assert "RISING" in d
    assert not v.closed


def test_swell_close_after_convergence():
    v = ValveState(w=1)
    v.feed(TurnObs("r1", 2, 2, 2, value=4.0))   # warm + value
    v.feed(TurnObs("r2", 2, 2, 1, value=2.0))   # converge, cum_value high -> R high
    d = None
    for i in range(5):                           # flat, high-anchor turns -> SWELL-CLOSE
        d = v.feed(TurnObs(f"f{i}", 2, 2, 0, value=0.0))
        if v.closed:
            break
    assert v.closed
    assert d == "SWELL-CLOSE"


def test_already_closed_is_idempotent():
    v = ValveState(warmup_limit=1)
    v.feed(TurnObs("r1", 2, 0, 0, value=0.0))    # dead-start close
    assert v.closed
    assert v.feed(TurnObs("r2", 2, 0, 0, value=0.0)) == "ALREADY-CLOSED"
