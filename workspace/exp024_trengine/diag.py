"""Diagnose how OUR policy drives a deck: first-attack turn + what it fetches (TO_HAND).

Wraps our agent to log, per game, the turn it first attacks and the cards it fetches.
Compare TR (yushin) vs our charmq under the same policy to locate the engine gap.
Usage: DECK=yushin|charmq uv run python diag.py [n]
"""
from __future__ import annotations
import csv, json, os, sys
from collections import Counter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp018_adaptive", "exp022_megastarmie", "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
os.environ.setdefault("REVENGE_BONUS", "50")
import revenge_policy as P  # noqa

names = {}
with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
    for r in csv.DictReader(f):
        names[int(r["Card ID"])] = r["Card Name"]

DECKS = {"yushin": os.path.join(os.path.dirname(__file__), "yushin_deck.json"),
         "charmq": os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")}

fetched = Counter()
first_atk = []
_state = {"turn_attacked": None}


def load_deck(name):
    d = json.load(open(DECKS[name]))
    return d.get("charmq") if isinstance(d, dict) else d


def make_logged(deck):
    base = P.make_agent(deck)
    def agent(obs):
        sel = obs.get("select") if isinstance(obs, dict) else None
        out = base(obs)
        try:
            if sel:
                ctx = sel.get("context"); opts = sel.get("option", [])
                cur = obs.get("current") or {}
                me = (cur.get("players") or [None, None])[cur.get("yourIndex", 0)]
                turn = cur.get("turn", 0)
                if opts and len(opts) != 60:
                    for ci in out:
                        if isinstance(ci, int) and ci < len(opts):
                            o = opts[ci]
                            if o.get("type") == 13 and _state["turn_attacked"] is None:
                                _state["turn_attacked"] = turn
                            # TO_HAND-ish: option referencing a deck card id
                            c = o.get("cardId") or o.get("id")
                            if ctx in (2, 3, 6, 7) and c:
                                fetched[names.get(int(c), f"#{c}")] += 1
        except Exception:
            pass
        return out
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    deckname = os.environ.get("DECK", "yushin")
    deck = load_deck(deckname)
    opp = AC.make_agent(AC.LUCARIO_DECK)  # vs ex (our weak matchup with TR)
    for g in range(n):
        _state["turn_attacked"] = None
        run_gauntlet(make_logged(deck), opp, n_games=1, swap_sides=False)
        if _state["turn_attacked"] is not None:
            first_atk.append(_state["turn_attacked"])
    avg = lambda xs: sum(xs)/len(xs) if xs else float("nan")
    print(f"# deck={deckname} vs ex, n={n}")
    print(f"first-attack turn: {avg(first_atk):.1f} (n={len(first_atk)})")
    print("top fetches:", ", ".join(f"{k}={v}" for k, v in fetched.most_common(12)))


if __name__ == "__main__":
    main()
