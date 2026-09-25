import type { GameMode, ModeSetting } from "./types";

// Change the game name / copy here; it's used on every screen.
export const GAME_NAME = "Amacide";
/** Trailing part of the name drawn in the AI's red glitch font in the logo. */
export const GAME_NAME_ACCENT = "cide";
export const TAGLINE = "Draw it. Type it. The AI decides your fate.";

/** Host picks the number of rounds in the lobby (contracts/api.md: POST /start {totalRounds}). */
export const DEFAULT_ROUNDS = 3;
export const MAX_ROUNDS = 10;

/** Elimination: lowest score each round dies; ghosts earn reduced points and can revive. */
export const ELIMINATION = {
  defaultOn: false,
  defaultReviveAfter: 2,
  maxReviveAfter: 5,
  /** A dead player's round counts towards reviving at this score or higher. */
  reviveScore: 6,
  /** Ghosts earn this fraction of their score (rounded down). */
  ghostMultiplier: 0.5,
};

/** Max characters for Survive / Quick Wit answers (the backend enforces the same limit). */
export const TEXT_LIMIT = 200;

export interface ModeInfo {
  name: string;
  emoji: string;
  blurb: string;
  /** Shown above the prompt, e.g. "Draw this". */
  instruction: string;
  /** Plural of what players submit, e.g. "drawings". */
  noun: string;
  placeholder?: string;
}

export const MODES: Record<GameMode, ModeInfo> = {
  draw: {
    name: "Draw",
    emoji: "🎨",
    blurb: "Draw the prompt. The AI judges how recognisable it is.",
    instruction: "Draw this",
    noun: "drawings",
  },
  survive: {
    name: "Survive",
    emoji: "☠️",
    blurb: "Type how you'd survive. The AI decides who lives.",
    instruction: "Survive this",
    noun: "plans",
    placeholder: "How do you survive?",
  },
  wit: {
    name: "Quick Wit",
    emoji: "💬",
    blurb: "Type the funniest answer. The AI picks the best.",
    instruction: "Answer this",
    noun: "answers",
    placeholder: "Your funniest answer…",
  },
};

export const MIXED: Omit<ModeInfo, "instruction" | "noun"> = {
  name: "Mixed",
  emoji: "🔀",
  blurb: "A different mode every round: Draw, then Survive, then Quick Wit.",
};

export const DEFAULT_MODE: ModeSetting = "mixed";
export const MODE_SETTINGS: ModeSetting[] = ["mixed", "draw", "survive", "wit"];
export const settingInfo = (m: ModeSetting) => (m === "mixed" ? MIXED : MODES[m]);

/** Base URL phones use to join (QR code). Set VITE_PUBLIC_URL when the host screen isn't on the public URL. */
export const JOIN_BASE_URL = import.meta.env.VITE_PUBLIC_URL || location.origin;

export const joinUrl = (code: string) => `${JOIN_BASE_URL}/?room=${code}`;
