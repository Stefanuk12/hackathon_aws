// Mirrors contracts/api.md and contracts/fixtures/*.json.
export type RoomState = "lobby" | "drawing" | "judging" | "results";

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
  imageUrl: string;
}

export interface Room {
  code: string;
  state: RoomState;
  round: number;
  prompt?: string;
  endsAt?: number;
  players: Player[];
  results?: Result[];
  audioUrl?: string | null;
}

export type GameEvent =
  | { type: "player_joined"; playerId: string; name: string }
  | { type: "round_started"; round: number; prompt: string; endsAt: number }
  | { type: "submission_in"; playerId: string; submitted: number; total: number }
  | { type: "judging"; round: number }
  | { type: "results_ready"; round: number; results: Result[]; audioUrl: string | null };
