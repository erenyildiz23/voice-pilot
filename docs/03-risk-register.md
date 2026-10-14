# 3. Risk register

| # | Risk | Impact | Mitigation | Status |
| --- | --- | --- | --- | --- |
| 1 | Audio goes to the cloud; redaction cannot protect audio | Breach of KVKK and of the customer's requirement | `ALLOW_CLOUD_AUDIO=false` by default; customer approval, legal review, verified provider contract and retention terms; or an on-prem model | Open, customer decision |
| 2 | Caller says their ID or card number | Personal data leaks to logs and providers | Masking of digits and spoken digits; handoff when sensitive data appears | Partly mitigated (limits below) |
| 3 | STT mis-transcribes Turkish phone audio | Wrong intent, poor experience | Clarify on low confidence, then hand off; measure WER on real calls in the pilot | To be measured |
| 4 | Negation is misread | A real loss mistaken for "I didn't lose it" is not handed off | An intent is skipped only if every occurrence of the security keyword is negated; "değil mi" (tag question) is not a negation; skipped intents are written to the audit log. In shadow mode, `negated:*` rows are compared one by one with the human decision | Partly mitigated, to be measured on real audio |
| 5 | A generative model gives wrong information | Reputational and legal risk | No generative replies in the pilot, approved templates only | Closed |
| 6 | Provider outage / latency | Call drops, caller waits in silence | Hand off on error (502 verified); first measurement 4.8–5.4 s per turn, too slow for phone. Try streaming STT/TTS and a faster model | Measured, needs work |
| 7 | Missing caller notice / consent | KVKK | Approved notice at the start of the call | Waiting for customer text |
| 8 | In-memory sessions are lost on restart | Handoff context lost | Accepted for the pilot; external session store in production | Known |
| 9 | Voice licence / plan limits | The chosen voice returns 402 from the API | Agree the voice with the customer together with the plan and licence; keep a premade voice as fallback | Hit during the first run |
| 10 | Account data (balance) goes to cloud TTS | Even after authentication, personal financial data leaves to a third party (KVKK) | Demo mode uses made-up balances only; in a real integration use on-prem TTS or pre-recorded digit audio for amounts (no numbers sent to TTS) | Design decision, with the customer |

## Known limits of the redaction

- Catches national ID (TCKN), IBAN, card (Luhn), phone, email, runs of 9+ spoken digits and full names after a cue ("adım ...", "ismim ...", "Ayşe Hanım"). Names without a cue, addresses and dates of birth are not caught.
- Digits glued into a word ("sifirbes...") or split into spoken chunks shorter than 9 digits can slip through.
