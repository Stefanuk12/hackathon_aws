import { mock } from "./mock";
import type { Room } from "./types";

/** Mirrors contracts/api.md. */
export interface Api {
  createRoom(): Promise<{ code: string }>;
  joinRoom(code: string, name: string): Promise<{ playerId: string }>;
  getRoom(code: string): Promise<Room>;
  startRound(code: string): Promise<{ round: number; prompt: string; endsAt: number }>;
  uploadUrl(code: string, playerId: string): Promise<{ url: string; key: string }>;
  putDrawing(url: string, image: Blob): Promise<void>;
  submit(code: string, playerId: string, key: string): Promise<{ ok: boolean }>;
  endRound(code: string): Promise<{ ok: boolean }>;
}

export const MOCK = import.meta.env.VITE_MOCK === "true";
const API_URL = import.meta.env.VITE_API_URL ?? "";

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail.error ?? `${method} ${path} failed (${res.status})`);
  }
  return res.json();
}

const http: Api = {
  createRoom: () => call("POST", "/rooms"),
  joinRoom: (code, name) => call("POST", `/rooms/${code}/join`, { name }),
  getRoom: (code) => call("GET", `/rooms/${code}`),
  startRound: (code) => call("POST", `/rooms/${code}/start`),
  uploadUrl: (code, playerId) => call("POST", `/rooms/${code}/upload-url`, { playerId }),
  async putDrawing(url, image) {
    const res = await fetch(url, { method: "PUT", headers: { "Content-Type": "image/jpeg" }, body: image });
    if (!res.ok) throw new Error(`Upload failed (${res.status})`);
  },
  submit: (code, playerId, key) => call("POST", `/rooms/${code}/submit`, { playerId, key }),
  endRound: (code) => call("POST", `/rooms/${code}/end`),
};

export const api: Api = MOCK ? mock : http;
