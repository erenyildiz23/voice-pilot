# 4. 30-day pilot plan

The success criteria are **proposals**; numeric thresholds are set with the customer against a baseline measured at the start of the pilot.

| Week | Goal | Output |
| --- | --- | --- |
| 1 | Discovery and data decision | Written answer to "can audio go to the cloud?", approved reply texts, sample call set |
| 2 | Shadow mode | The assistant listens but does not answer; its intent predictions are compared with the human agent's decision |
| 3 | Limited live | Only two in-scope intents, on a low-volume queue; handoff available on every call |
| 4 | Evaluation | Measurement report and go/no-go decision |

## What we measure

- Share of in-scope calls the assistant resolves on its own
- Missed handoffs on security intents (card loss, complaints). Target: zero
- Personal data leaks in logs and replies. Target: zero
- STT word error rate (on a real call sample)
- p95 latency per turn (STT + processing + TTS)
- Number of details the agent has to ask again after a handoff

## Stop conditions

A detected leak, a missed handoff on a security intent, or an objection from the customer's legal team stops the pilot immediately.
