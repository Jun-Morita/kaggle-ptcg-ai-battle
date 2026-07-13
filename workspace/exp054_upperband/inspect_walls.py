"""exp054 -- CORRECTNESS FIX: the crustle bucket is majority PURE WALL, not LO.

exp053 put the LO-mill deck into the band pool as the crustle_control
representative because it was the most common single *exact* decklist. But the
majority of that bucket is pure-wall (82% of our band's crustle games, 65% of
the silver band's) -- pure-wall builds just vary more, so no single list wins
the "most common exact list" vote. That means the 20%-weight crustle slot in
eval_band.py is STILL represented by the wrong deck, and every candidate's
band score is distorted:

    LO-mill  : pool says 0.692, but it scores 0.033 vs pure wall -> ~0.615 real
    v016-wall: pool says 0.646, but pure wall is its own MIRROR (~0.5), while
               the pool credited it 0.890 vs the LO variant       -> ~0.582 real

So this may even flip the our-band ranking. Before re-running anything, dump
the actual pure-wall lists we faced and check what they really are (are they
AC.CRUSTLE_DECK-like heal-walls, or something else?), then emit the most common
real pure-wall list as a proper pool opponent.

Usage: uv run python inspect_walls.py
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))
sys.path.insert(0, os.path.join(WS, "exp007_anti_crustle"))

from extract_deck import decks_from_replay  # noqa: E402
from analyze import card_map  # noqa: E402
import anti_crustle as AC  # noqa: E402

GREAT_TUSK, EXPLORER = 58, 1185

SOURCES = [
    ("meta_0713_54601467.json", "0713_54601467",
     os.path.join(WS, "exp049_archaludon", "arch_own_deck.json"), "our band"),
    ("top_tomatomato_0712.json", "top_tomatomato_0712",
     os.path.join(WS, "exp011_meta_watch", "tomatomato_deck.json"), "silver band"),
    ("top_tomatomato_0624.json", "top_tomatomato_0624",
     os.path.join(WS, "exp011_meta_watch", "tomatomato_deck.json"), "silver band"),
]


def main():
    byid = card_map()
    res = os.path.join(WS, "exp011_meta_watch", "results")
    base = os.path.join(ROOT, "references", "raw", "replays")

    walls = Counter()      # tuple(sorted deck) -> games, pure-wall only
    per_band = Counter()
    for snap, tag, own_path, band in SOURCES:
        p = os.path.join(res, snap)
        if not os.path.exists(p):
            continue
        own = sorted(json.load(open(own_path)))
        d = json.load(open(p))
        key = "arch" if "arch" in d["rows"][0] else "opp_arch"
        for r in d["rows"]:
            if r[key] != "crustle_control":
                continue
            fp = os.path.join(base, tag, f"episode-{r['epid']}-replay.json")
            if not os.path.exists(fp):
                continue
            for _, deck in decks_from_replay(json.load(open(fp))).items():
                if sorted(deck) == own:
                    continue
                is_lo = (GREAT_TUSK in deck) or (EXPLORER in deck)
                per_band[(band, "LO" if is_lo else "PURE_WALL")] += 1
                if not is_lo:
                    walls[tuple(sorted(deck))] += 1

    print("crustle bucket composition:")
    for k, v in sorted(per_band.items()):
        print(f"  {k[0]:12} {k[1]:10} {v}")

    if not walls:
        print("\nno pure-wall decks found")
        return

    print(f"\n{len(walls)} distinct pure-wall lists, {sum(walls.values())} games")
    top, n = walls.most_common(1)[0]
    names = Counter(getattr(byid.get(c), "name", str(c)) for c in top)
    print(f"\nmost common pure-wall list ({n} games):")
    print("  " + ", ".join(f"{nm}x{k}" for nm, k in names.most_common()))

    # how close is it to OUR proxy (AC.CRUSTLE_DECK, what v016-wall runs)?
    ours = Counter(getattr(byid.get(c), "name", str(c)) for c in AC.CRUSTLE_DECK)
    same = sum((names & ours).values())
    print(f"\noverlap with AC.CRUSTLE_DECK (our v016-wall list): {same}/60")
    print("  only in the real list: " + ", ".join(f"{k}x{v}" for k, v in (names - ours).items()))
    print("  only in ours         : " + ", ".join(f"{k}x{v}" for k, v in (ours - names).items()))

    out = os.path.join(HERE, "band_pure_wall.json")
    json.dump(list(top), open(out, "w"))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
