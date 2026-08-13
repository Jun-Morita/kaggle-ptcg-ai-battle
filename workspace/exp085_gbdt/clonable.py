"""Which archetypes are actually CLONABLE?

Imitation needs many people playing the same 60 cards the same way. An archetype
label does not guarantee that: ex_beatdown's most common list is only 20% of its
seats (Mega Kangaskhan ex / Slowking / Latias ex / Kyurem in one pile), so
copying it yielded 840 usable seats and a 0.609 top-k. Grimmsnarl's is 74%.

For each archetype this prints how concentrated the lists are and, more to the
point, how many teacher seats a clone would actually get.
"""
from __future__ import annotations
import glob, json, os, sys, zipfile
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))


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
    days = (sys.argv[1] if len(sys.argv) > 1 else
            "08-08,08-09,08-10,08-11,08-12").split(",")
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else 220
    lists = defaultdict(Counter)
    for day in days:
        p = os.path.join(HERE, "indices", f"2026-{day}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        z = zipfile.ZipFile(d["zip"])
        per = Counter()
        for (m, s, a, _sc) in d["teachers"]:
            if per[a] >= cap:
                continue
            per[a] += 1
            try:
                dk = decks_from_ep(json.loads(z.read(m)))
            except Exception:
                continue
            if s in dk:
                lists[a][tuple(sorted(dk[s]))] += 1
    print(f"days={days} cap={cap}/archetype/day\n")
    print(f"{'archetype':<20}{'seats':>7}{'lists':>7}{'top1':>8}{'top3':>8}"
          f"{'clone seats/day':>17}")
    rows = []
    for a, c in lists.items():
        n = sum(c.values())
        if n < 60:
            continue
        top1 = c.most_common(1)[0][1] / n
        top3 = sum(v for _, v in c.most_common(3)) / n
        rows.append((top1 * n, a, n, len(c), top1, top3))
    for _, a, n, k, t1, t3 in sorted(rows, key=lambda r: -r[0]):
        print(f"{a:<20}{n:>7}{k:>7}{t1:>8.0%}{t3:>8.0%}{t1*n/len(days):>17.0f}")
    print("\n'clone seats/day' = seats whose list is EXACTLY the most common one,"
          " per day\n(capped, so read it as a ranking, not an absolute)")


if __name__ == "__main__":
    main()
