"""Denetim kaydı. Yalnızca maskelenmiş metin yazılır; ham metin ve ses asla yazılmaz."""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .dialogue import TurnResult


class AuditLog:
    def __init__(self, path: str | Path | None):
        self.path = Path(path) if path else None
        self._lock = threading.Lock()

    def write(self, r: TurnResult, channel: str) -> None:
        if self.path is None:
            return
        entry = {
            "ts": round(time.time(), 3),
            "session_id": r.session_id,
            "channel": channel,
            "intent": r.intent,
            "action": r.action,
            "reasons": list(r.reasons),
            "redacted_input": r.redacted_input,
            "pii_counts": r.pii_found,
        }
        with self._lock, self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
