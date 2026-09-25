/**
 * Fake backend for `npm run dev:mock`. State lives in localStorage, so a host tab
 * and several player tabs in the same browser play one shared game.
 * Follows contracts/api.md, including the drawing -> judging -> results transitions.
 *
 * Extras: ?seconds=20 on the host URL shortens rounds; the host lobby has "+ Add bot".
 *
 * Only the host tab runs the timed transitions (like a single server would). Player tabs
 * never write on reads, so they can't overwrite newer state from another tab.
 */
import type { Api } from "./api";
import { DEFAULT_MODE, DEFAULT_ROUNDS, ELIMINATION, MAX_ROUNDS, TEXT_LIMIT } from "./config";
import { applyElimination } from "./elimination";
import type { GameMode, ModeSetting, Result, Room, RoundOutcome, RoomState } from "./types";
import { pick, sleep } from "./ui";

const ROUND_MS = Number(new URLSearchParams(location.search).get("seconds") ?? 60) * 1000;
const JUDGE_MS = 4000;
const GRACE_MS = 5000;
const IS_HOST = location.pathname.includes("host");

/** Mixed mode cycles through these (same rule the backend follows). */
const MIXED_ORDER: GameMode[] = ["draw", "survive", "wit"];

const PROMPTS: Record<GameMode, string[]> = {
  draw: [
    "A penguin running a lemonade stand",
    "A cat who just got fired",
    "Dracula at the dentist",
    "A snowman on a beach holiday",
    "A dog driving a bus",
    "The world's worst superhero",
    "A giraffe stuck in a lift",
    "A pizza with feelings",
    "A shark afraid of water",
    "Grandma on a skateboard",
    "A robot falling in love with a toaster",
    "A haunted washing machine",
    "An octopus doing the washing up",
  ],
  survive: [
    "You wake up in a lift with a hungry bear.",
    "The floor is lava and you're wearing socks.",
    "You're locked in IKEA after closing time. The lights go out.",
    "Zombies burst into your 9am lecture.",
    "You accidentally deleted the production database. Your boss is walking over.",
    "A gang of seagulls has surrounded you and your chips.",
    "You're on a sinking ship. All you have is a toaster.",
    "The Wi-Fi dies five minutes before your hackathon demo.",
    "A goose has declared war on you personally.",
  ],
  wit: [
    "The worst thing to say in a job interview",
    "A terrible name for a pet goldfish",
    "What the AI really does when nobody's watching",
    "The secret ingredient in the canteen food",
    "The most useless superpower",
    "A rejected AWS service name",
    "What your houseplant secretly thinks of you",
    "The real reason the lecture was cancelled",
    "A bad slogan for a dentist",
  ],
};

const ROASTS: Record<GameMode, string[]> = {
  draw: [
    "{name}, I've seen better art from a Roomba with a pen taped to it.",
    "{name} clearly heard the prompt and chose violence.",
    "Bold of you, {name}, to call this a drawing.",
    "{name}, this is either genius or a cry for help. I'm leaning towards help.",
    "I recognised it instantly, {name}. Unfortunately.",
    "{name}, my training data did not prepare me for this.",
    "Honestly, {name}? Not bad. Don't let it go to your head.",
    "{name}, I will be showing this to other AIs. As a warning.",
  ],
  wit: [
    "{name}, that's the funniest thing I've read today. Low bar, but still.",
    "I've processed billions of jokes, {name}. This was one of them.",
    "{name}, I laughed. Internally. Silently. Barely.",
    "Comedy is subjective, {name}. And subjectively, no.",
    "{name}, I'm adding this to my training data. As a warning.",
    "Genuinely clever, {name}. I'm annoyed.",
  ],
  survive: [],
};

const SURVIVE_LINES = {
  lived: [
    "{name} survived. Barely. I'm as surprised as you are.",
    "Against all odds, {name} lives. The universe is confused.",
    "{name}'s plan was ridiculous. It also worked. Fine.",
  ],
  died: [
    "{name} died instantly. It didn't even need to try.",
    "{name}'s plan lasted four seconds. Three of them were screaming.",
    "Bold strategy, {name}. Fatal, but bold.",
    "{name} is now a cautionary tale.",
  ],
};

const BOT_ANSWERS: Record<Exclude<GameMode, "draw">, string[]> = {
  survive: [
    "I befriend it with snacks.",
    "Run. Just run.",
    "I call my mum.",
    "I hide behind someone slower.",
    "I deploy a Lambda function to fight it.",
    "I simply refuse to panic.",
    "Play dead. Commit to the role.",
  ],
  wit: ["Gary", "Cheese, probably", "Blockchain", "My landlord", "It's always DNS", "Vibes", "Bold of you to ask"],
};

const BOT_NAMES = ["RoboBob", "Doodlebug", "Sir Scribbles", "Picasso.exe", "Crayon Eater", "Captain Blob"];

interface MockPlayer {
  playerId: string;
  name: string;
  score: number;
  alive: boolean;
  streak: number;
  bot?: boolean;
  botSubmitAt?: number;
}

/** A drawing (image key) or a typed answer. */
interface Entry {
  key?: string;
  text?: string;
}

interface MockRoom {
  code: string;
  state: RoomState;
  round: number;
  totalRounds: number;
  mode: ModeSetting;
  elimination: boolean;
  reviveAfter: number;
  outcome?: RoundOutcome;
  roundMode?: GameMode;
  prompt?: string;
  endsAt?: number;
  judgingAt?: number;
  players: MockPlayer[];
  entries: Record<number, Record<string, Entry>>; // round -> playerId -> entry
  results?: Omit<Result, "name" | "imageUrl" | "text">[];
  usedPrompts: string[];
}

const roomKey = (code: string) => `mock:room:${code}`;
const imageKey = (key: string) => `mock:img:${key}`;
const newId = () => Math.random().toString(36).slice(2, 8);
const latency = () => sleep(100 + Math.random() * 150);

function load(code: string): MockRoom {
  const raw = localStorage.getItem(roomKey(code));
  if (!raw) throw new Error(`Room ${code} not found`);
  return JSON.parse(raw);
}

function save(room: MockRoom) {
  localStorage.setItem(roomKey(room.code), JSON.stringify(room));
}

const drawingKey = (room: MockRoom, playerId: string) => `rooms/${room.code}/${room.round}/${playerId}.jpg`;
const nameOf = (room: MockRoom, playerId: string) => room.players.find((p) => p.playerId === playerId)?.name ?? "?";
const roastFor = (lines: string[], name: string) => pick(lines).replace("{name}", name);

function botEntry(room: MockRoom, playerId: string): Entry {
  const mode = room.roundMode ?? "draw";
  return mode === "draw" ? { key: drawingKey(room, playerId) } : { text: pick(BOT_ANSWERS[mode]) };
}

/** The "server-side" state transitions, applied lazily on every read. */
function tick(room: MockRoom) {
  const now = Date.now();
  if (room.state === "drawing") {
    const entries = (room.entries[room.round] ??= {});
    for (const p of room.players) {
      if (p.bot && (p.botSubmitAt ?? Infinity) <= now && !entries[p.playerId]) entries[p.playerId] = botEntry(room, p.playerId);
    }
    const allIn = room.players.length > 0 && room.players.every((p) => entries[p.playerId]);
    if (allIn || now > (room.endsAt ?? 0) + GRACE_MS) startJudging(room);
  }
  if (room.state === "judging" && now > (room.judgingAt ?? 0) + JUDGE_MS) finishJudging(room);
}

function startJudging(room: MockRoom) {
  if (room.state !== "drawing") return;
  room.state = "judging";
  room.judgingAt = Date.now();
}

function finishJudging(room: MockRoom) {
  const mode = room.roundMode ?? "draw";
  const scored = Object.keys(room.entries[room.round] ?? {})
    .map((playerId) => ({ playerId, score: 1 + Math.floor(Math.random() * 10) }))
    .sort((a, b) => b.score - a.score);
  room.results = scored.map((s, i) => {
    const name = nameOf(room, s.playerId);
    if (mode === "survive") {
      const survived = s.score >= 6;
      return { ...s, rank: i + 1, survived, roast: roastFor(SURVIVE_LINES[survived ? "lived" : "died"], name) };
    }
    return { ...s, rank: i + 1, roast: roastFor(ROASTS[mode], name) };
  });
  // Points: the score, unless elimination makes this player a ghost (reduced points).
  let points: Record<string, number> = Object.fromEntries(scored.map((s) => [s.playerId, s.score]));
  room.outcome = undefined;
  if (room.elimination) {
    const ghosts = new Set(room.players.filter((p) => !p.alive).map((p) => p.playerId));
    const out = applyElimination(room.players, points, {
      reviveAfter: room.reviveAfter,
      reviveScore: ELIMINATION.reviveScore,
      ghostMultiplier: ELIMINATION.ghostMultiplier,
    });
    points = out.points;
    for (const p of room.players) Object.assign(p, out.players.find((o) => o.playerId === p.playerId));
    for (const r of room.results) r.ghost = ghosts.has(r.playerId);
    room.outcome = { eliminated: out.eliminated, revived: out.revived };
  }
  for (const r of room.results) r.points = points[r.playerId] ?? 0;
  for (const p of room.players) p.score += points[p.playerId] ?? 0;
  room.state = "results";
}

function view(room: MockRoom): Room {
  const entries = room.entries[room.round] ?? {};
  return {
    code: room.code,
    state: room.state,
    round: room.round,
    totalRounds: room.totalRounds,
    mode: room.mode,
    elimination: room.elimination,
    reviveAfter: room.reviveAfter,
    roundMode: room.roundMode,
    prompt: room.prompt,
    endsAt: room.endsAt,
    players: room.players.map(({ playerId, name, score, alive, streak }) => ({
      playerId,
      name,
      score,
      submitted: !!entries[playerId],
      ...(room.elimination ? { alive, streak } : {}),
    })),
    results:
      room.state === "results"
        ? room.results?.map((r) => {
            const entry = entries[r.playerId] ?? {};
            return {
              ...r,
              name: nameOf(room, r.playerId),
              ...(entry.key ? { imageUrl: localStorage.getItem(imageKey(entry.key)) ?? "" } : { text: entry.text ?? "" }),
            };
          })
        : undefined,
    outcome: room.state === "results" ? room.outcome : undefined,
    audioUrl: null,
  };
}

/** A random doodle so bots have something to be roasted for. */
function scribble() {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 512;
  const ctx = canvas.getContext("2d")!;
  ctx.fillStyle = "#fff";
  ctx.fillRect(0, 0, 512, 512);
  ctx.lineCap = "round";
  const r = () => 60 + Math.random() * 392;
  for (let i = 0; i < 3 + Math.random() * 4; i++) {
    ctx.strokeStyle = pick(["#0d0a1a", "#ff3b3b", "#5ab0ff", "#2ecc71", "#ff8a3d", "#7b5cff"]);
    ctx.lineWidth = 6 + Math.random() * 18;
    ctx.beginPath();
    ctx.moveTo(r(), r());
    ctx.bezierCurveTo(r(), r(), r(), r(), r(), r());
    ctx.stroke();
  }
  return canvas.toDataURL("image/jpeg", 0.7);
}

/** Drop the current round's images; localStorage only holds ~5 MB. */
function freeImages(room: MockRoom) {
  for (const entry of Object.values(room.entries[room.round] ?? {})) {
    if (entry.key) localStorage.removeItem(imageKey(entry.key));
  }
  // Bot drawings are stored at round start, before the bot "submits".
  for (const p of room.players) if (p.bot) localStorage.removeItem(imageKey(drawingKey(room, p.playerId)));
}

const blobToDataUrl = (blob: Blob) =>
  new Promise<string>((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(blob);
  });

export const mock: Api = {
  async createRoom() {
    await latency();
    const letters = "ABCDEFGHJKLMNPQRSTUVWXYZ";
    const code = Array.from({ length: 4 }, () => pick([...letters])).join("");
    save({
      code,
      state: "lobby",
      round: 0,
      totalRounds: DEFAULT_ROUNDS,
      mode: DEFAULT_MODE,
      elimination: ELIMINATION.defaultOn,
      reviveAfter: ELIMINATION.defaultReviveAfter,
      players: [],
      entries: {},
      usedPrompts: [],
    });
    return { code };
  },

  async joinRoom(code, name) {
    await latency();
    const room = load(code);
    const playerId = `p_${newId()}`;
    room.players.push({ playerId, name, score: 0, alive: true, streak: 0 });
    save(room);
    return { playerId };
  },

  async getRoom(code) {
    const room = load(code);
    if (IS_HOST) {
      const before = JSON.stringify(room);
      tick(room);
      if (JSON.stringify(room) !== before) save(room);
    }
    return view(room);
  },

  async startRound(code, settings) {
    await latency();
    const room = load(code);
    if (room.state === "drawing" || room.state === "judging") throw new Error("Round already in progress");
    if (room.state === "lobby") {
      if (settings?.totalRounds) room.totalRounds = Math.min(MAX_ROUNDS, Math.max(1, Math.round(settings.totalRounds)));
      if (settings?.mode) room.mode = settings.mode;
      if (settings?.elimination !== undefined) room.elimination = settings.elimination;
      if (settings?.reviveAfter) {
        room.reviveAfter = Math.min(ELIMINATION.maxReviveAfter, Math.max(1, Math.round(settings.reviveAfter)));
      }
    }
    if (room.round >= room.totalRounds) throw new Error("Game over! Press Play again.");
    freeImages(room);

    room.round += 1;
    room.roundMode = room.mode === "mixed" ? MIXED_ORDER[(room.round - 1) % MIXED_ORDER.length] : room.mode;
    const options = PROMPTS[room.roundMode];
    const fresh = options.filter((p) => !room.usedPrompts.includes(p));
    room.prompt = pick(fresh.length ? fresh : options);
    room.usedPrompts.push(room.prompt);
    room.state = "drawing";
    room.endsAt = Date.now() + ROUND_MS;
    room.results = undefined;
    room.outcome = undefined;
    for (const p of room.players.filter((p) => p.bot)) {
      p.botSubmitAt = Date.now() + 3000 + Math.random() * ROUND_MS * 0.6;
      if (room.roundMode === "draw") localStorage.setItem(imageKey(drawingKey(room, p.playerId)), scribble());
    }
    save(room);
    return { round: room.round, prompt: room.prompt, endsAt: room.endsAt };
  },

  async uploadUrl(code, playerId) {
    await latency();
    const key = drawingKey(load(code), playerId);
    return { url: `mock://${key}`, key };
  },

  async putDrawing(url, image) {
    await latency();
    localStorage.setItem(imageKey(url.replace("mock://", "")), await blobToDataUrl(image));
  },

  async submit(code, playerId, submission) {
    await latency();
    const room = load(code);
    if (room.state !== "drawing") throw new Error("Too late! The round is over.");
    (room.entries[room.round] ??= {})[playerId] =
      "key" in submission ? { key: submission.key } : { text: submission.text.slice(0, TEXT_LIMIT) };
    save(room);
    return { ok: true };
  },

  async endRound(code) {
    const room = load(code);
    startJudging(room);
    save(room);
    return { ok: true };
  },

  async resetRoom(code) {
    await latency();
    const room = load(code);
    freeImages(room);
    Object.assign(room, {
      state: "lobby",
      round: 0,
      entries: {},
      roundMode: undefined,
      prompt: undefined,
      endsAt: undefined,
      results: undefined,
      outcome: undefined,
    });
    for (const p of room.players) Object.assign(p, { score: 0, alive: true, streak: 0 });
    save(room);
    return { ok: true };
  },
};

export function mockAddBot(code: string) {
  const room = load(code);
  const taken = new Set(room.players.map((p) => p.name));
  const name = BOT_NAMES.find((n) => !taken.has(n)) ?? `Bot ${room.players.length + 1}`;
  room.players.push({ playerId: `bot_${newId()}`, name, score: 0, alive: true, streak: 0, bot: true });
  save(room);
}
