# HTTP API

Base URL: the `ApiUrl` output from the SAM stack. All bodies are JSON. CORS is open.

| Method | Path | Body | Response | Fixture |
|---|---|---|---|---|
| POST | `/rooms` | – | `{code}` | `create_room.json` |
| POST | `/rooms/{code}/join` | `{name}` | `{playerId}` | `join_room.json` |
| GET | `/rooms/{code}` | – | full room state | `room.json` |
| POST | `/rooms/{code}/start` | `{totalRounds?, mode?, elimination?, reviveAfter?, themeEvery?}` | `{round, prompt, endsAt}` | `start_round.json` |
| POST | `/rooms/{code}/upload-url` | `{playerId}` | `{url, key}` | `upload_url.json` |
| POST | `/rooms/{code}/submit` | `{playerId, key}` (draw) or `{playerId, text}` (learn/wit) | `{ok}` | – |
| POST | `/rooms/{code}/end` | – | `{ok}` | – |
| POST | `/rooms/{code}/reset` | – | `{ok}` | – |
| POST | `/rooms/{code}/begin` | – | `{ok}` | – |

## Notes

- `endsAt` is a Unix timestamp in milliseconds.
- **Game modes:** `start` from the `lobby` may send `{mode}`: `"draw"`, `"learn"`, `"wit"` or `"mixed"` (default `"mixed"`). The room returns it as `mode`, and each round's actual mode as `roundMode`. In `"mixed"`, round *n* uses `["draw", "learn", "wit"][(n - 1) % 3]`.
  - `draw`: players upload a drawing (`upload-url` → PUT → `submit {key}`).
  - `learn` (an AWS quiz) and `wit` (Quiplash style): players type an answer and `submit {text}` (max 200 chars, no upload).
  - Results have `imageUrl` in draw rounds and `text` in learn/wit rounds.
- **Elimination** (optional, works with any mode): `start` from the `lobby` may send `{elimination: true, reviveAfter: 1-5}` (defaults `false`, `2`). The room returns `elimination` and `reviveAfter`; players get `alive` and `streak` (good rounds in a row while dead).
  - After each round the lowest-scoring **living** player dies; non-submitters score 0. Ties at the bottom all die, unless that would kill everyone alive (then nobody dies).
  - Dead players ("ghosts") keep playing for **half points** (rounded down). A score of **6+** extends their streak, anything lower resets it; at `reviveAfter` in a row they revive.
  - Results gain `points` (what was added to the total) and `ghost: true` for dead players. In `results`, the room has `outcome: {eliminated: [playerId], revived: [playerId]}`.
  - The rules are implemented in `backend/src/shared/elimination.py` (`apply_elimination`) and mirrored in `frontend/src/elimination.ts`; `backend/scripts/test_elimination.py` covers both.
- **Themed rounds** (AWS services): `start` from the `lobby` may send `{themeEvery}`: `0` off, `1` every round, `2` every 2nd round (rounds 1, 3, 5…; default `2`).
  - A themed round starts in state **`theme`**: the room has `theme` (an entry from `backend/src/shared/themes.json` without `promptHint`/`examples`) and `themeEndsAt`. The prompt is already chosen, and it fits the theme.
  - The host screen shows the intro and calls **`begin`** when `themeEndsAt` passes or the host presses Skip. Then state becomes `drawing` with a fresh `endsAt`. `begin` only acts in `theme`, so calling it twice is harmless.
  - `theme` stays on the room until the next round starts, so the round and reveal screens can show a theme badge.
- **Rounds:** the room has `totalRounds` (default 3). `start` from the `lobby` may send `{totalRounds}` (1–10) to set it; the value is ignored on later rounds. After the last round's results, `start` fails with **409**. The host shows final scores and calls `reset` instead.
- `reset` goes back to `lobby`: `round` = 0, every player's `score` = 0, players are kept. The host uses it for "Play again".
- `upload-url` returns a presigned S3 **PUT** URL. Upload with `Content-Type: image/jpeg`, then call `submit` with the returned `key`.
- Judging starts when **every player has submitted**, or when the host screen calls `/end` once the timer reaches 0, whichever comes first. The transition from `drawing` to `judging` happens exactly once, so calling `/end` twice is harmless.
- Once judging finishes, `GET /rooms/{code}` includes `results` (see `results.json`).

## Room states

`lobby` → (`theme` →) `drawing` → `judging` → `results` → (`start` again, while `round < totalRounds`) → (`theme` →) `drawing` …

After the final `results`: `reset` → `lobby`.
