"""What IS a given archetype, and how much exact-list teacher data does it have?

mixed_ex4 was 0.4% of teachers on 07-28 and 18.9% on 08-08, and four of the top
fifteen teams moved onto it from our own archetype. Before any talk of switching
decks, two things have to be known: the exact 60-card list the strong pilots run
(the label is a fuzzy classifier -- training on the label instead of the list is
what made the v2 corpus worse than no data), and how many exact-match seats
exist, since corpus size is worth real winrate.

Usage: uv run python probe_arch.py [--arch mixed_ex4] [--days 08-05,...] [--cap 400]
"""
from __future__ import annotations
import glob, json, os, sys, zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2", "exp011_meta_watch", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))
sys.path.insert(0, HERE)
import feats  # noqa: E402  (loads the engine, gives card names)

NAME = {int(c.cardId): c.name for c in feats.all_card_data()}


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
    target = arg("--arch", "mixed_ex4")
    days = (arg("--days", "08-04,08-05,08-06,08-07,08-08")).split(",")
    cap = int(arg("--cap", "400"))
    lists = Counter()
    best_for = {}
    for day in days:
        p = os.path.join(HERE, "indices", f"2026-{day}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        z = zipfile.ZipFile(d["zip"])
        seats = [(m, s, sc) for (m, s, a, sc) in d["teachers"] if a == target]
        for m, s, sc in seats[:cap]:
            try:
                ep = json.loads(z.read(m))
            except Exception:
                continue
            dk = decks_from_ep(ep)
            if s not in dk:
                continue
            key = tuple(sorted(dk[s]))
            lists[key] += 1
            if sc is not None and sc > best_for.get(key, 0):
                best_for[key] = sc
    tot = sum(lists.values())
    print(f"archetype={target}  days={days}  seats sampled={tot}  "
          f"distinct 60-card lists={len(lists)}")
    if not tot:
        return
    print("\ntop lists by frequency:")
    for key, n in lists.most_common(5):
        print(f"   {n:>5} seats ({n/tot:5.1%})   best score {best_for.get(key,0):.1f}")
    key, n = lists.most_common(1)[0]
    print(f"\nthe most common list ({n} seats, {n/tot:.1%} of this archetype):")
    for cid, k in sorted(Counter(key).items(), key=lambda x: (-x[1], x[0])):
        print(f"   x{k:<3} {cid:>5}  {NAME.get(cid,'?')}")
    out = os.path.join(HERE, f"deck_{target}.json")
    json.dump(list(key), open(out, "w"))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
