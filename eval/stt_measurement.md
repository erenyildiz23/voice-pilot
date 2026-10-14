# STT measurement: synthetic Turkish audio (14 October 2026)

**Method:** The sentences the prototype finds riskiest were voiced with ElevenLabs TTS (`eleven_multilingual_v2`, voice "Şevval - Call Center"), then transcribed with ElevenLabs STT (`eleven_scribe_v1`). The transcripts were run through `DialogueManager`. Raw data: [stt_measurement.csv](stt_measurement.csv).

**What this does not show:** The audio is clean, studio quality and comes from the same vendor's TTS. It is not real phone audio (8 kHz, noise, accents, cut-off sentences). The result is the **best case**, not a production performance claim.

## Result

| Metric | Result |
| --- | --- |
| Sentences | 8 (10 planned; 2 were not run for budget reasons, see below) |
| Word error rate (after tr_fold) | 0/48 = 0% |
| Correct intent + action | 8/8 |
| Missed security handoffs | 0 |

## What we actually learned

1. **The negative suffix survives.** "kaybet**me**dim" (I did not lose) was not dropped by STT, so the assumption the negation logic relies on holds on clean audio. It must be measured separately on phone audio (risk 4).
2. **Spoken digits were not converted to numbers.** Scribe kept "bir iki üç ..." (one two three ...) as words, so the spoken `digit_sequence` mask caught the national ID, not the TCKN checksum. If an STT setting or model change starts producing digits, the `national_id` mask applies instead; both paths are tested.
3. **The full name came with punctuation** ("Adım Ayşe Demir,") and was masked; the intent (`loan_info`) was kept.
4. **The audio was in the cloud.** In this measurement audio reached ElevenLabs before redaction. That is why it used only synthetic test sentences, never real customer audio (risk 1).

## Cost and incident notes

- Voicing cost 20–65 credits per sentence; transcription was estimated at ~33 credits per sentence.
- Parallel requests through the connector returned 429 (rate limit); sending one at a time worked.
- While transcribing sentence 8, the platform regenerated the audio and showed a 416-credit price for the transcription. Because of the risk of exceeding the agreed budget, the remaining 2 sentences ("Hiç memnun değilim, temsilciyle görüşmek istiyorum" = I'm not happy at all, I want an agent; "Hesabımda ne kadar param var?" = how much money is in my account?) were not run.
- **Lesson (FDE view):** In a customer environment too, provider billing and rate limits should be measured on day one of the pilot; the estimate and the actual cost can differ.

## Next measurement

During the shadow-mode week, the same table on **consented, redacted real phone recordings**: WER, loss of negative suffixes, digits vs. words, and per-turn latency.
