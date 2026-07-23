"""exp073 — does our local pool PREDICT our real ladder results?

Motivation: under the V3 weights, pure_wall is 37.5% of all our modelled losses
and fixing it would be worth +0.060 (4.6x what v030 gained). Before spending any
effort there, check whether the pool's 0.205 is even real:

  - our pool's pure_wall opponent is a KNOWN-BROKEN reproduction: it holds
    4x Mega Kangaskhan ex and never puts one on board (found in exp070 stage 1)
  - meta_watch on v029 (147 real games) shows crustle_control at 6-6-0 = 0.50,
    which is nothing like 0.205

If the pool systematically mispredicts, every band-weighted number we compute --
including the adoption bar and every gate verdict -- inherits that error. This is
the same class of finding as the V2/V3 share calibration and the CRN bug, and it
has been the highest-yield lane we have.

Method: over the koff-build ladder replays, compute our real winrate per opponent
archetype (as meta_watch labels them), then line those up against the pool's
predicted winrate for the corresponding pool opponent. Report the gaps.

Caveat stated up front: archetype labels are coarse and real opponents are a MIX
of pilots, whereas each pool slot is ONE deck + ONE pilot. So this measures
"does the pool predict the field", not "is this specific proxy faithful".
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

# meta_watch archetype label -> our pool slot(s)
LABEL_TO_POOL = {
    "crustle_control": ["pure_wall", "crustle_LO"],
    "non_ex_attackers": ["alakazam_dun"],
    "mixed_ex1": ["alakazam"],
    "mixed_ex4": ["archaludon"],
    "mixed_ex3": ["marnie"],
    "dragapult": ["dragapult"],
    "lucario_ex": ["lucario_ex"],
}


def main():
    snaps = sorted(glob.glob(os.path.join(WS, "exp011_meta_watch", "results", "meta_*.json")))
    # koff-era submissions only
    KOFF_SUBS = {"54783479", "54794345", "54797761", "54878432"}
    agg = collections.defaultdict(lambda: [0, 0])   # label -> [wins, games]
    used = []
    for p in snaps:
        sub = os.path.basename(p).replace(".json", "").split("_")[-1]
        if sub not in KOFF_SUBS:
            continue
        try:
            d = json.load(open(p))
        except Exception:
            continue
        by = d.get("by_arch") or {}
        if not by:
            continue
        used.append(os.path.basename(p))
        for label, rec in by.items():
            if isinstance(rec, dict):
                w = rec.get("w", rec.get("wins", 0))
                l = rec.get("l", rec.get("losses", 0))
                dr = rec.get("d", rec.get("draws", 0))
            elif isinstance(rec, (list, tuple)) and len(rec) >= 2:
                w, l, dr = rec[0], rec[1], (rec[2] if len(rec) > 2 else 0)
            else:
                continue
            agg[label][0] += w
            agg[label][1] += w + l + dr
    print("snapshots used:", used or "(none -- check json shape)")
    if not agg:
        # fall back: show the raw shape so we can fix the parser
        for p in snaps[-1:]:
            print("sample keys:", list(json.load(open(p)).keys()))
        return

    k = json.load(open(os.path.join(WS, "exp070_predicates", "nodun600.json")))
    pool = {x: v["no_dun"] for x, v in k.items()}
    W = EB.SILVER_BAND

    print(f"\n{'archetype':20s}{'real W-N':>12}{'real wr':>9}{'pool wr':>9}{'gap':>8}   pool slot")
    tot_real_w = tot_real_n = 0
    for label, (w, n) in sorted(agg.items(), key=lambda x: -x[1][1]):
        if n == 0:
            continue
        tot_real_w += w
        tot_real_n += n
        slots = LABEL_TO_POOL.get(label)
        if not slots:
            print(f"{label:20s}{f'{w}-{n}':>12}{w/n:9.3f}{'--':>9}{'--':>8}   (not modelled)")
            continue
        # weight-blend the pool slots
        sw = sum(W[s] for s in slots)
        pw = sum(W[s] * pool[s] for s in slots) / sw
        print(f"{label:20s}{f'{w}-{n}':>12}{w/n:9.3f}{pw:9.3f}{w/n-pw:+8.3f}   {'+'.join(slots)}")
    print(f"\noverall real ladder winrate: {tot_real_w}/{tot_real_n} = {tot_real_w/max(1,tot_real_n):.3f}")
    band = sum(W[o] * pool[o] for o in W) / sum(W.values())
    print(f"pool band-weighted prediction: {band:.4f}")
    print("\nNOTE: the pool is scored on a FIXED band mix; the real field mix differs,")
    print("so compare per-archetype gaps, not the two aggregates directly.")


if __name__ == "__main__":
    main()
