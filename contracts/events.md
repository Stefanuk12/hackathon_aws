# Realtime events

Transport: **AppSync Events**. Channel: `/rooms/<code>`.
Connection details come from the stack outputs `EventsHttpDomain`, `EventsRealtimeDomain` and `EventsApiKey`.
Fallback: poll `GET /rooms/{code}` every second.

Every event has the shape `{ "type": "<name>", ...payload }`.

| type | Payload | Sent when |
|---|---|---|
| `player_joined` | `{playerId, name}` | someone joins |
| `theme_intro` | `{round, roundMode, theme, themeEndsAt}` | a themed round starts (intro screen) |
| `round_started` | `{round, roundMode, prompt, endsAt}` | drawing/typing begins (straight away, or after `begin`) |
| `submission_in` | `{playerId, submitted, total}` | a drawing is submitted |
| `judging` | `{round}` | all players are in, or the timer ended |
| `results_ready` | `{round, results, outcome?, audioUrl}` | the judge state machine finishes (`outcome` when elimination is on) |
| `room_reset` | `{}` | host pressed "Play again" |

`results` has the same shape as in `fixtures/results.json`.
