"""Scenario tests for the elimination rules (Python), plus a JSON dump the
frontend test replays against frontend/src/elimination.ts.

    python backend/scripts/test_elimination.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from shared.elimination import apply_elimination  # noqa: E402


def P(pid, alive=True, streak=0):
    return {"playerId": pid, "alive": alive, "streak": streak}


SCENARIOS = [
    ("lowest alive player dies", [P("a"), P("b"), P("c")], {"a": 8, "b": 3, "c": 6}, 2,
     {"eliminated": ["b"], "revived": [], "points": {"a": 8, "b": 3, "c": 6}}),
    ("tied lowest both die", [P("a"), P("b"), P("c")], {"a": 8, "b": 3, "c": 3}, 2,
     {"eliminated": ["b", "c"], "revived": []}),
    ("everyone tied: nobody dies", [P("a"), P("b")], {"a": 5, "b": 5}, 2,
     {"eliminated": [], "revived": []}),
    ("last one alive can't die", [P("a"), P("b", alive=False)], {"a": 1, "b": 9}, 2,
     {"eliminated": [], "revived": []}),
    ("non-submitter scores 0 and dies", [P("a"), P("b"), P("c")], {"a": 2, "b": 4}, 2,
     {"eliminated": ["c"], "points": {"a": 2, "b": 4, "c": 0}}),
    ("ghost gets half points (rounded down)", [P("a"), P("b"), P("g", alive=False)], {"a": 5, "b": 7, "g": 7}, 2,
     {"points": {"a": 5, "b": 7, "g": 3}, "streak": {"g": 1}, "alive": {"g": False}}),
    ("ghost bad round resets streak", [P("a"), P("b"), P("g", alive=False, streak=1)], {"a": 5, "b": 7, "g": 5}, 2,
     {"streak": {"g": 0}, "revived": []}),
    ("ghost revives on streak", [P("a"), P("b"), P("g", alive=False, streak=1)], {"a": 5, "b": 7, "g": 9}, 2,
     {"revived": ["g"], "alive": {"g": True}, "streak": {"g": 0}, "eliminated": ["a"], "points": {"g": 4}}),
    ("revive after 1 revives immediately", [P("a"), P("b"), P("g", alive=False)], {"a": 5, "b": 7, "g": 6}, 1,
     {"revived": ["g"]}),
    ("revived player isn't eliminated in the same round", [P("a"), P("b"), P("g", alive=False, streak=1)], {"a": 4, "b": 7, "g": 6}, 2,
     {"revived": ["g"], "eliminated": ["a"]}),
]


def check(name, result, expect):
    by_id = {p["playerId"]: p for p in result["players"]}
    for key in ("eliminated", "revived"):
        if key in expect:
            assert result[key] == expect[key], (name, key, result[key])
    for pid, pts in expect.get("points", {}).items():
        assert result["points"][pid] == pts, (name, "points", pid, result["points"][pid])
    for pid, s in expect.get("streak", {}).items():
        assert by_id[pid]["streak"] == s, (name, "streak", pid)
    for pid, a in expect.get("alive", {}).items():
        assert by_id[pid]["alive"] == a, (name, "alive", pid)


if __name__ == "__main__":
    for name, players, scores, revive_after, expect in SCENARIOS:
        check(name, apply_elimination(players, scores, revive_after), expect)
        print("PASS", name)
    if "--dump" in sys.argv:
        print(json.dumps([{"name": n, "players": p, "scores": s, "reviveAfter": r, "expect": e} for n, p, s, r, e in SCENARIOS]))
