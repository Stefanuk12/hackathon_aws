"""Elimination rules. Mirrors frontend/src/elimination.ts; keep them in sync.

After each round:
 1. Ghosts (dead players) earn a reduced share of their score. A score at or above
    revive_score extends their streak, anything lower resets it. At revive_after
    good rounds in a row they come back to life.
 2. Among players who were alive at the start of the round, the lowest score dies
    (non-submitters score 0). Ties at the bottom all die, unless that would kill
    every living player, in which case nobody dies.

save_results calls this when the room has elimination on.
"""

import math

REVIVE_SCORE = 6
GHOST_MULTIPLIER = 0.5


def apply_elimination(players, scores, revive_after, revive_score=REVIVE_SCORE, ghost_multiplier=GHOST_MULTIPLIER):
    """players: [{"playerId", "alive", "streak"}]; scores: {playerId: 0-10} (missing = 0).

    Returns {"players": updated copies, "points": {playerId: points to add},
             "eliminated": [playerId], "revived": [playerId]}.
    """
    points, revived = {}, []
    alive_before = [p for p in players if p["alive"]]
    nxt = [dict(p) for p in players]

    for p in nxt:
        raw = scores.get(p["playerId"], 0)
        if p["alive"]:
            points[p["playerId"]] = raw
            continue
        points[p["playerId"]] = math.floor(raw * ghost_multiplier)
        p["streak"] = p["streak"] + 1 if raw >= revive_score else 0
        if p["streak"] >= revive_after:
            p["alive"], p["streak"] = True, 0
            revived.append(p["playerId"])

    eliminated = []
    if len(alive_before) > 1:
        lowest = min(scores.get(p["playerId"], 0) for p in alive_before)
        losers = [p["playerId"] for p in alive_before if scores.get(p["playerId"], 0) == lowest]
        if len(losers) < len(alive_before):
            eliminated = losers
    for p in nxt:
        if p["playerId"] in eliminated:
            p["alive"], p["streak"] = False, 0

    return {"players": nxt, "points": points, "eliminated": eliminated, "revived": revived}
