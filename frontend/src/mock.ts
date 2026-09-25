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
import type { Result, Room, RoomState } from "./types";
import { pick, sleep } from "./ui";

const ROUND_MS = Number(new URLSearchParams(location.search).get("seconds") ?? 60) * 1000;
const JUDGE_MS = 4000;
const GRACE_MS = 5000;
const IS_HOST = location.pathname.includes("host");

const PROMPTS = [
  "A penguin running a lemonade stand",
  "A cat who just got fired",
  "Dracula at the dentist",
  "A snowman on a beach holiday",
  "A dog driving a bus",
  "The world's worst superhero",
  "A giraffe stuck in a lift",
  "A pizza with feelings",
  "Shakespeare playing video games",
  "A shark afraid of water",
  "Grandma on a skateboard",
  "A robot falling in love with a toaster",
  "A haunted washing machine",
  "A wizard who lost his hat",
  "An octopus doing the washing up",
];

const ROASTS = [
  "{name}, I've seen better art from a Roomba with a pen taped to it.",
  "{name} clearly heard the prompt and chose violence.",
  "Bold of you, {name}, to call this a drawing.",
  "{name}, this is either genius or a cry for help. I'm leaning towards help.",
  "I recognised it instantly, {name}. Unfortunately.",
  "{name}, my training data did not prepare me for this.",
  "Honestly, {name}? Not bad. Don't let it go to your head.",
  "{name}, I will be showing this to other AIs. As a warning.",
  "Every line is a choice, {name}. You made so many wrong ones.",
  "{name} has the confidence of a Picasso and the skill of a potato.",
];

const BOT_NAMES = ["RoboBob", "Doodlebug", "Sir Scribbles", "Picasso.exe", "Crayon Eater", "Captain Blob"];

interface MockPlayer {
  playerId: string;
  name: string;
  score: number;
  bot?: boolean;
  botSubmitAt?: number;
}

interface MockRoom {
  code: string;
  state: RoomState;
  round: number;
  prompt?: string;
  endsAt?: number;
  judgingAt?: number;
  players: MockPlayer[];
  entries: Record<number, Record<string, string>>; // round -> playerId -> image key
  results?: Omit<Result, "name" | "imageUrl">[];
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

/** The "server-side" state transitions, applied lazily on every read. */
function tick(room: MockRoom) {
  const now = Date.now();
  if (room.state === "drawing") {
    const entries = (room.entries[room.round] ??= {});
    for (const p of room.players) {
      if (p.bot && (p.botSubmitAt ?? Infinity) <= now && !entries[p.playerId]) entries[p.playerId] = drawingKey(room, p.playerId);
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
  const scored = Object.keys(room.entries[room.round] ?? {})
    .map((playerId) => ({ playerId, score: 1 + Math.floor(Math.random() * 10) }))
    .sort((a, b) => b.score - a.score);
  room.results = scored.map((s, i) => ({
    ...s,
    rank: i + 1,
    roast: pick(ROASTS).replace("{name}", nameOf(room, s.playerId)),
  }));
  for (const s of scored) {
    const player = room.players.find((p) => p.playerId === s.playerId);
    if (player) player.score += s.score;
  }
  room.state = "results";
}

function view(room: MockRoom): Room {
  const entries = room.entries[room.round] ?? {};
  return {
    code: room.code,
    state: room.state,
    round: room.round,
    prompt: room.prompt,
    endsAt: room.endsAt,
    players: room.players.map(({ playerId, name, score }) => ({ playerId, name, score, submitted: !!entries[playerId] })),
    results:
      room.state === "results"
        ? room.results?.map((r) => ({
            ...r,
            name: nameOf(room, r.playerId),
            imageUrl: localStorage.getItem(imageKey(entries[r.playerId])) ?? "",
          }))
        : undefined,
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
    save({ code, state: "lobby", round: 0, players: [], entries: {}, usedPrompts: [] });
    return { code };
  },

  async joinRoom(code, name) {
    await latency();
    const room = load(code);
    const playerId = `p_${newId()}`;
    room.players.push({ playerId, name, score: 0 });
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

  async startRound(code) {
    await latency();
    const room = load(code);
    if (room.state === "drawing" || room.state === "judging") throw new Error("Round already in progress");
    // Free the previous round's images; localStorage only holds ~5 MB.
    for (const key of Object.values(room.entries[room.round] ?? {})) localStorage.removeItem(imageKey(key));

    const fresh = PROMPTS.filter((p) => !room.usedPrompts.includes(p));
    room.prompt = pick(fresh.length ? fresh : PROMPTS);
    room.usedPrompts.push(room.prompt);
    room.round += 1;
    room.state = "drawing";
    room.endsAt = Date.now() + ROUND_MS;
    room.results = undefined;
    for (const p of room.players.filter((p) => p.bot)) {
      p.botSubmitAt = Date.now() + 3000 + Math.random() * ROUND_MS * 0.6;
      localStorage.setItem(imageKey(drawingKey(room, p.playerId)), scribble());
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

  async submit(code, playerId, key) {
    await latency();
    const room = load(code);
    if (room.state !== "drawing") throw new Error("Too late! The round is over.");
    (room.entries[room.round] ??= {})[playerId] = key;
    save(room);
    return { ok: true };
  },

  async endRound(code) {
    const room = load(code);
    startJudging(room);
    save(room);
    return { ok: true };
  },
};

export function mockAddBot(code: string) {
  const room = load(code);
  const taken = new Set(room.players.map((p) => p.name));
  const name = BOT_NAMES.find((n) => !taken.has(n)) ?? `Bot ${room.players.length + 1}`;
  room.players.push({ playerId: `bot_${newId()}`, name, score: 0, bot: true });
  save(room);
}
