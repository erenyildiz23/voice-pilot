# Case study 1: A Turkish voice assistant pilot in a customer environment

*Target role: Forward Deployed Engineer. One-page summary; details in docs 01–05.*

## Context

A mid-sized financial institution in Turkey ("Demo Finans", fictional) wants a Turkish voice assistant to handle simple questions coming into its call centre. Constraint: customer data must not leave the institution's environment (KVKK, Turkey's data protection law).

## Problem

The real question is not "how smart is the assistant" but **"what can it safely do on its own, and what must it leave to a human"**. Cloud STT/TTS is the easiest technical path, but it directly conflicts with "data cannot leave": audio reaches the provider before any redaction can run. So the first deliverable was not code but discovery questions (see [01-discovery-note.md](01-discovery-note.md)).

## Decisions and why

| Decision | Why |
| --- | --- |
| Audio endpoint **off** by default (`ALLOW_CLOUD_AUDIO=false`) | Whether audio may go to the cloud is the customer's and legal team's call. The code cannot leave it on by accident. The text channel (the IVR's own STT) works without approval |
| No generative model, approved templates only | Replies never echo the caller, so no personal data can reach TTS or logs. The risk of wrong information drops to zero |
| Redaction before everything else | The classifier, audit log and API response only see redacted text. Checksums for national ID/IBAN/card (fewer false positives), spoken digit runs, names after a cue |
| Security intents hand off on the first turn | Card loss, unauthorised transactions, complaints, balance and shared personal data are never answered automatically. Out-of-scope banking requests are handed off without an "I didn't understand" loop |
| Negation handling biased to the safe side | "Kartımı kaybetmedim" (I didn't lose my card) is not handed off, but "kaybetmedim ama çalındı" (didn't lose it, but it was stolen) is: one non-negated match is enough. Skipped intents are logged as `negated:*` for human review in shadow mode |
| Balance only behind authentication | In demo mode the caller keys in a PIN (never logged, never spoken back), then a mock core-banking service returns a made-up balance. This mirrors the real integration point instead of having the assistant invent account data |
| Rule-based classifier | In the first pilot week the goal is to measure which intents can be automated on real call data. The `classify()` interface is fixed; a model replaces it once data arrives |
| `SpeechProvider` interface | ElevenLabs in the cloud, a mock offline. If the customer says audio cannot leave, an on-prem STT/TTS plugs into the same interface and nothing else changes |

## Measured results

- **76 automated tests** pass: redaction, intents, negation, dialogue policy, keypad menu, PIN flow, API, no raw data in the audit log.
- **Smoke eval: 50/50, 0 missed handoffs, 0 leaks.** This is *not* a performance claim: the same person wrote the rules and the sentences.
- The more honest number: on **11 new sentences** tried after the rules were written, **4 security misses** came up (e.g. "birisi kartımla alışveriş yapmış" = someone used my card, was not handed off on the first turn). Fixed and added to the set. Lesson: the blind spots of a rule-based system are only found with real call data; that is exactly what the shadow-mode week of the 30-day plan is for.
- **Synthetic audio measurement:** 8 risky sentences voiced with ElevenLabs TTS went through Scribe STT: 0% WER, 8/8 correct decisions. The negative suffix ("kaybet-me-dim") survived; a spoken national ID came back as words, not digits, and was caught by the spoken-digit mask ([details](../eval/stt_measurement.md)). Clean studio audio, so this is the best case.
- **End to end against the live service:** with the prototype connected to ElevenLabs, audio → STT → redaction → intent → TTS turns worked; latency was 4.8–5.4 s per turn. That is too slow for phone; streaming STT/TTS is the next step. The first setup surfaced two real problems: the app was not reading `.env`, and the free plan rejected a library voice via the API (402). Both are documented.
- **End-to-end browser test:** a scripted run of the demo page found two bugs that unit tests missed: PINs starting with 0 could not be entered (0 was the "agent" key), and a late reply from a previous call could hijack a new call. Both fixed and covered by tests.
- **What I could not measure:** accuracy on phone audio (8 kHz). That needs consented real call recordings.

## What I would do differently

- I would not draw an architecture before getting the answer to **"can audio go to the cloud?"** in the first customer meeting. If the answer is no, time spent on cloud integration is wasted; I would start with an on-prem Whisper-style STT.
- Instead of writing the eval set myself, I would ask the customer for **a few hundred redacted real turns** from day one. 100% on my own sentences versus 4 misses out of 11 on the first unfamiliar ones shows why.
- I would handle negation and name masking with a small Turkish NER/classifier running inside the institution instead of regex, but only decide that after comparing against shadow-mode data.

## How to try it

```bash
pip install -r requirements.txt
python -m pytest -q && python eval/run_eval.py
PYTHONPATH=src uvicorn pilot.app:app --port 8000   # http://localhost:8000
```
