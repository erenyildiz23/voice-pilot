"""Small smoke eval. This is NOT real call data.

The rules and this list were written by the same person, so the numbers are a regression
signal, not a performance claim. Re-run it on real (consented, redacted) call samples
during the pilot.

Run:  python eval/run_eval.py
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
tp = fp = fn = 0  # for handoff
leaks = 0
for row in rows:
    r = dm.handle(Session(), row["text"])  # a fresh session per row
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
print(f"Samples: {n}")
print(f"Intent accuracy: {intent_ok}/{n} = {intent_ok / n:.0%}")
print(f"Action accuracy (answer/clarify/handoff): {action_ok}/{n} = {action_ok / n:.0%}")
print(f"Missed handoffs: {fn} (handoffs required {tp + fn}); unnecessary handoffs: {fp}")
print(f"Personal data leaked in replies: {leaks}")
if wrong:
    print("\nWrong rows (text | expected intent | got | expected action | got):")
    for w in wrong:
        print("  ", " | ".join(w))
print("\nAction distribution:", dict(Counter(dm.handle(Session(), r["text"]).action for r in rows)))
sys.exit(1 if fn or leaks else 0)
