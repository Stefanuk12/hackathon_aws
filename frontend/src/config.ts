// Change the game name / copy here; it's used on every screen.
export const GAME_NAME = "Judged by AI";
export const TAGLINE = "Draw it. The AI decides your fate.";

/** Host picks the number of rounds in the lobby (contracts/api.md: POST /start {totalRounds}). */
export const DEFAULT_ROUNDS = 3;
export const MAX_ROUNDS = 10;

/** Base URL phones use to join (QR code). Set VITE_PUBLIC_URL when the host screen isn't on the public URL. */
export const JOIN_BASE_URL = import.meta.env.VITE_PUBLIC_URL || location.origin;

export const joinUrl = (code: string) => `${JOIN_BASE_URL}/?room=${code}`;
