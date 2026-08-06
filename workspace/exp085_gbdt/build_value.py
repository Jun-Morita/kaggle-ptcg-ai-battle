"""State -> win probability rows, for the search that exp085 does not yet have.

The ranker says which option looks like the teacher's; it says nothing about
whether the resulting position is good. Search needs that second thing.

Two ways to get it, and the choice matters for the time budget:

  rollouts       play the position out with the policy. Honest, needs no extra
                 model -- but a full game is ~400 decisions across both seats, so
                 one rollout costs ~0.2s and a 600s game budget buys roughly 25
                 per decision. Too thin to sharpen anything.
  learned value  a second GBDT over the same flat state. Inference is a few
                 microseconds, so the same budget buys three orders of magnitude
                 more evaluations.

This builds the training data for the second. Unlike build_rows.py it keeps BOTH
seats: a value model needs losses. It also emits one row per decision instead of
one per option, so the corpus is ~7x smaller than the ranking one.

Deck filter is still exact -- the reason it exists (our 60 cards did not exist in
the meta before 07-17) applies just as much to "was this position winning".

Usage: uv run python build_value.py [--max-dec N] [--out v1]
"""
from __future__ import annotations
import glob, json, os, pickle, sys, zipfile
from collections import Counter
from itertools import zip_longest

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
for p in ("exp001_harness", "exp040_mctsv2", "exp011_meta_watch", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))

import feats  # noqa: E402
import numpy as np  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from build_rows import arg, decks_from_ep  # noqa: E402


def main():
    target = arg("--arch", "mixed_ex3")
    max_dec = int(arg("--max-dec", "400000"))
    tag = arg("--out", "v1")
    exact = sorted(json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))))
    days = []
    for p in sorted(glob.glob(os.path.join(HERE, "indices", "*.json"))):
        d = json.load(open(p))
        s = [(d["zip"], m) for (m, _seat, a, _sc) in d["teachers"] if a == target]
        if s:
            days.append(s)
    # de-dup: a game can appear once per qualifying seat, and we take both seats
    seen, games = set(), []
    for grp in zip_longest(*days):
        for x in grp:
            if x is not None and x not in seen:
                seen.add(x)
                games.append(x)
    print(f"games={len(games)} max_dec={max_dec}", flush=True)

    zips, stats = {}, Counter()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out = os.path.join(HERE, "results", f"value_{tag}.pkl")
    Y, X = [], []
    with open(out, "wb") as fout:
        def flush():
            if not X:
                return
            pickle.dump((np.array(Y, np.int8), np.asarray(X, np.float32)),
                        fout, protocol=4)
            Y.clear(); X.clear()

        for n, (zp, member) in enumerate(games):
            try:
                z = zips.get(zp) or zips.setdefault(zp, zipfile.ZipFile(zp))
                ep = json.loads(z.read(member))
            except Exception:
                stats["skip_json"] += 1
                continue
            decks = decks_from_ep(ep)
            rewards = ep.get("rewards") or [None, None]
            steps = ep.get("steps", [])
            for ti in (0, 1):
                if not decks.get(ti) or sorted(decks[ti]) != exact:
                    stats["skip_deck"] += 1
                    continue
                r = rewards[ti] if ti < len(rewards) else None
                if r not in (1, -1):
                    stats["skip_draw"] += 1
                    continue
                won = 1 if r == 1 else 0
                history = []
                for si, st in enumerate(steps):
                    if ti >= len(st) or st[ti].get("status") != "ACTIVE":
                        continue
                    obs = st[ti].get("observation")
                    if not isinstance(obs, dict) or obs.get("select") is None:
                        continue
                    try:
                        oc = to_observation_class(obs)
                    except Exception:
                        continue
                    if oc.select is None or not oc.select.option:
                        continue
                    try:
                        row = feats.base_state(oc, history)
                    except Exception:
                        stats["skip_feat"] += 1
                        continue
                    # history is advanced from the ACTUAL next action so the
                    # turn-scoped counters mean the same thing they do at play time
                    act = steps[si + 1][ti].get("action") \
                        if si + 1 < len(steps) and ti < len(steps[si + 1]) else None
                    if isinstance(act, list) and len(act) != 60:
                        try:
                            sems = [feats.semantic(oc, o) for o in oc.select.option]
                            for i in act:
                                if isinstance(i, int) and 0 <= i < len(sems):
                                    history.append((oc.current.turn, sems[i]))
                            history = history[-40:]
                        except Exception:
                            pass
                    X.append(row); Y.append(won)
                    stats["recorded"] += 1
                    stats["won" if won else "lost"] += 1
                    if len(X) >= 400000:
                        flush()
            if stats["recorded"] >= max_dec:
                print(f"  reached max_dec at game {n+1}", flush=True)
                break
            if (n + 1) % 400 == 0:
                print(f"  ...{n+1}/{len(games)} games, rows {stats['recorded']}",
                      flush=True)
        flush()
    print(f"\nrows={stats['recorded']}  won={stats['won']} lost={stats['lost']}  "
          f"-> {out} ({os.path.getsize(out)/1e6:.0f}MB)")
    print("skips:", {k: v for k, v in stats.items() if k.startswith('skip')})
    json.dump(dict(stats), open(os.path.join(HERE, "results", f"value_{tag}_stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
