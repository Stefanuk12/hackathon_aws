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
