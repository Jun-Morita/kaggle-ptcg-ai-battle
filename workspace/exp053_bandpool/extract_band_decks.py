"""exp053 -- rebuild the local eval pool from the decks we ACTUALLY face in our
rating band (~700-770), instead of our hand-built proxies.

Motivation (2026-07-13): v020's real ladder record is 27-28 (0.491) while our
local gauntlet said 4.625/6. The two biggest shares are exactly where local
most over-predicts:
    lucario_ex       30.9% share, real wr 0.47  (local said 0.645)
    crustle_control  20.0% share, real wr 0.36  (local said 0.805)
Hypothesis: our local `AC.CRUSTLE_DECK` / `AC.LUCARIO_DECK` proxies are OUR
OWN builds, not what the band actually plays -- so the pool is mis-specified
(the PokeForge "offline pool composition misranks candidates" failure mode,
which we were running in reverse).

This script pulls the opponents' EXACT 60-card decklists out of our own cached
v020 ladder replays (reusing extract_deck.decks_from_replay, which reads the
len-60 deck action), groups them by archetype + exact decklist, and writes the
most common real list per archetype to band_<arch>.json -- ready to drop into a
band-weighted gauntlet.

Usage: uv run python extract_band_decks.py
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

SNAPSHOTS = ["meta_0713_54601467.json", "meta_0712_54601467.json"]
REPLAY_TAGS = ["0713_54601467", "0712_54601467"]


def main():
    byid = card_map()
    res_dir = os.path.join(WS, "exp011_meta_watch", "results")
    base = os.path.join(ROOT, "references", "raw", "replays")

    rows = {}
    for f in SNAPSHOTS:
        p = os.path.join(res_dir, f)
        if os.path.exists(p):
            for r in json.load(open(p))["rows"]:
                rows[r["epid"]] = r
    print(f"pooled {len(rows)} unique ladder games")

    # our own deck (v020 archaludon) -- used to tell which of the two decks in a
    # replay is the OPPONENT's
    my_deck = sorted(json.load(open(os.path.join(WS, "exp049_archaludon", "arch_own_deck.json"))))

    by_arch = defaultdict(Counter)   # arch -> Counter[tuple(sorted deck)]
    arch_wl = defaultdict(lambda: [0, 0])
    for epid, r in rows.items():
        fp = None
        for tag in REPLAY_TAGS:
            c = os.path.join(base, tag, f"episode-{epid}-replay.json")
            if os.path.exists(c):
                fp = c
                break
        if not fp:
            continue
        rep = json.load(open(fp))
        decks = decks_from_replay(rep)
        for idx, d in decks.items():
            if sorted(d) == my_deck:
                continue  # that's us
            by_arch[r["arch"]][tuple(sorted(d))] += 1
        arch_wl[r["arch"]][0 if r["result"] == "W" else 1] += 1

    out = {}
    print(f"\n{'archetype':22} {'games':>5} {'wr':>5}  distinct_lists  top_list_share")
    for arch, ctr in sorted(by_arch.items(), key=lambda kv: -sum(kv[1].values())):
        n = sum(ctr.values())
        w, l = arch_wl[arch]
        wr = w / (w + l) if (w + l) else 0.0
        top_deck, top_n = ctr.most_common(1)[0]
        print(f"{arch:22} {n:5} {wr:5.2f}  {len(ctr):14} {top_n}/{n}")
        path = os.path.join(HERE, f"band_{arch}.json")
        json.dump(list(top_deck), open(path, "w"))
        out[arch] = {"n_games": n, "real_wr": round(wr, 3), "distinct_lists": len(ctr),
                     "top_list_n": top_n, "deck_path": os.path.basename(path)}
        names = Counter(getattr(byid.get(c), "name", str(c)) for c in top_deck)
        key_mons = [f"{nm}x{k}" for nm, k in names.most_common(8)]
        print(f"    top list: {', '.join(key_mons)}")

    json.dump(out, open(os.path.join(HERE, "band_summary.json"), "w"), indent=1)
    print(f"\nwrote band_*.json + band_summary.json to {HERE}")


if __name__ == "__main__":
    main()
