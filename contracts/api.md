# HTTP API

Base URL: the `ApiUrl` output from the SAM stack. All bodies are JSON. CORS is open.

| Method | Path | Body | Response | Fixture |
|---|---|---|---|---|
| POST | `/rooms` | – | `{code}` | `create_room.json` |
| POST | `/rooms/{code}/join` | `{name}` | `{playerId}` | `join_room.json` |
| GET | `/rooms/{code}` | – | full room state | `room.json` |
| POST | `/rooms/{code}/start` | `{totalRounds?, mode?}` | `{round, prompt, endsAt}` | `start_round.json` |
| POST | `/rooms/{code}/upload-url` | `{playerId}` | `{url, key}` | `upload_url.json` |
| POST | `/rooms/{code}/submit` | `{playerId, key}` or `{playerId, text}` | `{ok}` | – |
| POST | `/rooms/{code}/end` | – | `{ok}` | – |
| POST | `/rooms/{code}/reset` | – | `{ok}` | – |

## Notes

- `endsAt` is a Unix timestamp in milliseconds.
- **Game modes:** `start` from the `lobby` may send `{mode}`: `"draw"`, `"survive"`, `"wit"` or `"mixed"` (default `"mixed"`). The room returns it as `mode`, and each round's actual mode as `roundMode`. In `"mixed"`, round *n* uses `["draw", "survive", "wit"][(n - 1) % 3]`.
  - `draw`: players upload a drawing (`upload-url` → PUT → `submit {key}`).
  - `survive` (Death by AI style) and `wit` (Quiplash style): players type an answer and `submit {text}` (max 200 chars, no upload).
  - Results have `imageUrl` in draw rounds and `text` in survive/wit rounds. Survive results also have `survived: true | false`.
- **Rounds:** the room has `totalRounds` (default 3). `start` from the `lobby` may send `{totalRounds}` (1–10) to set it; the value is ignored on later rounds. After the last round's results, `start` fails with **409**. The host shows final scores and calls `reset` instead.
- `reset` goes back to `lobby`: `round` = 0, every player's `score` = 0, players are kept. The host uses it for "Play again".
- `upload-url` returns a presigned S3 **PUT** URL. Upload with `Content-Type: image/jpeg`, then call `submit` with the returned `key`.
- Judging starts when **every player has submitted**, or when the host screen calls `/end` once the timer reaches 0, whichever comes first. The transition from `drawing` to `judging` happens exactly once, so calling `/end` twice is harmless.
- Once judging finishes, `GET /rooms/{code}` includes `results` (see `results.json`).

## Room states

`lobby` → `drawing` → `judging` → `results` → (`start` again, while `round < totalRounds`) → `drawing` …

After the final `results`: `reset` → `lobby`.
