# Turkish voice assistant pilot in a customer environment

A working prototype for case study 1: a Turkish voice assistant for a bank call centre. The focus is not **how smart it is** but **what it does safely on its own and what it leaves to a human**.

## Demo (under 2 min, with sound)

https://github.com/user-attachments/assets/1fa5927b-ccfa-4e4f-945a-ac5c28a66d56

If the player does not load: [MP4 file (2.4 MB)](docs/media/demo.mp4)

| Time | What happens | What it shows |
| --- | --- | --- |
| 0:00 | "Merhaba" (hello) → greeting + keypad menu, caller presses 1 → branch hours | Reply variants, DTMF menu |
| 0:19 | "Kartımı kaybetmedim" (I didn't lose my card) → no handoff, clarification | Negation (`negated:card_security`) |
| 0:38 | "Bakiyemi öğrenmek istiyorum" (I want my balance) → PIN keyed in (••••) → demo balance → 9 to end | Authentication; the PIN stays `[PIN]` in the log |
| 1:41 | "Adım Ahmet Yılmaz, kartım çalındı" (my name is …, my card was stolen) → name masked, handed to card security | Name masking, immediate handoff on a security intent |

The video was recorded against the live service with a scripted browser run: the assistant's voice is ElevenLabs TTS ("Şevval"), the caller is a second Turkish ElevenLabs voice; the typed text stands for what the caller says. The few seconds of waiting between replies is **real TTS latency** (see [first run results](docs/05-first-run.md)). Balances are made up.

## What it does

- Personal data (national ID, IBAN, card, phone, email, spoken digit runs, names after a cue) is redacted before classification, logging and TTS.
- Intents that need security or authentication (card loss/fraud, complaints, balance) go straight to a human. Out-of-scope banking requests (limits, passwords, transfers) are handed off without an "I didn't understand" loop.
- Negation is understood: "kartımı kaybetmedim" (I didn't lose my card) is not handed off but is logged as `negated:card_security`; "kaybetmedim ama çalındı" (didn't lose it, but it was stolen) is still handed off.
- Two consecutive misunderstood turns trigger a handoff. Replies are approved fixed templates; there is no generative model.
- Each intent has a few approved reply variants (same information, different wording). The greeting and "didn't understand" replies offer a keypad menu: 1 branch hours, 2 loans, 3 balance (demo mode), 0 agent, 9 goodbye.
- **Demo banking mode** (`MOCK_BANKING=true`, off by default): a balance request first asks for a 4-digit PIN (demo PIN `1234`), then reads a **made-up** balance from a mock account service (`mockbank.py`). The PIN never appears in replies or logs; a spoken PIN is refused and not logged; two wrong PINs trigger a handoff; `*` reaches an agent from the PIN prompt. Card security and complaints are never answered automatically, in this mode too.
- The audio endpoint is **off** by default: audio would go to a cloud STT, which needs customer approval.

The assistant speaks Turkish, so reply templates, matching rules and the sample caller phrases are Turkish; code, comments and docs are English.

## Quick start (offline, mock provider)

```bash
pip install -r requirements.txt
python -m pytest -q
python eval/run_eval.py
PYTHONPATH=src uvicorn pilot.app:app --port 8000 --env-file .env   # drop the flag if there is no .env; demo page at http://localhost:8000
curl -s localhost:8000/v1/turn -H 'content-type: application/json' \
  -d '{"text":"Şubeniz saat kaçta açılıyor","with_audio":true}'
```

To use the live ElevenLabs service, copy `.env.example` to `.env` and follow [docs/05-first-run.md](docs/05-first-run.md).

## What was tested, and what was not

| Area | Status |
| --- | --- |
| Redaction, intents, negation, dialogue, keypad menu, PIN flow, API, demo page, audit log | 76 unit/endpoint tests pass |
| End to end with ElevenLabs | Run against the live service: text+TTS and audio→STT→redaction→TTS turns work; a wrong key returns 502 with no leak. Latency 4.8–5.4 s per turn ([details](docs/05-first-run.md#first-run-results-14-october-2026-free-plan)) |
| End to end in a browser | A scripted Chrome run found two bugs unit tests missed (PINs starting with 0; a late reply hijacking a new call). Both fixed and covered by tests |
| Turkish STT/TTS quality | Measured on clean synthetic audio: 0% WER on 8 sentences, 8/8 correct decisions ([eval/stt_measurement.md](eval/stt_measurement.md)). **Not measured on phone audio**; this is the best case |
| Smoke eval | 50 of 50 correct. **Not a performance claim**: the same person wrote the rules and the sentences. Must be re-measured on real call data |
| Out-of-set probe | 11 new sentences tried after the rules were written found 4 security misses ("birisi kartımla alışveriş yapmış" = someone used my card, "kartımı unuttum" = I left my card, "memnun değilim" = I'm not happy, "kimse ilgilenmedi" = nobody helped me). Fixed and added to the set; it shows that the blind spots of a rule-based approach are found with real data |

## Known limitations

- Negation is detected through suffix and auxiliary-verb patterns. If STT drops the negative suffix ("-me-"), the sentence reads as positive and is handed off (safe side). The opposite risk: if STT wrongly adds "-me-", a handoff is missed. Must be measured on real audio (risk 4).
- Names are only caught after a cue ("adım", "ismim", "Ahmet Bey"). "Ben Ahmet" (I'm Ahmet) and addresses are not masked.
- Broad keywords like "limit" also hand off unrelated sentences such as "limitsiz internet paketi" (unlimited data plan) (safe side).
- Sessions are kept in memory.

## Documents

0. [One-page case study](docs/00-case-study.md)
1. [Discovery note](docs/01-discovery-note.md)
2. [Architecture](docs/02-architecture.md)
3. [Risk register](docs/03-risk-register.md)
4. [30-day pilot plan](docs/04-30-day-pilot-plan.md)
5. [First run with ElevenLabs](docs/05-first-run.md)
6. [Developer notes](docs/developer-notes.md)
