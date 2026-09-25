/**
 * Elimination rules. Mirrors backend/src/shared/elimination.py; keep them in sync
 * (both are exercised by the same scenarios in backend/scripts/test_elimination.py).
 *
 * After each round:
 *  1. Ghosts (dead players) earn a reduced share of their score. A score at or above
 *     `reviveScore` extends their streak, anything lower resets it. At `reviveAfter`
 *     good rounds in a row they come back to life.
 *  2. Among players who were alive at the start of the round, the lowest score dies
 *     (non-submitters score 0). Ties at the bottom all die, unless that would kill
 *     every living player, in which case nobody dies.
 */
export interface ElimPlayer {
  playerId: string;
  alive: boolean;
  streak: number;
}

export interface ElimRules {
  reviveAfter: number;
  reviveScore: number;
  ghostMultiplier: number;
}

export function applyElimination(players: ElimPlayer[], scores: Record<string, number>, rules: ElimRules) {
  const points: Record<string, number> = {};
  const revived: string[] = [];
  const aliveBefore = players.filter((p) => p.alive);
  const next = players.map((p) => ({ ...p }));

  for (const p of next) {
    const raw = scores[p.playerId] ?? 0;
    if (p.alive) {
      points[p.playerId] = raw;
      continue;
    }
    points[p.playerId] = Math.floor(raw * rules.ghostMultiplier);
    p.streak = raw >= rules.reviveScore ? p.streak + 1 : 0;
    if (p.streak >= rules.reviveAfter) {
      p.alive = true;
      p.streak = 0;
      revived.push(p.playerId);
    }
  }

  let eliminated: string[] = [];
  if (aliveBefore.length > 1) {
    const lowest = Math.min(...aliveBefore.map((p) => scores[p.playerId] ?? 0));
    const losers = aliveBefore.filter((p) => (scores[p.playerId] ?? 0) === lowest).map((p) => p.playerId);
    if (losers.length < aliveBefore.length) eliminated = losers;
  }
  for (const p of next) {
    if (eliminated.includes(p.playerId)) {
      p.alive = false;
      p.streak = 0;
    }
  }
  return { players: next, points, eliminated, revived };
}
