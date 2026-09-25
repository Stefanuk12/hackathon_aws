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
  /** The current round's mode; set once a round has started. */
  roundMode?: GameMode;
  prompt?: string;
  endsAt?: number;
  players: Player[];
  results?: Result[];
  audioUrl?: string | null;
}
