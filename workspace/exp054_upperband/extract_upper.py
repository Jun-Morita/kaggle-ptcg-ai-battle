"""exp054 -- build the UPPER-BAND (silver-boundary) opponent pool.

Why: exp053 gave us a calibrated Elo model, which says silver (933) is not
reachable by being better in OUR band (700-770) -- climbing changes who you
face. So we must measure against the band we'd need to survive AT silver.

We have never played there, but tomatomato did: their cached submission sat at
**LB 948.8** -- right on the silver boundary (933) -- and we hold 537 of their
ladder replays. Their OPPONENTS are therefore a direct sample of the
silver-band field. (taksai's cache, LB ~1304, samples the elite band above it;
kept as a secondary reference.)

The composition is drastically different from our band, which is the whole
point:
                        our band (700-770)   tomatomato's band (~948)
    lucario_ex                31%                    6.9%
    crustle_control (LO)      20%                    3.7%
    mixed_ex4 (Archaludon)     9%                   35.2%   <-- the wall up there
    non_ex_attackers           9%                   21.6%
So v016-wall / LO-mill's local strength rests on beating decks that are nearly
ABSENT at silver, while the 35% Archaludon slice crushes v016-wall (0.170) and
v019 (0.160). Only LO-mill holds up there (0.687).

Same method as exp053's extract_band_decks.py: pull the OPPONENT's exact 60-card
deck out of each cached replay, group by archetype, keep the most common real
list per archetype, and record the real share + the cache owner's own W-L.

Usage: uv run python extract_upper.py
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

from extract_deck import decks_from_replay  # noqa: E402
from analyze import card_map  # noqa: E402

# (snapshot json, replay cache dir, the cache owner's own decklist)
SOURCES = [
    ("top_tomatomato_0712.json", "top_tomatomato_0712", "tomatomato_deck.json"),
    ("top_tomatomato_0624.json", "top_tomatomato_0624", "tomatomato_deck.json"),
]


def main():
    byid = card_map()
    res = os.path.join(WS, "exp011_meta_watch", "results")
    base = os.path.join(ROOT, "references", "raw", "replays")

    by_arch = defaultdict(Counter)      # arch -> Counter[deck tuple]
    arch_n = Counter()                  # arch -> games
    owner_wl = defaultdict(lambda: [0, 0])

    for snap, tag, own_json in SOURCES:
        p = os.path.join(res, snap)
        if not os.path.exists(p):
            print(f"  !! missing snapshot {snap}")
            continue
        own = sorted(json.load(open(os.path.join(WS, "exp011_meta_watch", own_json))))
        d = json.load(open(p))
        n_ok = 0
        for r in d["rows"]:
            fp = os.path.join(base, tag, f"episode-{r['epid']}-replay.json")
            if not os.path.exists(fp):
                continue
            rep = json.load(open(fp))
            arch = r["opp_arch"]
            for idx, deck in decks_from_replay(rep).items():
                if sorted(deck) == own:
                    continue                       # that's the cache owner
                by_arch[arch][tuple(sorted(deck))] += 1
            arch_n[arch] += 1
            owner_wl[arch][0 if r["result"] == "W" else 1] += 1
            n_ok += 1
        print(f"{tag}: {n_ok} replays parsed")

    tot = sum(arch_n.values())
    out = {}
    print(f"\npooled {tot} silver-band games\n")
    print(f"{'archetype':22} {'share':>6} {'owner W-L':>10} {'lists':>6}  top list")
    for arch, n in arch_n.most_common():
        ctr = by_arch[arch]
        if not ctr:
            continue
        w, l = owner_wl[arch]
        top_deck, top_n = ctr.most_common(1)[0]
        path = os.path.join(HERE, f"up_{arch}.json")
        json.dump(list(top_deck), open(path, "w"))
        names = Counter(getattr(byid.get(c), "name", str(c)) for c in top_deck)
        key = ", ".join(f"{nm}x{k}" for nm, k in names.most_common(5))
        print(f"{arch:22} {n/tot*100:5.1f}% {w:4}-{l:<4} {len(ctr):6}  {key}")
        out[arch] = {"share": round(n / tot, 4), "games": n,
                     "owner_wr": round(w / (w + l), 3) if (w + l) else None,
                     "distinct_lists": len(ctr), "top_list_n": top_n,
                     "deck": f"up_{arch}.json"}

    json.dump(out, open(os.path.join(HERE, "upper_summary.json"), "w"), indent=1)
    print(f"\nwrote up_*.json + upper_summary.json to {HERE}")


if __name__ == "__main__":
    main()
