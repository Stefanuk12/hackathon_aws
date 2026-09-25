# AI Gartic Phone — AWS North x Northumbria Hackathon

A party game in the style of Gartic Phone. Bedrock writes the prompt, everyone draws it on their phone, and the AI ranks the drawings against the prompt. A game-show host voice (Polly) reads out the results and a roast of each drawing.

**Categories:** Traditional (party game), Digital worlds, Gamification

## Game loop

1. The host screen shows a QR code and room code. Players join on their phones.
2. Bedrock generates a prompt (themed, scaled by difficulty, no repeats).
3. Everyone draws before the timer runs out.
4. Bedrock vision ranks **all drawings in one call**. It scores recognisability, not art quality, and penalises written words.
5. The reveal shows each drawing's rank, score and one-line roast, read aloud by Polly.

**Stretch goals** (only once the core loop works end to end):
- **AI player:** Nova Canvas draws its own entry, which is mixed in anonymously and judged blind. Humans guess which drawing is the AI's.
- **Chain mode:** prompt → A draws → AI describes the drawing → B draws that description → … At the end, show how far the idea drifted.

## Architecture

```
Phones (HTML canvas) ──► CloudFront + S3 (static site)
   │
   ├─ join/submit ──► API Gateway (HTTP) ──► Lambda ──► DynamoDB
   │                                         └─► S3 presigned PUT (drawing JPEG)
   │
   ├─ live updates ◄── AppSync Events (fallback: poll GET /rooms/{code} every 1s)
   │
   └─ round end ──► Step Functions
                      ├─ Bedrock Claude (vision): rank all drawings + roasts → JSON
                      ├─ (stretch) Nova Canvas: AI's own entry
                      ├─ Polly: host voice MP3 → S3
                      └─ results → DynamoDB → publish results_ready
```

- Shrink drawings to about 512px JPEG on the client before upload.
- The judge uses the Bedrock Converse API with images labelled `Drawing 1..n` and returns strict JSON.

## Contracts (don't change these without telling the team)

### DynamoDB (single table)

| PK | SK | Attributes |
|---|---|---|
| `ROOM#<code>` | `META` | `state` (lobby \| drawing \| judging \| results), `round`, `prompt`, `endsAt` |
| `ROOM#<code>` | `PLAYER#<id>` | `name`, `score` |
| `ROOM#<code>` | `ROUND#<n>#<playerId>` | `s3Key`, `rank`, `score`, `roast` |

### HTTP API

```
POST /rooms                        → {code}
POST /rooms/{code}/join            {name} → {playerId}
POST /rooms/{code}/start           → {round, prompt, endsAt}
POST /rooms/{code}/upload-url      {playerId} → {url, key}
POST /rooms/{code}/submit          {playerId, key}
GET  /rooms/{code}                 → full room state (also the polling fallback)
```

### Realtime events (channel `/rooms/<code>`)

`player_joined` · `round_started` · `submission_in` · `judging` · `results_ready`

### Judge output

```json
{
  "results": [{ "playerId": "…", "rank": 1, "score": 8, "roast": "…" }],
  "audioUrl": "https://…"
}
```

## Team

| # | Role | Owns |
|---|---|---|
| 1 | **Player frontend** | Phone UI: join, drawing canvas (brush, colours, undo, clear), timer, resize and upload via presigned URL |
| 2 | **Host screen frontend** | Big-screen UI: lobby with QR code, countdown, results reveal with Polly audio |
| 3 | **Backend / infra** | CDK/SAM stack, DynamoDB, Lambdas, realtime events, hosting. **Only person 3 deploys** |
| 4 | **AI pipeline** | Prompt generation, judge prompt, Step Functions round-end flow, Polly, (stretch) Nova Canvas |
| 5 | **Lead / pitch / QA** | Adapting to the theme, timekeeping, architecture diagram, slides, testing on real phones, backup video, helping whoever is blocked. **Decides what gets cut** |

Frontends mock the API with hard-coded JSON until the backend is live. Person 4 tests the judge prompt on sample drawings before the backend exists.

## Timeline (development runs 10:30–4:00, judging 4:00)

| Time | Must be true |
|---|---|
| **10:45** | Contracts agreed, repo set up, Bedrock model access confirmed (Claude, Nova Canvas) in our region |
| **12:00** | Stack deployed (even if empty). Canvas uploads to S3. Judge returns sensible JSON on sample drawings |
| **1:30** | **First end-to-end round on real phones.** From here, integration is everyone's job |
| **2:30** | Reveal screen with audio. Diagram and slides drafted |
| **3:30** | **Feature freeze.** Full rehearsal, then record the backup demo video |
| **3:30–4:00** | Only fix bugs and rehearse the pitch |

**Minimum demo:** join by code → AI prompt → draw → AI ranking with roasts.

## Rules

- Merge to `main` at least every 30–45 minutes. No big integration at 3pm.
- If the 1:30 checkpoint slips, drop the stretch goals without debating it.
- **Pitch:** hand the judges the QR code and play a round straight away. Show the architecture diagram while Bedrock is judging.
