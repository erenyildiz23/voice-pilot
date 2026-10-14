"""Küçük dumanlı test (smoke eval). Gerçek çağrı verisi DEĞİLDİR.

Kuralları ve bu listeyi aynı kişi yazdı; çıkan sayılar performans iddiası değil,
regresyon göstergesidir. Pilotta gerçek (izinli, maskelenmiş) çağrı örnekleriyle
yeniden çalıştırılmalıdır.

Çalıştır:  python eval/run_eval.py
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from pilot.dialogue import DialogueManager, Session  # noqa: E402
from pilot.pii import redact  # noqa: E402

rows = list(csv.DictReader((ROOT / "eval" / "utterances_tr.csv").open(encoding="utf-8")))
dm = DialogueManager()

intent_ok = action_ok = 0
wrong: list[tuple[str, str, str, str, str]] = []
tp = fp = fn = 0  # handoff için
leaks = 0
for row in rows:
    r = dm.handle(Session(), row["text"])  # her satır yeni oturum
    intent_ok += r.intent == row["expected_intent"]
    action_ok += r.action == row["expected_action"]
    if r.action != row["expected_action"] or r.intent != row["expected_intent"]:
        wrong.append((row["text"], row["expected_intent"], r.intent, row["expected_action"], r.action))
    exp_h, got_h = row["expected_action"] == "handoff", r.action == "handoff"
    tp += exp_h and got_h
    fp += (not exp_h) and got_h
    fn += exp_h and (not got_h)
    _, found = redact(r.reply)
    leaks += sum(found.values())

n = len(rows)
print(f"Örnek sayısı: {n}")
print(f"Niyet doğruluğu: {intent_ok}/{n} = {intent_ok / n:.0%}")
print(f"Eylem doğruluğu (answer/clarify/handoff): {action_ok}/{n} = {action_ok / n:.0%}")
print(f"Devir (handoff) kaçırma: {fn} (gereken devir {tp + fn}); gereksiz devir: {fp}")
print(f"Yanıtlarda kişisel veri sızıntısı: {leaks}")
if wrong:
    print("\nHatalı satırlar (metin | beklenen niyet | bulunan | beklenen eylem | bulunan):")
    for w in wrong:
        print("  ", " | ".join(w))
print("\nEylem dağılımı:", dict(Counter(dm.handle(Session(), r["text"]).action for r in rows)))
sys.exit(1 if fn or leaks else 0)
