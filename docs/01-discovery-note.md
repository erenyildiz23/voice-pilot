# 1. Discovery note

This note is the agenda for the first meeting with the customer. These questions are answered before any code is written; the answers can change the architecture.

**Scenario (assumption):** A mid-sized financial institution wants a Turkish voice assistant to handle simple questions coming into its call centre. Customer data must not leave the institution's environment (Turkey's data protection law, KVKK). The scenario is illustrated with "Demo Finans", a fictional institution.

## Five questions to answer first

1. **Can audio go to the cloud?** Does "data cannot leave" apply only to text, or to call audio as well? If the answer is no, cloud STT/TTS cannot be used in the pilot; an on-prem model or a text-only channel is needed. In this project the audio endpoint is off by default (`ALLOW_CLOUD_AUDIO=false`).
2. **Which calls are in scope?** Suggested first scope: branch opening hours and general loan application information. Anything that needs authentication (balance, transactions) is out of the pilot and handed to a human.
3. **How are callers informed?** Who owns the approved text that tells the caller, at the start of the call, that it is recorded and handled by an automated assistant?
4. **What is the telephony stack?** SIP/IVR provider, audio codec (8 kHz phone audio lowers STT accuracy), and how the assistant transfers a call (transfer API).
5. **How is success measured?** Can the customer provide a consented, redacted sample of real call recordings?

## Out of scope (deliberately not in the pilot)

- Authentication and account lookups
- Free-form chat / generative replies (replies are approved fixed texts)
- Real telephony integration (SIP). The prototype receives audio/text over HTTP.

## What we need from the customer

- Approved reply texts (the `FAQ` in the code is demo content)
- Handoff rules: when, and to which queue
- A sample of call transcripts (redacted), at least a few hundred turns
