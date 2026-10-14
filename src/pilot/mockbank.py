"""Mock core-banking service (demo only).

In a real deployment the customer's account API replaces this module; the interface
(verify_pin, balance) stays the same. The balances here are MADE UP and belong to no
real account.
"""
from __future__ import annotations

import hashlib

DEMO_PIN = "1234"  # Demo phone-banking PIN; not a real credential.


def verify_pin(pin: str) -> bool:
    return pin == DEMO_PIN


def balance(session_id: str) -> tuple[int, int]:
    """Demo balance that looks random but is stable per session: (lira, kuruş)."""
    h = int(hashlib.sha256(session_id.encode()).hexdigest(), 16)
    return 500 + h % 49_500, (h // 49_500) % 100


def format_tl(lira: int, kurus: int) -> str:
    # Spoken Turkish format, e.g. "12.480 lira 35 kuruş".
    return f"{lira:,}".replace(",", ".") + f" lira {kurus} kuruş"
