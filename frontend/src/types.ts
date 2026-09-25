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

/** True once the last round's results are in: time for final scores, not "Next round". */
export const isGameOver = (room: Room) => room.state === "results" && room.round >= room.totalRounds;

export interface Room {
  code: string;
  state: RoomState;
  round: number;
  totalRounds: number;
  prompt?: string;
  endsAt?: number;
  players: Player[];
  results?: Result[];
  audioUrl?: string | null;
}
