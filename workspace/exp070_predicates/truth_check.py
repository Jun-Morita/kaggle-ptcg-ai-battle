"""exp070c — GROUND-TRUTH check of the ex-detection predicate on real replays.

The insight this implements (user's): should_wall_mode is gated on a JUDGEMENT
ABOUT THE OPPONENT'S DECK -- `opponent_has_ex_or_ex_line_pressure`. A judgement
has a right answer, so we do not have to settle for win/loss correlation (which
is confounded by reverse causation). Replays record everything the opponent ever
revealed, so we can score the predicate against what they actually were.

The predicate only inspects pokemon currently ON BOARD. Ground truth = any ex
card the opponent revealed at ANY point in the game (active/bench/discard). So:

  FALSE NEGATIVE : opponent demonstrably ran ex, predicate never fired all game.
  LAG            : turns between the opponent first revealing an ex and the
                   predicate first firing. A structurally late proxy is a real
                   misspecification even when it eventually fires.

Scope: koff builds only (v027/v028/v029) -- the shipped pilot.
"""
from __future__ import annotations
import os, sys, json, glob, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine
sys.path.insert(0, HERE)
import probe_predicates as PP

OUR_NAME = "Morita"
KOFF_DIRS = ["0718_54783479", "0718_54797761", "0719_54797761", "0720_54797761"]


def ids_of(seq):
    out = []
    for x in seq or []:
        if x is None:
            continue
        i = getattr(x, "id", None)
        if i is not None:
            out.append(i)
    return out


def main():
    api, _ = load_engine()
    mod = PP.load_koff()
    to_obs = api.to_observation_class
    pred = mod.opponent_has_ex_or_ex_line_pressure
    is_ex = mod.is_ex_card

    files = []
    for d in KOFF_DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                               "episode-*-replay.json")))

    rows = []
    for fp in files:
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        info = d.get("info", {})
        names = info.get("TeamNames") or []
        seats = [i for i, n in enumerate(names) if OUR_NAME in str(n)]
        rewards = d.get("rewards") or []
        for seat in seats:
            if seat >= len(rewards) or rewards[seat] is None or len(rewards) < 2:
                continue
            won = rewards[seat] > rewards[1 - seat]
            first_ex_turn = None      # truth: opponent revealed an ex
            first_fire_turn = None    # predicate said "ex pressure"
            ex_ids = set()
            turns_seen = 0
            for step in d.get("steps", []):
                if seat >= len(step):
                    continue
                ob = (step[seat] or {}).get("observation") or {}
                if not ob.get("current") or ob.get("select") is None:
                    continue
                try:
                    o = to_obs(ob)
                except Exception:
                    continue
                cur = o.current
                if cur is None or cur.yourIndex != seat:
                    continue
                opp = cur.players[1 - seat]
                t = cur.turn
                turns_seen = max(turns_seen, t)

                revealed = ids_of(getattr(opp, "active", [])) + \
                           ids_of(getattr(opp, "bench", [])) + \
                           ids_of(getattr(opp, "discard", []))
                for cid in revealed:
                    if is_ex(cid):
                        ex_ids.add(cid)
                        if first_ex_turn is None:
                            first_ex_turn = t
                try:
                    if pred(opp) and first_fire_turn is None:
                        first_fire_turn = t
                except Exception:
                    pass
            rows.append({"won": won, "first_ex": first_ex_turn,
                         "first_fire": first_fire_turn, "turns": turns_seen,
                         "ex_ids": sorted(ex_ids)})

    n = len(rows)
    truth_ex = [r for r in rows if r["first_ex"] is not None]
    truth_noex = [r for r in rows if r["first_ex"] is None]
    print(f"games: {n}  |  opponent revealed an ex: {len(truth_ex)}  "
          f"|  no ex revealed: {len(truth_noex)}\n")

    fn = [r for r in truth_ex if r["first_fire"] is None]
    fp_ = [r for r in truth_noex if r["first_fire"] is not None]
    print("=== confusion vs ground truth (per game) ===")
    print(f"  opponent HAD ex, predicate fired      : {len(truth_ex)-len(fn):4d}"
          f"  ({100*(len(truth_ex)-len(fn))/max(1,len(truth_ex)):.1f}%)")
    print(f"  opponent HAD ex, predicate NEVER fired: {len(fn):4d}"
          f"  ({100*len(fn)/max(1,len(truth_ex)):.1f}%)   <- FALSE NEGATIVE")
    print(f"  opponent had NO ex, predicate fired   : {len(fp_):4d}"
          f"  ({100*len(fp_)/max(1,len(truth_noex)):.1f}%)   <- FALSE POSITIVE")
    print(f"  opponent had NO ex, never fired       : {len(truth_noex)-len(fp_):4d}")

    lags = [r["first_fire"] - r["first_ex"] for r in truth_ex
            if r["first_fire"] is not None and r["first_ex"] is not None]
    if lags:
        early = sum(1 for x in lags if x < 0)
        same = sum(1 for x in lags if x == 0)
        late = sum(1 for x in lags if x > 0)
        print(f"\n=== detection lag (turns; predicate_fire - ex_revealed) ===")
        print(f"  median {st.median(lags):+.0f}   mean {st.mean(lags):+.2f}   "
              f"fired BEFORE reveal {early}  same turn {same}  AFTER {late}")
        print(f"  distribution: {collections.Counter(sorted(lags)).most_common(8)}")

    print(f"\n=== outcome by ground truth ===")
    for label, sub in (("opponent had ex", truth_ex), ("opponent had no ex", truth_noex)):
        if sub:
            print(f"  {label:22s} n={len(sub):4d}  our wr {sum(r['won'] for r in sub)/len(sub):.3f}")
    if fn:
        print(f"  {'FALSE-NEGATIVE games':22s} n={len(fn):4d}  our wr "
              f"{sum(r['won'] for r in fn)/len(fn):.3f}")
    json.dump(rows, open(os.path.join(HERE, "truth_check.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
