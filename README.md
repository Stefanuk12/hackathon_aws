# Amacide — AWS North x Northumbria Hackathon

**Amacide** is a party game in the style of Gartic Phone and Death by AI. Bedrock writes the prompt, everyone answers it on their phone, and the AI ranks the answers against the prompt. A game-show host voice (Polly) reads out the results and a roast of each answer.

**Categories:** Traditional (party game), Digital worlds, Gamification

## Game modes

The host picks a mode in the lobby, along with the number of rounds.

| Mode | Prompt example | Players | The AI judges |
|---|---|---|---|
| 🎨 **Draw** | "A penguin running a lemonade stand" | draw it | recognisability, 0–10 |
| ☠️ **Survive** (Death by AI style) | "You wake up in a lift with a hungry bear." | type how they'd survive | **lives or dies**, plus a score |
| 💬 **Quick Wit** (Quiplash style) | "A rejected AWS service name" | type the funniest answer | funniness, 0–10 |
| 🔀 **Mixed** (default) | Draw → Survive → Quick Wit, repeating | | |

**☁️ AWS themes** (every round, every 2nd round, or off): before a themed round, the big screen shows an intro to an AWS service: what it is, two facts, and how Amacide uses it. The host can skip it. The round's prompt then fits the theme. The 10 themes are in [backend/src/shared/themes.json](backend/src/shared/themes.json).

**💀 Elimination** is an optional switch that works with any mode. The lowest-scoring living player dies each round. Dead players keep answering as ghosts for half points, and revive after scoring 6+ in a number of rounds in a row (the host sets this, 1–5).

## Game loop

1. The host screen shows a QR code and room code. Players join on their phones.
2. Bedrock generates a prompt (themed, scaled by difficulty, no repeats).
3. Everyone draws or types an answer before the timer runs out.
4. Bedrock ranks **all entries in one call**: vision for drawings (scoring recognisability, not art quality, and penalising written words), text for Survive and Quick Wit.
5. The reveal shows each drawing's rank, score and one-line roast, read aloud by Polly.

**Stretch goals** (only once the core loop works end to end):
- **AI player:** Nova Canvas draws its own entry, which is mixed in anonymously and judged blind. Humans guess which drawing is the AI's.
- **Chain mode:** prompt → A draws → AI describes the drawing → B draws that description → … At the end, show how far the idea drifted.

## AWS architecture

Region: **eu-west-2 (London)**. Everything is serverless and defined in one SAM stack ([backend/template.yaml](backend/template.yaml)), so nothing costs money while idle.

```
                         ┌──────────────────────────────┐
 Phones / host screen ──►│ CloudFront ──► S3 (frontend) │   static site
        │                └──────────────────────────────┘
        │
        │  HTTPS          ┌─────────────────┐      ┌──────────┐
        ├────────────────►│ API Gateway     │─────►│ Lambda   │──► DynamoDB (rooms, players, entries)
        │                 │ (HTTP API)      │      │ (rooms/) │──► Bedrock Claude (round prompt)
        │                 └─────────────────┘      └────┬─────┘
        │                                               │ presigned PUT URL
        │  PUT drawing.jpg                              ▼
        ├──────────────────────────────────────────► S3 (drawings + host audio)
        │
        │  WebSocket      ┌─────────────────┐
        ◄─────────────────│ AppSync Events  │◄── Lambdas publish player_joined, round_started, …
                          └─────────────────┘      (fallback: poll GET /rooms/{code} every 1s)

 All drawings in / timer ends
        │
        ▼
 ┌──────────────── Step Functions: judge_round ────────────────┐
 │ Judge (Bedrock Claude vision: rank all drawings + roasts)    │
 │   → HostVoice (Polly: game-show host MP3 → S3)               │
 │   → SaveResults (DynamoDB + publish results_ready)           │
 └──────────────────────────────────────────────────────────────┘

 Across everything: IAM (least-privilege role per function), CloudWatch (logs + metrics)
```

- Shrink drawings to about 512px JPEG on the client before upload.
- The judge uses the Bedrock Converse API with images labelled `Drawing 1..n` and returns strict JSON.

### AWS services

**Core** (in the template, needed for the minimum demo):

| Service | What we use it for | Owner |
|---|---|---|
| **Amazon Bedrock**: Claude | Writes each round's prompt for its mode. Judges all entries in one call (vision for drawings, text for Survive and Quick Wit) | 4 |
| **AWS Lambda** (Python 3.12, arm64) | API handlers and the steps of the judging pipeline | 3, 4 |
| **Amazon API Gateway** (HTTP API) | REST endpoints for rooms, joining, rounds, uploads | 3 |
| **Amazon DynamoDB** | Single-table game state: rooms, players, drawings, scores | 3 |
| **Amazon S3** | Drawing uploads via presigned URLs, Polly audio, frontend hosting | 3 |
| **AWS AppSync Events** | Live pub/sub over WebSockets, pushing game events to phones and the host screen | 3 |
| **AWS Step Functions** | Judging pipeline: Judge → HostVoice → SaveResults, with retries and a fallback if Polly fails | 4 |
| **Amazon Polly** (neural voice) | Game-show host reads out the winner and the roasts | 4 |
| **AWS SAM / CloudFormation** | Infrastructure as code: the whole stack deploys with one command | 3 |
| **AWS IAM** | A least-privilege role for each function, generated by SAM policy templates | 3 |
| **Amazon CloudWatch** | Lambda logs and metrics for debugging on the day | 3 |

**To add** (small, but completes the architecture):

| Service | What we'd use it for | Owner |
|---|---|---|
| **Amazon CloudFront** | HTTPS in front of the frontend S3 bucket. Gives phones a proper URL for the QR code | 3 |

**Stretch / possible** (only once the core loop works end to end):

| Service | What we'd use it for | Owner |
|---|---|---|
| **Bedrock: Amazon Nova Canvas** | Draws the judge's reference images (core), and in the stretch goal the AI player's own entry. Not in eu-west-2, so it's called in `ImageRegion` (eu-west-1) | 4 |
| **Bedrock Guardrails** | Keep the AI's roasts playful, never offensive, which matters with an audience of judges | 4 |
| **Amazon Rekognition** (`DetectModerationLabels`) | Filter inappropriate drawings before they appear on the big screen | 4 |
| **Amazon EventBridge Scheduler** | End the round on the server when the timer expires, rather than relying on the host screen calling `/end` | 3 |
| **AWS X-Ray** | Trace a whole round through API → Lambda → Step Functions → Bedrock. Makes a good visual for the AWS judges | 3 |

**Deliberately not used** (so we can explain the choices if the judges ask):
- **Amazon Cognito:** players only need a name and a room code, so accounts would slow down joining.
- **API Gateway WebSocket APIs:** AppSync Events gives us pub/sub channels without managing connection IDs ourselves.
- **Amazon EC2 / ECS:** no servers to run. Serverless scales to a room of phones and costs nothing when idle.

## Contracts (don't change these without telling the team)

### DynamoDB (single table)

| PK | SK | Attributes |
|---|---|---|
| `ROOM#<code>` | `META` | `state` (lobby \| drawing \| judging \| results), `round`, `totalRounds`, `prompt`, `endsAt`, `usedPrompts`, `audioUrl` |
| `ROOM#<code>` | `PLAYER#<id>` | `name` |
| `ROOM#<code>` | `ROUND#<n>#<playerId>` | `s3Key`, then after judging `rank`, `score`, `roast`, `imageUrl` |

A player's total score isn't stored: `GET /rooms/{code}` sums their `ROUND#` scores. That makes saving results safe to retry, and "Play again" just deletes the `ROUND#` rows.

### HTTP API, realtime events and response shapes

**[`contracts/`](contracts/) is the source of truth.** It holds [api.md](contracts/api.md), [events.md](contracts/events.md) and sample responses in [fixtures/](contracts/fixtures/).

```
POST /rooms                        → {code}
POST /rooms/{code}/join            {name} → {playerId}
GET  /rooms/{code}                 → full room state (also the polling fallback)
POST /rooms/{code}/start           {totalRounds?, mode?, elimination?, reviveAfter?, themeEvery?} → {round, prompt, endsAt}   (409 after the last round)
POST /rooms/{code}/upload-url      {playerId} → {url, key}
POST /rooms/{code}/submit          {playerId, key} (draw) or {playerId, text} (survive/wit)
POST /rooms/{code}/end             host calls this when the timer hits 0
POST /rooms/{code}/reset           "Play again": back to lobby, scores to 0
POST /rooms/{code}/begin           themed round: end the AWS theme intro (timer or Skip)
```

## Project structure

Each folder has one owner, which keeps merge conflicts rare.

```
contracts/        ALL      API + events contract, JSON example responses
frontend/         1 + 2    Vite + TypeScript. index.html = phone, host.html = big screen
  src/api.ts               fetch wrapper; VITE_MOCK=true swaps in src/mock.ts (fake backend)
  src/realtime.ts          polling now, AppSync Events later
  src/player/     1        canvas, upload, screens
  src/host/       2        lobby (settings), theme intro, round, judging, reveal, leaderboard
backend/          3        SAM stack (template.yaml), Python 3.12 Lambdas
  src/shared/     3        DynamoDB keys, HTTP helpers, AppSync publish, elimination rules, AWS themes
  src/rooms/      3        API handlers + save_results (last step of judging)
  src/ai/         4        prompt_gen + judge per mode, host_voice, ai_player (stretch), prompts/*.txt
  statemachine/   4        judge_round.asl.json: Judge → HostVoice → SaveResults
  scripts/        3 + 4    test_judge.py (judge on samples/), test_elimination.py (rules)
samples/          4        test drawings (.jpg) for tuning the judge
pitch/            5        diagram, slides, demo script
```

Every handler is a stub that returns a response shaped like the contract, so the stack can be deployed and the frontend pointed at it straight away. Search for `TODO person N` to find your work.

## Running it on AWS (read this before the demo)

**This hackathon account cannot deploy the stack.** `WSParticipantRole` has `cloudformation:*`
denied in every region and `iam:*` explicitly denied, so there is no way to create a stack or
the Lambda execution roles it needs. `sam build` works; `sam deploy` cannot.

What the account *does* allow, and what we therefore use for real:

| Service | Status | Used for |
|---|---|---|
| **Amazon Bedrock** (us-west-2) | ✅ | Writing every prompt, judging drawings (vision) and answers (text) |
| **Amazon DynamoDB** (us-east-1) | ✅ | Table `amacide` — rooms, players, entries, scores |
| **Amazon S3** (us-east-1) | ✅ | Bucket `amacide-985539753760` — drawings via presigned URLs |
| Lambda / API Gateway / Step Functions | ❌ | Need IAM roles, which are denied |
| AppSync Events | ❌ | Denied — the screens poll `GET /rooms/{code}` instead (documented fallback) |
| Amazon Polly | ❌ | Denied — `host_voice` returns `hostScript` and the browser reads it aloud |

So the API runs on the laptop via [backend/scripts/serve_local.py](backend/scripts/serve_local.py),
which serves the **same `rooms/` handlers** against the real table, bucket and models. Step
Functions is replaced by a thread running the same Judge → HostVoice → SaveResults order.

```sh
# 1. Backend (needs boto3 and working AWS credentials)
cd backend && python scripts/serve_local.py          # http://0.0.0.0:8000

# 2. Frontend, pointed at the laptop's LAN IP so phones can reach it
cd frontend
cat > .env.local <<'ENV'
VITE_API_URL=http://<laptop-lan-ip>:8000
VITE_PUBLIC_URL=http://<laptop-lan-ip>:5173
ENV
npm run dev
```

Open `http://<laptop-lan-ip>:5173/host.html` on the big screen; phones scan the QR code.
Everyone must be on the same wifi.

> **Serve the frontend over HTTP, not HTTPS.** The API is plain HTTP on the laptop, and a
> page served over HTTPS (S3/CloudFront) is not allowed to call it — browsers block mixed
> content. That is why the frontend is served from Vite rather than uploaded to S3.

If you get an account that *can* deploy, the template is ready: `sam build && sam deploy`
brings up the full serverless architecture, and the frontend just needs `VITE_API_URL`
repointed at the stack's `ApiUrl`.

## Getting started

```sh
# Frontend (persons 1, 2)
cd frontend && npm install
npm run dev:mock                     # no backend needed
cp .env.example .env.local           # later: fill from stack outputs, then `npm run dev`

# Backend (person 3 deploys; region eu-west-2 in samconfig.toml)
cd backend && sam build && sam deploy
sam sync --watch                     # hot-redeploy while developing
pip install "moto[dynamodb,s3]" && python scripts/test_rooms.py   # play a whole game against fake AWS

# Frontend hosting (person 3): fill frontend/.env.local from the stack outputs first
cd frontend && npm run build
aws s3 sync dist s3://<FrontendBucketName> --delete   # then open the FrontendUrl output

# Judge prompt tuning (person 4)
cd backend && TEXT_MODEL_ID=<id> AWS_REGION=eu-west-2 python scripts/test_judge.py "A penguin running a lemonade stand"
```

`npm run dev` listens on the LAN, so phones on the same wifi can open `http://<laptop-ip>:5173`.

### Frontend mock mode

`npm run dev:mock` runs the **whole game with no backend**. A fake server in [src/mock.ts](frontend/src/mock.ts) keeps game state in localStorage, so tabs in the same browser play together:

1. Open `http://localhost:5173/host.html` (the big screen). Add `?seconds=20` for shorter rounds.
2. Open the join link shown under the QR code in another tab, or on a phone via your LAN IP.
3. Click **+ Add bot** to fill the room. Bots submit random scribbles, and the mock "AI" gives random scores and canned roasts.

UI copy and the game name live in [src/config.ts](frontend/src/config.ts) and [src/ai.ts](frontend/src/ai.ts).

## Team

| # | Role | Owns |
|---|---|---|
| 1 | **Player frontend** | Phone UI: join, drawing canvas (brush, colours, undo, clear), timer, resize and upload via presigned URL |
| 2 | **Host screen frontend** | Big-screen UI: lobby with QR code, countdown, results reveal with Polly audio |
| 3 | **Backend / infra** | SAM stack, DynamoDB, Lambdas, realtime events, hosting. **Only person 3 deploys** |
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
