# Amacide — AWS North x Northumbria Hackathon

**Amacide** is a party game in the style of Gartic Phone and Quiplash, with an AWS quiz round that teaches players the services as they play. Bedrock writes the prompt, everyone answers it on their phone, and the AI ranks the answers against the prompt. A game-show host voice reads out the results and a roast of each answer (Polly, falling back to the browser's own speech).

**Categories:** Traditional (party game), Digital worlds, Gamification

## Game modes

The host picks a mode in the lobby, along with the number of rounds.

| Mode | Prompt example | Players | The AI judges |
|---|---|---|---|
| 🎨 **Draw** | "A penguin running a lemonade stand" | draw it | recognisability, 0–10 |
| 🎓 **Learn** (an AWS quiz) | "What does AWS Lambda let you avoid managing?" | type their best guess | how correct it is, 0–10, and tells everyone the right answer |
| 💬 **Quick Wit** (Quiplash style) | "A rejected AWS service name" | type the funniest answer | funniness, 0–10 |
| 🔀 **Mixed** (default) | Draw → Learn → Quick Wit, repeating | | |

**☁️ AWS themes** (every round, every 2nd round, or off): before a themed round, the big screen shows an intro to an AWS service: what it is, two facts, and how Amacide uses it. The host can skip it. The round's prompt then fits the theme. The 10 themes are in [backend/src/shared/themes.json](backend/src/shared/themes.json).

**💀 Elimination** is an optional switch that works with any mode. The lowest-scoring living player dies each round. Dead players keep answering as ghosts for half points, and revive after scoring 6+ in a number of rounds in a row (the host sets this, 1–5).

## Game loop

1. The host screen shows a QR code and room code. Players join on their phones.
2. Bedrock generates a prompt (themed, scaled by difficulty, no repeats).
3. Everyone draws or types an answer before the timer runs out.
4. Bedrock ranks **all entries in one call**: vision for drawings (scoring recognisability, not art quality, and penalising written words), text for Learn and Quick Wit.
5. The reveal shows each entry's rank, score and one-line roast, read aloud by the host voice.

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
| **Amazon Bedrock**: Claude | Writes each round's prompt for its mode. Judges all entries in one call (vision for drawings, text for Learn and Quick Wit) | 4 |
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
| `ROOM#<code>` | `META` | `state` (lobby \| theme \| drawing \| judging \| results), `round`, `totalRounds`, `mode`, `roundMode`, `elimination`, `reviveAfter`, `themeEvery`, `theme`, `themeEndsAt`, `prompt`, `endsAt`, `usedPrompts`, `usedThemes`, `outcome`, `audioUrl`, `hostScript`, `referenceUrls` |
| `ROOM#<code>` | `PLAYER#<id>` | `name`, `alive`, `streak` (the last two matter only in elimination games) |
| `ROOM#<code>` | `ROUND#<n>#<playerId>` | `s3Key` (draw) or `text` (learn/wit), then after judging `rank`, `score`, `points`, `roast`, plus `imageUrl`, `ghost` where it applies |

A player's total score isn't stored: `GET /rooms/{code}` sums their `ROUND#` **points** (the score, or half of it while eliminated). That makes saving results safe to retry, and "Play again" just deletes the `ROUND#` rows.

### HTTP API, realtime events and response shapes

**[`contracts/`](contracts/) is the source of truth.** It holds [api.md](contracts/api.md), [events.md](contracts/events.md) and sample responses in [fixtures/](contracts/fixtures/).

```
POST /rooms                        → {code}
POST /rooms/{code}/join            {name} → {playerId}
GET  /rooms/{code}                 → full room state (also the polling fallback)
POST /rooms/{code}/start           {totalRounds?, mode?, elimination?, reviveAfter?, themeEvery?} → {round, prompt, endsAt}   (409 after the last round)
POST /rooms/{code}/upload-url      {playerId} → {url, key}
POST /rooms/{code}/submit          {playerId, key} (draw) or {playerId, text} (learn/wit)
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

## 🔴 Live demo

| | URL |
|---|---|
| **Host / big screen** | http://amacide-web-985539753760.s3-website-us-east-1.amazonaws.com/host.html |
| **Phones** | the QR code on the host screen, or `.../?room=CODE` |
| API | `http://54.86.27.110:8000` (EC2) |

Both are public, so phones don't need to be on the venue wifi. Everything runs on AWS:
S3 website hosting for the frontend, EC2 for the API, DynamoDB for state, S3 for drawings,
Bedrock for every prompt and judgement.

**Two things to know:**
- The EC2 instance carries the workshop's **temporary credentials**, because the account
  denies IAM so there is no instance role. When those expire the API starts failing; re-run
  `python backend/scripts/deploy_ec2.py` to launch a fresh instance with current credentials.
- It costs a few pence an hour. Stop it when you're done:
  `aws ec2 terminate-instances --instance-ids i-0c1c3815c85decdbc --region us-east-1`

To repoint the site after redeploying, rebuild with the new IP and re-upload:

```sh
cd frontend
VITE_API_URL=http://<new-ip>:8000 \
VITE_PUBLIC_URL=http://amacide-web-985539753760.s3-website-us-east-1.amazonaws.com \
  npm run build
aws s3 sync dist s3://amacide-web-985539753760 --delete
```

## How it's deployed, and why it isn't the SAM stack

**This hackathon account cannot deploy the SAM stack.** `WSParticipantRole` has
`cloudformation:*` denied in every region and `iam:*` explicitly denied, so there is no way to
create a stack, or the Lambda execution roles it needs. `sam build` works; `sam deploy` cannot.
EC2 *is* allowed, so the API runs there instead, provisioned by
[backend/scripts/deploy_ec2.py](backend/scripts/deploy_ec2.py).

What the account *does* allow, and what we therefore use for real:

| Service | Status | Used for |
|---|---|---|
| **Amazon Bedrock** (us-west-2) | ✅ | Writing every prompt, judging drawings (vision) and answers (text) |
| **Amazon DynamoDB** (us-east-1) | ✅ | Table `amacide` — rooms, players, entries, scores |
| **Amazon S3** (us-east-1) | ✅ | Bucket `amacide-985539753760` — drawings via presigned URLs |
| **Amazon EC2** (us-east-1) | ✅ | t3.micro running the API, the only compute this account can create |
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

## Demo notes

The pitch timings are in [pitch/demo-script.md](pitch/demo-script.md). These notes cover what to set up, what to say at each screen, and what to do when something breaks.

### Before the judges arrive

- [ ] Laptop and every phone on the **same wifi**. Venue wifi often isolates devices from each other. If phones can't load the page, use a phone hotspot for everyone.
- [ ] AWS credentials are fresh (workshop sessions expire). `serve_local.py` prints the table, bucket and model it's using on startup.
- [ ] `python scripts/serve_local.py` is running, and so is `npm run dev` with `.env.local` pointing at the laptop's LAN IP (see above).
- [ ] Open `http://<laptop-lan-ip>:5173/host.html` on the big screen, **not** `localhost`. The QR code uses `VITE_PUBLIC_URL`, so check that it opens on a phone.
- [ ] Play one full round yourself to warm up Bedrock and check it's answering.
- [ ] Have the architecture diagram and backup video open in other tabs. Neither is in [pitch/](pitch/) yet. Until the diagram exists, the ASCII one above will do.
- [ ] Sound doesn't matter. See "No voice" below.

### Suggested settings

- **Mode: Mixed, 3 rounds.** One of each mode: a drawing, an AWS quiz question and a Quiplash-style joke. That shows the most in the least time.
- **AWS themes: every round.** Each round opens with a 20-second intro to an AWS service, which the judges will like. Press **Skip** if you're short of time.
- **Elimination: off** for a 3-minute slot. It needs several rounds to get interesting. Mention it instead.
- Rounds last 60 seconds. If everyone has submitted early, press **End round now**.

### What to say at each screen

| Screen | Talking point |
|---|---|
| **Lobby / QR** | No accounts and no app, just a room code. That's why we didn't use Cognito. |
| **Theme intro** | An AWS service explained in two facts, and how Amacide itself uses it. The round's prompt is then about that service. |
| **Prompt** | Bedrock (Claude) wrote this just now. It avoids repeating earlier prompts and fits the mode and theme. |
| **Judging** | Here's the architecture. **All entries are judged in one Bedrock call**: vision for drawings, text for answers. For drawings we first generate a reference image (Stability Image Core on Bedrock), so the judge knows what the key elements of the prompt look like. It scores recognisability, not art skill, and penalises written words. |
| **Reveal** | Entries are revealed from last place to the winner, each with a one-line roast. In Learn rounds, the AI also says what the right answer was, so everyone learns something. |
| **Leaderboard** | Scores aren't stored. They're added up from each round's points, so a retried save can't double-count them. |

### Be honest about the architecture

The hackathon account can't deploy (CloudFormation and IAM are denied, see above). Say this up front rather than let the judges find out:

- **Live AWS in the demo:** Bedrock (Claude for prompts and judging, Stability for reference images), DynamoDB for all game state, S3 for drawings via presigned URLs.
- **Written, but not deployed:** the SAM stack in [backend/template.yaml](backend/template.yaml) with Lambda, API Gateway, Step Functions, AppSync Events, Polly and CloudFront. `sam build` passes. The laptop runs **the same Lambda handler code**, and a thread follows the Step Functions order (Judge → HostVoice → SaveResults).
- **No voice.** Polly is denied, and the host screen doesn't read `hostScript` aloud yet, so the roasts are shown as the robot's typed speech. Don't promise a voice.
- **Screens poll** `GET /rooms/{code}` every second because AppSync Events is denied. This is the documented fallback.

### Questions the judges might ask

- **Why serverless?** A game room gets busy for 20 minutes and then nothing happens. With Lambda, DynamoDB and S3 an idle game costs nothing, and a room full of phones scales on its own.
- **Why judge everything in one call?** It's cheaper and faster, and the model ranks entries against each other rather than scoring each one in isolation.
- **How do you stop offensive content?** We haven't yet. The plan is Bedrock Guardrails for the roasts and Rekognition moderation for drawings (see Stretch above).
- **What's next?** An AI player that draws its own entry for the humans to spot ([backend/src/ai/ai_player.py](backend/src/ai/ai_player.py) is written but not wired in), and chain mode.

### If something breaks

| Problem | Fix |
|---|---|
| Phones can't open the page | Different network or client isolation. Switch everyone to a hotspot and restart Vite with the new IP in `.env.local`. |
| Stuck on the judging screen | Check the `serve_local.py` output. If judging failed, the room goes back to the round, and **End round now** retries. |
| Bedrock errors or expired credentials | Refresh the credentials and restart `serve_local.py`. Rooms are kept in DynamoDB, so the room carries on. |
| Nothing works | Play the backup video, or run `npm run dev:mock` and play against bots. The mock "AI" gives random scores, so say so. |

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
