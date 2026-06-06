# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — Resonance Valve core (turn-axis yield optimiser).  © 2026 Tağmaç Çankaya
"""Decides WHEN coordination should close: optimises YIELD = information value / effort,
not one-sided token cutting. The gardener (core.Gardener) drives this each round.

This is the reusable core extracted from the backtested `resonance_valve.py` proof
script (the proof keeps the demo data + iteration story; this module is import-only).
Default trigger = "value" (v3): value-weighted R + value trigger + double-gate adaptive w.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

EPS = 0.02
EPS_VAL = 0.5
W = 2
R_HIGH = 0.55
VALUE_FULL = 5.0
WARMUP_LIMIT = 3


@dataclass
class TurnObs:
    label: str
    active_workers: int
    anchored_workers: int
    new_unique: int
    value: float = 0.0

    @property
    def anchor_overlap(self) -> float:
        return self.anchored_workers / self.active_workers if self.active_workers else 0.0

    @property
    def semantic_closeness(self) -> float:
        return 1.0 / (1.0 + self.new_unique)


def compute_R(obs: TurnObs, cum_value: float = 0.0, value_weighted: bool = True) -> float:
    if value_weighted:
        return 0.5 * obs.anchor_overlap + 0.5 * min(1.0, cum_value / VALUE_FULL)
    return 0.5 * obs.anchor_overlap + 0.5 * obs.semantic_closeness


@dataclass
class ValveState:
    w: int = W
    eps: float = EPS
    eps_val: float = EPS_VAL
    r_high: float = R_HIGH
    warmup_limit: int = WARMUP_LIMIT
    trigger: str = "value"
    r_prev: Optional[float] = None
    flat_k: int = 0
    warmup_k: int = 0
    warmed: bool = False
    cum_value: float = 0.0
    last_value: float = 0.0
    decisions: list = field(default_factory=list)
    closed_at: Optional[str] = None
    closed_reason: Optional[str] = None

    def _w_eff(self, obs: TurnObs) -> int:
        if self.trigger != "value":
            return self.w
        momentum = (self.last_value + obs.value) > self.eps_val
        return self.w + 1 if momentum else self.w

    def feed(self, obs: TurnObs) -> str:
        if self.closed_at is not None:
            return "ALREADY-CLOSED"
        vw = (self.trigger == "value")
        if vw:
            self.cum_value += obs.value
        R = compute_R(obs, self.cum_value, value_weighted=vw)
        dR = None if self.r_prev is None else R - self.r_prev
        w_eff = self._w_eff(obs)

        if self.trigger == "dR":
            if self.r_prev is None:
                decision = "OPEN"
            elif obs.new_unique > 0 and dR > self.eps:
                self.flat_k = 0; decision = "RISING"
            elif dR <= self.eps:
                self.flat_k += 1; decision = self._close_or_wait(obs, R, self.w)
            else:
                self.flat_k = 0; decision = "RISING"
        elif self.trigger == "new":
            if not self.warmed:
                if obs.new_unique > 0:
                    self.warmed = True; self.flat_k = 0; decision = "RISING"
                else:
                    self.warmup_k += 1
                    decision = self._dead_start(obs) if self.warmup_k >= self.warmup_limit else "WARMUP"
            elif obs.new_unique > 0:
                self.flat_k = 0; decision = "RISING"
            else:
                self.flat_k += 1; decision = self._close_or_wait(obs, R, self.w)
        else:  # "value" (v3)
            if not self.warmed:
                if obs.value > self.eps_val:
                    self.warmed = True; self.flat_k = 0; decision = "RISING(value)"
                else:
                    self.warmup_k += 1
                    decision = self._dead_start(obs) if self.warmup_k >= self.warmup_limit else "WARMUP"
            elif obs.value > self.eps_val:
                self.flat_k = 0; decision = "RISING(value)"
            else:
                self.flat_k += 1; decision = self._close_or_wait(obs, R, w_eff)

        self.last_value = obs.value
        self.r_prev = R
        self.decisions.append((obs.label, round(R, 3), None if dR is None else round(dR, 3),
                               f"{self.flat_k}/{w_eff}", round(obs.value, 1), decision))
        return decision

    def _close_or_wait(self, obs, R, w_eff):
        if self.flat_k >= w_eff:
            if R >= self.r_high:
                self.closed_at, self.closed_reason = obs.label, "swell (converged + valuable)"
                return "SWELL-CLOSE"
            self.closed_at, self.closed_reason = obs.label, "plateau (low value)"
            return "PLATEAU-CUT"
        return f"FLAT {self.flat_k}/{w_eff}"

    def _dead_start(self, obs):
        self.closed_at, self.closed_reason = obs.label, "plateau (no traction)"
        return "PLATEAU-CUT"

    @property
    def closed(self) -> bool:
        return self.closed_at is not None
