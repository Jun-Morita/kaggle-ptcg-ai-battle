"""exp074 stage 2 -- per-LIST records inside the non_ex_attackers bucket.

Stage 1 result (background job bl3neba3x): swapping the pool's synthetic deck for
the REAL most-common non-ex list moved our winrate 0.847 -> 0.820 (RVP pilot) and
only 0.610 with the strongest pilot we own. Real ladder is 0.259. So NEITHER the
deck NOR any pilot we have explains a 0.351 residual gap.

Before concluding "their pilots are simply 0.35 better than anything we own",
check the cheaper explanation: the bucket is not one deck. The stage-1 autopsy
showed 8 distinct exact lists with wildly different records (one 6-game list went
0-6 against us, one 4-game list went 4-0 for us). If the losses concentrate in ONE
list that is structurally different from the one we picked, then we calibrated the
pool against the list we BEAT and the residual is a deck-selection artifact, not a
pilot gap.

Output: per-list W-L, and the full 60-card list of whichever list beats us most,
written to real_nonex_worst.json for use as the pool opponent.
"""
from __future__ import annotations
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

OUR = "Morita"
KOFF_DIRS = ["0718_54783479", "0718_54797761", "0719_54797761", "0720_54797761"]


def main():
    load_engine()
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}

    files = []
    for d in KOFF_DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                               "episode-*-replay.json")))

    rec = collections.defaultdict(lambda: [0, 0])   # deck key -> [wins, games]
    raw = {}
    for fp in files:
        try:
            rep = json.load(open(fp))
        except Exception:
            continue
        names = (rep.get("info") or {}).get("TeamNames") or []
        seats = [i for i, n in enumerate(names) if OUR in str(n)]
        rewards = rep.get("rewards") or []
        if len(seats) != 1 or len(rewards) < 2:
            continue
        seat = seats[0]
        if rewards[seat] is None or rewards[1 - seat] is None:
            continue
        opp_deck = None
        for step in rep.get("steps", []):
            if 1 - seat < len(step):
                a = (step[1 - seat] or {}).get("action")
                if isinstance(a, list) and len(a) == 60:
                    opp_deck = [int(x) for x in a]
                    break
        if opp_deck is None or A.archetype(opp_deck, byid) != "non_ex_attackers":
            continue
        key = tuple(sorted(collections.Counter(opp_deck).items()))
        raw[key] = opp_deck
        rec[key][0] += 1 if rewards[seat] > rewards[1 - seat] else 0
        rec[key][1] += 1

    print(f"{'W-N':>8}{'wr':>8}   list (top cards)")
    order = sorted(rec.items(), key=lambda kv: (kv[1][0] / kv[1][1], -kv[1][1]))
    for key, (w, n) in order:
        cnt = dict(key)
        top = sorted(cnt.items(), key=lambda x: -x[1])[:7]
        nm = ", ".join(f"{byid[c].name if c in byid else c}x{k}" for c, k in top)
        print(f"{f'{w}-{n}':>8}{w/n:8.3f}   {nm}")

    tot_w = sum(v[0] for v in rec.values())
    tot_n = sum(v[1] for v in rec.values())
    print(f"\ntotal {tot_w}-{tot_n} = {tot_w/tot_n:.3f}")

    # the list that beats us most (ties broken by sample size)
    worst = min(rec.items(), key=lambda kv: (kv[1][0] / kv[1][1], -kv[1][1]))
    w, n = rec[worst[0]]
    print(f"\nWORST-FOR-US list: {w}-{n} (wr {w/n:.3f}), n={n} games")
    print("full list:")
    for cid, k in sorted(dict(worst[0]).items(), key=lambda x: -x[1]):
        print(f"  x{k}  {byid[cid].name if cid in byid else cid}")
    json.dump(raw[worst[0]], open(os.path.join(HERE, "real_nonex_worst.json"), "w"))
    print(f"\n-> {os.path.join(HERE, 'real_nonex_worst.json')}")

    # how much of our total non-ex loss mass does this one list carry?
    losses = {k: v[1] - v[0] for k, v in rec.items()}
    tl = sum(losses.values())
    print(f"\nloss concentration: this list = {losses[worst[0]]}/{tl} "
          f"= {losses[worst[0]]/max(1,tl):.1%} of non-ex losses")


if __name__ == "__main__":
    main()
