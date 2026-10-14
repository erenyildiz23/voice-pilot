# 5. First run with ElevenLabs

The first run against the live service was done on 14 October 2026 (results at the bottom). When setting it up again, check:

1. Copy `.env.example` to `.env` and start the server with `--env-file .env` (otherwise `.env` is not read). Fill in `PROVIDER=elevenlabs`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`. Set `ALLOW_CLOUD_AUDIO=true` for testing. Do not test with real customer data.
2. Check model names against the current docs (`ELEVENLABS_STT_MODEL`, `ELEVENLABS_TTS_MODEL`). Defaults: `scribe_v2`, `eleven_multilingual_v2`.
3. Check which code `ELEVENLABS_STT_LANGUAGE` accepts for Turkish; leave it empty for automatic language detection.
4. Send about 10 short recordings of your own voice (`curl -F file=@sample.wav localhost:8000/v1/turn/audio`) and check the transcript in the `transcript_redacted` field.
5. Decode the returned `audio_b64` and listen to it (`base64 -d`).
6. Failure cases: confirm that a wrong key returns 502 and that the provider's error body does not leak into the response.

Fix any differences in `src/pilot/providers.py` and update the related test.

## First run results (14 October 2026, free plan)

| Check | Result |
| --- | --- |
| Is `.env` read? | **No** on the first attempt: the app only read environment variables. Fixed with `--env-file .env` + `python-dotenv` |
| Wrong key (the key ID was pasted instead of the key) | ElevenLabs 400 `invalid_api_key`; the API returned **502** and the error body did not leak ✓ |
| Library voice ("Şevval") | **402 `paid_plan_required`**: the free plan does not allow library voices via the API. Continued with the premade voice "Sarah"; later the paid plan was enabled and "Şevval" works. In a customer pilot, voice choice is a plan/licence decision |
| Text turn + TTS | 200, valid MP3 (~117 KB) ✓ |
| Audio turn: STT (`scribe_v2`) → redaction → intent → TTS | 3/3 correct: "kaybetmedim ama çalındı" (didn't lose it but it was stolen) → handoff; "Adım Ayşe Demir…" (my name is…) → name masked, answered; spoken national ID → masked, handoff ✓ |
| Raw data leak (API response + audit log) | None ✓ |
| Turn latency (STT + processing + TTS, from a local machine) | 4.8–5.4 s. **Too slow for phone**; try streaming STT/TTS and a faster model (`eleven_flash_v2_5`) in the pilot |
| `ELEVENLABS_STT_LANGUAGE` | Left empty; the language was detected automatically and Turkish came out correctly |
