"""Sahte çekirdek bankacılık servisi (yalnızca demo).

Gerçek entegrasyonda bu modülün yerini müşterinin hesap API'si alır; arayüz
(verify_pin, balance) aynı kalır. Buradaki bakiyeler UYDURMADIR ve gerçek bir
hesaba ait değildir.
"""
from __future__ import annotations

import hashlib

DEMO_PIN = "1234"  # Demo telefon bankacılığı şifresi; gerçek şifre değildir.


def verify_pin(pin: str) -> bool:
    return pin == DEMO_PIN


def balance(session_id: str) -> tuple[int, int]:
    """Oturuma göre sabit ama rastgele görünen demo bakiye: (lira, kuruş)."""
    h = int(hashlib.sha256(session_id.encode()).hexdigest(), 16)
    return 500 + h % 49_500, (h // 49_500) % 100


def format_tl(lira: int, kurus: int) -> str:
    return f"{lira:,}".replace(",", ".") + f" lira {kurus} kuruş"
