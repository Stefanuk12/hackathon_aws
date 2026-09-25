// Mirrors contracts/api.md and contracts/fixtures/*.json.
export type RoomState = "lobby" | "drawing" | "judging" | "results";

/** What a single round is. */
export type GameMode = "draw" | "survive" | "wit";
/** What the host picks in the lobby: one mode for every round, or "mixed". */
export type ModeSetting = GameMode | "mixed";

export interface Player {
  playerId: string;
  name: string;
  score: number;
  submitted?: boolean;
  /** Elimination only: false once eliminated (a "ghost" until revived). */
  alive?: boolean;
  /** Elimination only: good rounds in a row towards reviving (dead players). */
  streak?: number;
}

export interface Result {
  playerId: string;
  name: string;
  rank: number;
  score: number;
  roast: string;
  /** Draw rounds. */
  imageUrl?: string;
  /** Survive / Quick Wit rounds. */
  text?: string;
  /** Survive rounds only. */
  survived?: boolean;
  /** Points actually added to the total (the score, or half of it for ghosts). */
  points?: number;
  /** Elimination only: this player was dead during the round. */
  ghost?: boolean;
}

/** Elimination only: who died and who came back at the end of this round. */
export interface RoundOutcome {
  eliminated: string[];
  revived: string[];
}

export interface GameSettings {
  totalRounds?: number;
  mode?: ModeSetting;
  elimination?: boolean;
  /** Good rounds in a row a dead player needs to revive. */
  reviveAfter?: number;
}

/** Draw rounds send the uploaded image key; text rounds send the answer. */
export type Submission = { key: string } | { text: string };

/** True once the last round's results are in: time for final scores, not "Next round". */
export const isGameOver = (room: Room) => room.state === "results" && room.round >= room.totalRounds;

export interface Room {
  code: string;
  state: RoomState;
  round: number;
  totalRounds: number;
  mode: ModeSetting;
  elimination: boolean;
  reviveAfter: number;
  /** The current round's mode; set once a round has started. */
  roundMode?: GameMode;
  prompt?: string;
  endsAt?: number;
  players: Player[];
  results?: Result[];
  /** Present in "results" when elimination is on. */
  outcome?: RoundOutcome;
  audioUrl?: string | null;
}
