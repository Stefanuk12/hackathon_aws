import createRoomFx from "../../contracts/fixtures/create_room.json";
import joinRoomFx from "../../contracts/fixtures/join_room.json";
import roomFx from "../../contracts/fixtures/room.json";
import startRoundFx from "../../contracts/fixtures/start_round.json";
import uploadUrlFx from "../../contracts/fixtures/upload_url.json";
import type { Room } from "./types";

export const MOCK = import.meta.env.VITE_MOCK === "true";
const API_URL = import.meta.env.VITE_API_URL as string;

async function call<T>(method: string, path: string, body?: unknown, mock?: unknown): Promise<T> {
  if (MOCK) return structuredClone(mock) as T;
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${method} ${path} → ${res.status}`);
  return res.json();
}

export const api = {
  createRoom: () => call<{ code: string }>("POST", "/rooms", undefined, createRoomFx),
  joinRoom: (code: string, name: string) =>
    call<{ playerId: string }>("POST", `/rooms/${code}/join`, { name }, joinRoomFx),
  getRoom: (code: string) => call<Room>("GET", `/rooms/${code}`, undefined, roomFx),
  startRound: (code: string) =>
    call<{ round: number; prompt: string; endsAt: number }>("POST", `/rooms/${code}/start`, undefined, startRoundFx),
  uploadUrl: (code: string, playerId: string) =>
    call<{ url: string; key: string }>("POST", `/rooms/${code}/upload-url`, { playerId }, uploadUrlFx),
  submit: (code: string, playerId: string, key: string) =>
    call<{ ok: boolean }>("POST", `/rooms/${code}/submit`, { playerId, key }, { ok: true }),
  endRound: (code: string) => call<{ ok: boolean }>("POST", `/rooms/${code}/end`, undefined, { ok: true }),
};
