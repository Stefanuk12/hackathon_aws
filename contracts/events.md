# Realtime events

Transport: **AppSync Events**. Channel: `/rooms/<code>`.
Connection details come from the stack outputs `EventsHttpDomain`, `EventsRealtimeDomain` and `EventsApiKey`.
Fallback: poll `GET /rooms/{code}` every second.

Every event has the shape `{ "type": "<name>", ...payload }`.

| type | Payload | Sent when |
|---|---|---|
| `player_joined` | `{playerId, name}` | someone joins |
| `round_started` | `{round, prompt, endsAt}` | host starts a round |
| `submission_in` | `{playerId, submitted, total}` | a drawing is submitted |
| `judging` | `{round}` | all players are in, or the timer ended |
| `results_ready` | `{round, results, audioUrl}` | the judge state machine finishes |
| `room_reset` | `{}` | host pressed "Play again" |

`results` has the same shape as in `fixtures/results.json`.
