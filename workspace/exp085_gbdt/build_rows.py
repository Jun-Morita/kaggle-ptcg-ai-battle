"""Turn teacher seats into per-option ranking rows.

Same streaming as exp080/build_records.py (random-access out of the daily zip,
teacher seats from teachers_index.json, obs at step t answered by the action at
step t+1) -- only the featuriser differs. Where build_records emitted the
transformer's sparse encoder/decoder words, this emits one dense feats.py row per
LEGAL OPTION plus a 0/1 label saying whether the teacher took it.

Labelling note: for a multi-select decision (maxCount > 1) the teacher's action is
a SET of indices, and every member gets label 1. That is deliberate -- the ranker
is scored by "are the teacher's picks the top-k", which is exactly how the agent
will consume it, rather than by a single-label softmax that cannot express a set.

Groups: rows are tagged with the SelectContext so train_gbdt.py can fit one model
per context family. We do NOT hardcode a routing table here; the split is chosen
from observed counts after this runs, so it reflects our corpus and not somebody
else's.

Usage: uv run python build_rows.py [archetype] [--max-dec N] [--out tag]
Writes results/rows_<tag>.npz-style pickle chunks: (ctx, qid, y, X float32).
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

import feats  # noqa: E402  (loads the engine)
import numpy as np  # noqa: E402
import train_mcts as tm  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from analyze import card_map, archetype  # noqa: E402


# The OPPONENT's archetype rides along with every row. It was computed and
# thrown away until now (`_mu`), and it is the one thing that lets the training
# distribution be matched to the field we actually face: the corpus is dominated
# by late-July games, when 63% of the ladder played our own deck, while on 08-12
# the field was dragapult 25.8% / ex_beatdown 20.6% / mixed_ex3 14.1%. Reweighting
# by this column is not more data -- it is different data.
ARCH_CODE = {"mixed_ex3": 1, "mixed_ex1": 2, "mixed_ex4": 3, "dragapult": 4,
             "ex_beatdown": 5, "crustle_control": 6, "lucario_ex": 7,
             "non_ex_attackers": 8, "mixed_ex2": 9}
ARCH_NAME = {v: k for k, v in ARCH_CODE.items()}


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


def convert_seat(ep, ti, byid, stats, qid0, exact=None, score=None, near=None):
    """Yield (ctx, qid, y[list], X[list of rows], mu) for one teacher seat.

    `exact`: if given, the teacher's 60 cards must match this list exactly.

    This filter is the difference between v2 and v3, and it is worth the comment.
    The archetype label ("mixed_ex3" = Grimmsnarl) is a fuzzy classifier over the
    decklist, not our decklist. Counting exact matches per day shows our 60-card
    list simply did not exist in the meta before 2026-07-17:

        07-01..07-16   0.00-0.14 of Grimmsnarl teachers ran our exact list
        07-17..07-28   0.33-0.73

    v2 drew 400k decisions from 07-01..07-11 and so learned, faithfully, how to
    pilot somebody else's deck: held-out top-k rose 0.684 -> 0.798 while the
    head-to-head against our own shipped build fell 0.510 -> 0.315. Fidelity to
    the wrong teacher is worse than less data.

    The same construction was used for the transformer's 28-day corpus (exp083k),
    which cost ~70 ladder points that no local gate could see -- most likely the
    same contamination.
    """
    # the row records who produced it, as a rank inside that day's own field --
    # see feats.TEACHER_PCT for why this is a percentile and not the raw score
    feats.TEACHER_PCT = 1.0 if score is None else float(score)
    decks = decks_from_ep(ep)
    if not decks.get(ti) or not decks.get(1 - ti):
        stats["skip_no_deck"] += 1
        return
    if exact is not None:
        mine = sorted(decks[ti])
        if near is None:
            ok = mine == exact
        else:
            # multiset overlap. The near misses are not random: 10 distinct lists
            # cover 802 of the 4,800 seats sampled, and they are our list minus
            # Tool Scrapper / Pokegear 3.0 plus Handheld Fan / Judge. Two cards of
            # difference does not change the lines the model is learning, whereas
            # the 18/60 cluster below is a different deck entirely and is exactly
            # what poisoned the v2 corpus.
            a, b = Counter(mine), Counter(exact)
            ok = sum((a & b).values()) >= near
        if not ok:
            stats["skip_deck_mismatch"] += 1
            return
    rewards = ep.get("rewards") or [None, None]
    r = rewards[ti] if ti < len(rewards) else None
    if r != 1:                      # teacher seats are winners; keep it that way
        stats["skip_not_won"] += 1
        return
    mu = archetype(decks[1 - ti], byid)
    steps = ep.get("steps", [])
    history = []
    qid = qid0
    for si, st in enumerate(steps):
        if ti >= len(st):
            continue
        ag = st[ti]
        if ag.get("status") != "ACTIVE":
            continue
        obs = ag.get("observation")
        if si + 1 >= len(steps) or ti >= len(steps[si + 1]):
            continue
        act = steps[si + 1][ti].get("action")
        if not isinstance(obs, dict) or obs.get("select") is None \
                or not isinstance(act, list) or len(act) == 60:
            continue
        try:
            oc = to_observation_class(obs)
        except Exception:
            stats["skip_obs"] += 1
            continue
        if oc.select is None or not oc.select.option:
            continue
        n_opt = len(oc.select.option)
        chosen = sorted(int(i) for i in act if isinstance(i, int) and 0 <= i < n_opt)
        if len(chosen) != len(act):
            stats["skip_bad_action"] += 1
            continue
        try:
            rows, sems = feats.option_rows(oc, history)
        except Exception:
            stats["skip_feat"] += 1
            continue
        # advance history with what the teacher actually did. Entries carry the
        # turn so feats can separate "this turn" from "three decisions ago"; the
        # window has to outlive 3 now, since a turn can run a dozen actions.
        for i in chosen:
            history.append((oc.current.turn, sems[i]))
        history = history[-40:]
        if n_opt < 2:
            stats["skip_forced"] += 1     # nothing to rank
            continue
        y = [0] * n_opt
        for i in chosen:
            y[i] = 1
        ctx = int(getattr(oc.select, "context", -1) or -1)
        stats["recorded"] += 1
        stats[f"ctx_{ctx}"] += 1
        yield ctx, qid, y, rows, mu, score
        qid += 1


def main():
    target = arg("--arch", "mixed_ex3")
    max_dec = int(arg("--max-dec", "300000"))
    tag = arg("--out", target)
    # One index per daily zip (scan_all_days.sh). Days are interleaved rather than
    # concatenated so that a --max-dec cap still samples the whole month instead of
    # stopping inside July 1st -- the meta rotates, and a corpus that is all one
    # week is how v046 specialised into the mirror and lost 146 ladder points.
    ipat = arg("--index", os.path.join(HERE, "indices", "*.json"))
    ipaths = sorted(glob.glob(ipat)) if any(c in ipat for c in "*?") else [ipat]
    if not ipaths:
        raise SystemExit(f"no teacher index matched {ipat}")
    days = []
    for p in ipaths:
        d = json.load(open(p))
        # Rank every teacher against THAT DAY's field, not against a fixed number.
        # The ladder's score level fell through August (the top of 08-08 sits where
        # the middle of 07-26 was), so an absolute threshold silently selects by
        # date. A within-day percentile does not.
        allsc = sorted(float(sc) for (_m, _s, _a, sc) in d["teachers"] if sc)
        n = len(allsc)

        def pct(sc):
            if not sc or n < 2:
                return 1.0
            lo, hi = 0, n
            while lo < hi:                      # bisect_left, stdlib-free
                mid = (lo + hi) // 2
                if allsc[mid] < float(sc):
                    lo = mid + 1
                else:
                    hi = mid
            return lo / (n - 1)

        s = [(d["zip"], m, seat, pct(sc)) for (m, seat, a, sc) in d["teachers"]
             if a == target]
        if s:
            days.append(s)
    seats = [x for grp in zip_longest(*days) for x in grp if x is not None]
    print(f"target={target} days={len(days)} teacher seats={len(seats)} "
          f"max_dec={max_dec}", flush=True)

    # --deck points the exact-match filter AND the featuriser at another list.
    # feats.set_deck rebuilds the per-card columns and re-resolves the card roles
    # (gust / ACE SPEC / biggest ex / main Energy), so the row width follows the
    # deck -- 360 columns for Grimmsnarl (オーロンゲ), 366 for the Mega Lopunny ex
    # (メガミミロップex) list, which has 21 distinct cards instead of 19.
    deck_path = arg("--deck", os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))
    exact = None
    if "--exact-deck" in sys.argv:
        exact = sorted(json.load(open(deck_path)))
        feats.set_deck(exact)
        print(f"  exact-deck filter ON: {os.path.basename(deck_path)}, "
              f"{len(feats.DECK_IDS)} distinct cards, "
              f"{feats.N_FEATURES} features", flush=True)

    # --near N accepts a teacher whose list shares >= N of our 60 cards
    near = int(arg("--near")) if "--near" in sys.argv else None
    if near:
        print(f"  near-deck filter: overlap >= {near}/60", flush=True)

    byid = card_map()
    zips = {}
    stats = Counter()
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    out = os.path.join(HERE, "results", f"rows_{tag}.pkl")
    CTX, QID, Y, X, SC, MU = [], [], [], [], [], []
    qid = 0
    with open(out, "wb") as fout:
        def flush():
            if not X:
                return
            pickle.dump((np.array(CTX, np.int16), np.array(QID, np.int32),
                         np.array(Y, np.int8), np.asarray(X, np.float32),
                         np.array(SC, np.float32), np.array(MU, np.int8)),
                        fout, protocol=4)
            CTX.clear(); QID.clear(); Y.clear(); X.clear(); SC.clear(); MU.clear()

        for n, (zp, member, seat, tscore) in enumerate(seats):
            try:
                z = zips.get(zp) or zips.setdefault(zp, zipfile.ZipFile(zp))
                ep = json.loads(z.read(member))
            except Exception:
                stats["skip_json"] += 1
                continue
            for ctx, q, y, rows, mu, sc in convert_seat(
                    ep, seat, byid, stats, qid, exact, tscore, near):
                qid = q + 1
                for yy, rr in zip(y, rows):
                    CTX.append(ctx); QID.append(q); Y.append(yy); X.append(rr)
                    SC.append(sc if sc is not None else 0.0)
                    MU.append(ARCH_CODE.get(mu, 0))
                if len(X) >= 400000:
                    flush()
            if stats["recorded"] >= max_dec:
                print(f"  reached max_dec at episode {n+1}", flush=True)
                break
            if (n + 1) % 200 == 0:
                print(f"  ...{n+1}/{len(seats)} eps, decisions {stats['recorded']}",
                      flush=True)
        flush()

    top = sorted(((int(k[4:]), v) for k, v in stats.items() if k.startswith("ctx_")),
                 key=lambda x: -x[1])
    print(f"\ndecisions={stats['recorded']}  rows written -> {out} "
          f"({os.path.getsize(out)/1e6:.0f}MB)")
    print("skips:", {k: v for k, v in stats.items() if k.startswith("skip")})
    print("context counts:", top[:24])
    json.dump({"target": target, "stats": dict(stats), "ctx": top},
              open(os.path.join(HERE, "results", f"rows_{tag}_stats.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
