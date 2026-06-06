# SPDX-License-Identifier: AGPL-3.0-or-later
# Cairn — passive stigmergic blackboard.  © 2026 Tağmaç Çankaya
"""The shared surface agents coordinate THROUGH — by leaving traces, not messages.

No agent-to-agent conversation channel: a worker reads a compact *digest* of what
others have left and appends its own short trace. Coordination emerges from a
shared filter, not chatter. The digest is deliberately small — that is the
token lever: each worker carries a bounded view, never the full transcript.
"""
from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class Trace:
    """One mark left on the blackboard. Short by design (a claim/finding/status),
    never a conversation turn."""
    agent: str
    kind: str = "finding"        # "claim" | "finding" | "status"
    text: str = ""
    value: float = 0.0           # information value (0 = repeat/chatter; high = a real find)
    anchored: bool = False       # did this converge on a shared anchor another worker set?
    ts: float = field(default_factory=time.time)

    def line(self) -> str:
        a = "*" if self.anchored else " "
        return f"[{self.agent}|{self.kind}|v{self.value:g}]{a} {self.text}".rstrip()


class Blackboard:
    """Append-only shared store. Workers read `digest()` (bounded) and `append()` traces."""

    def __init__(self, path: Optional[str | Path] = None):
        self.traces: list[Trace] = []
        self.path = Path(path) if path else None
        if self.path and self.path.exists():
            self._load()

    def append(self, trace: Trace) -> Trace:
        self.traces.append(trace)
        if self.path:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(trace), ensure_ascii=False) + "\n")
        return trace

    def digest(self, max_chars: int = 1200, recent: int = 20) -> str:
        """Compact view a worker reads — the LAST `recent` traces, capped at `max_chars`.
        Bounded ON PURPOSE: this is the minimal cross-agent context, not the full history."""
        lines = [t.line() for t in self.traces[-recent:]]
        out: list[str] = []
        total = 0
        for ln in reversed(lines):           # newest first; stop when budget hit
            if total + len(ln) + 1 > max_chars:
                break
            out.append(ln); total += len(ln) + 1
        return "\n".join(reversed(out))

    def findings(self) -> list[Trace]:
        return [t for t in self.traces if t.kind == "finding"]

    def total_value(self) -> float:
        return sum(t.value for t in self.traces)

    def _load(self) -> None:
        for raw in self.path.read_text(encoding="utf-8").splitlines():
            raw = raw.strip()
            if raw:
                try:
                    self.traces.append(Trace(**json.loads(raw)))
                except Exception:
                    pass

    def __len__(self) -> int:
        return len(self.traces)
