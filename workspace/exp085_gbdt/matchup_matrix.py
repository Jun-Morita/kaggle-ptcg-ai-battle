"""Archetype-vs-archetype win matrix from real ladder replays.

The question this answers: our deck is 40.7% of the >=1000 field, so ~40% of our
games are mirrors and a mirror is 0.500 by construction. If some archetype beats
Grimmsnarl (mixed_ex3 / オーロンゲ) reliably, switching converts that 40% from a
coin flip into a favourable matchup -- which is worth more than any amount of
pilot tuning inside the mirror.

Score distributions cannot answer it. They show mixed_ex3 with the lowest mean of
the popular decks, but mixed_ex3 is also the most popular deck, so its mean is
dragged down by copy-paste pilots rather than by the deck. Head-to-head results
between archetypes are not confounded that way.

Reads only the first steps (for the two 60-card lists) and `rewards`, so it is far
cheaper than the featurising pass in build_rows.py.

Usage: uv run python matchup_matrix.py [--days 9] [--min-n 40]
"""
from __future__ import annotations
import glob, json, os, sys, zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2", "exp011_meta_watch", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))
sys.path.insert(0, HERE)

from analyze import card_map, archetype  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def decks_from_ep(ep):
    d = {}
    for st in ep.get("steps", []):
        for i, ag in enumerate(st):
            a = (ag or {}).get("action")
            if isinstance(a, list) and len(a) == 60 and i not in d:
                d[i] = [int(x) for x in a]
        if len(d) >= 2:
            break
    return d


def main():
    ndays = int(arg("--days", "9"))
    min_n = int(arg("--min-n", "40"))
    ipaths = sorted(glob.glob(os.path.join(HERE, "indices", "*.json")))[-ndays:]
    byid = card_map()
    ours = sorted(json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))))

    wins = defaultdict(int)      # (a, b) -> a beat b
    games = defaultdict(int)
    seen = set()
    exact_wins = defaultdict(int)
    exact_games = defaultdict(int)
    stats = Counter()
    for p in ipaths:
        d = json.load(open(p))
        z = zipfile.ZipFile(d["zip"])
        members = {m for (m, _s, _a, _sc) in d["teachers"]}
        for m in members:
            key = (d["zip"], m)
            if key in seen:
                continue
            seen.add(key)
            try:
                ep = json.loads(z.read(m))
            except Exception:
                stats["bad_json"] += 1
                continue
            decks = decks_from_ep(ep)
            if 0 not in decks or 1 not in decks:
                stats["no_deck"] += 1
                continue
            r = ep.get("rewards") or [None, None]
            if r[0] == r[1] or r[0] is None or r[1] is None:
                stats["no_result"] += 1
                continue
            w = 0 if r[0] > r[1] else 1
            a0, a1 = archetype(decks[0], byid), archetype(decks[1], byid)
            aw, al = (a0, a1) if w == 0 else (a1, a0)
            games[(aw, al)] += 1; games[(al, aw)] += 1
            wins[(aw, al)] += 1
            # the same, restricted to the winner running OUR exact 60 cards --
            # separates "this archetype beats us" from "this decklist beats us"
            if sorted(decks[w]) == ours:
                exact_games[al] += 1; exact_wins[al] += 1
            if sorted(decks[1 - w]) == ours:
                exact_games[aw] += 1
            stats["games"] += 1

    archs = sorted({a for a, _ in games} | {b for _, b in games},
                   key=lambda a: -sum(games[(a, b)] for b in
                                      {x for x, _ in games} | {y for _, y in games}))
    archs = [a for a in archs
             if sum(games[(a, b)] for b in archs) >= min_n][:9]
    print(f"days={len(ipaths)}  games={stats['games']}  skips={dict(stats)}\n")
    print("row beats column (win rate of ROW), n in parentheses\n")
    w = 13
    print(" " * 18 + "".join(f"{a[:11]:>{w}}" for a in archs))
    for a in archs:
        line = f"{a[:17]:<18}"
        for b in archs:
            n = games[(a, b)]
            line += f"{wins[(a,b)]/n:>8.3f}({n:>3})"[-w:] if n >= 10 else f"{'-':>{w}}"
        print(line)

    print("\nagainst OUR exact 60 cards (winner ran our list), by opponent archetype")
    for a in sorted(exact_games, key=lambda x: -exact_games[x]):
        n = exact_games[a]
        if n >= 20:
            print(f"  {a:<20} our winrate {exact_wins[a]/n:.3f}  (n={n})")


if __name__ == "__main__":
    main()
