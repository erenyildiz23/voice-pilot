# Developer notes

Turkish voice assistant pilot for a call centre: a prototype that does not leak personal data and hands off to a human when unsure.

## Commands
- Tests: `python -m pytest -q`
- Smoke eval: `python eval/run_eval.py` (exit code 1 on any leak or missed handoff)
- Server: `PYTHONPATH=src uvicorn pilot.app:app --reload --env-file .env` (demo page at `/`)

## Invariants (do not break)
1. The classifier, logs and TTS never see raw text, only the output of `pii.redact`.
2. Replies are template variants from `dialogue.FAQ` / `HANDOFF_REPLIES`; they never echo caller input. The only dynamic value is the demo balance from `mockbank` after PIN authentication.
3. Anything uncertain goes to a human. Security intents (`card_security`, `complaint`) are never answered automatically.
4. The raw transcript is never returned by the API.
5. The audio endpoint does not work without `ALLOW_CLOUD_AUDIO=true`. Do not change this default.
6. A keyed-in PIN never appears in a reply, a log line or TTS text; anything said while a PIN is expected is not logged. `MOCK_BANKING` defaults to `false`.

## Conventions
- Use `intents.tr_fold` for Turkish text matching (Turkish İ/ı and diacritics); `str.lower()` alone is not enough.
- Never commit real personal data, keys or call recordings. Test data is synthetic and algorithmically valid.
- When adding an intent, add examples to `tests/test_intents.py` and `eval/utterances_tr.csv`.
- The FAQ texts are demo content; do not present them as authoritative until the customer approves them.
- The assistant's replies and the matching rules are Turkish on purpose; code, comments and docs are English.

## Next steps
- Turn latency is 4.8–5.4 s: try streaming STT/TTS and `eleven_flash_v2_5`, measure p95
- Negation and cue-based name masking are done; validate `negated:*` rows against real data in shadow mode
- Name masking without cues and address masking (e.g. an on-prem NER model, so data never leaves)
- Telephony (SIP) integration
