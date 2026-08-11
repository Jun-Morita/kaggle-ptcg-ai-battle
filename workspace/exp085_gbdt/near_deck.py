"""How close are the teacher decks we throw away?

The exact-60 filter drops 22,415 of 45,840 mixed_ex3 teacher seats -- 49% of the
only lever that has ever worked. Relaxing it is the largest untapped source of
data, but v2 proved that training on somebody else's list is worse than having
less data (held-out rose 0.684 -> 0.798 while head-to-head fell 0.510 -> 0.315).

So the question is not "should we relax the filter" but "how far away are the
seats we are dropping". A pile of 58/60 lists is a different proposition from a
pile of 45/60 lists. This counts the overlap distribution, and for the near
misses, WHICH cards differ.

Usage: uv run python near_deck.py [--days 2026-08-01,...] [--cap 600]
"""
from __future__ import annotations
import glob, json, os, sys, zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2", "exp011_meta_watch", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))
sys.path.insert(0, HERE)
import feats  # noqa: E402

NAME = {int(c.cardId): c.name for c in feats.all_card_data()}
OURS = sorted(json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))))
OURC = Counter(OURS)


def arg(n, d=None):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


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
    days = (arg("--days") or ",".join(
        sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(HERE, "indices", "2026-*.json")))[-12:]
    )).split(",")
    cap = int(arg("--cap", "600"))
    hist = Counter()          # overlap size -> seats
    missing = Counter()       # card we run that a near-miss teacher lacks
    extra = Counter()         # card they run that we do not
    near_lists = Counter()
    for day in days:
        p = os.path.join(HERE, "indices", f"{day}.json")
        if not os.path.exists(p):
            continue
        d = json.load(open(p))
        z = zipfile.ZipFile(d["zip"])
        seats = [(m, s) for (m, s, a, _sc) in d["teachers"] if a == "mixed_ex3"]
        for m, s in seats[:cap]:
            try:
                ep = json.loads(z.read(m))
            except Exception:
                continue
            dk = decks_from_ep(ep)
            if s not in dk:
                continue
            c = Counter(dk[s])
            ov = sum((c & OURC).values())        # multiset intersection = shared cards
            hist[ov] += 1
            if 54 <= ov < 60:
                near_lists[tuple(sorted(dk[s]))] += 1
                for cid, k in (OURC - c).items():
                    missing[cid] += k
                for cid, k in (c - OURC).items():
                    extra[cid] += k
    tot = sum(hist.values())
    print(f"days={len(days)} seats sampled={tot}\n")
    print("overlap with our 60 cards:")
    cum = 0
    for ov in sorted(hist, reverse=True):
        cum += hist[ov]
        print(f"  {ov:>2}/60  {hist[ov]:>5}  {hist[ov]/tot:6.1%}   cumulative >= {ov}: {cum/tot:6.1%}")
    print(f"\nnear misses (54-59 of 60): {sum(v for k,v in hist.items() if 54<=k<60)} seats, "
          f"{len(near_lists)} distinct lists")
    print("\ncards WE run that the near misses cut:")
    for cid, k in missing.most_common(10):
        print(f"  -{k:<5} {cid:>5}  {NAME.get(cid,'?')}")
    print("\ncards the near misses run that we do NOT:")
    for cid, k in extra.most_common(10):
        print(f"  +{k:<5} {cid:>5}  {NAME.get(cid,'?')}")


if __name__ == "__main__":
    main()
