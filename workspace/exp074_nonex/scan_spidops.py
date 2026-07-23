"""exp074 / H12 -- have we been losing to Team Rocket's Spidops without noticing?

Why: our whole defence is Crustle（イワパレス）Safeguard + Neutralization Zone,
which only blanks ex attacks. references/knowledge/disc_code_sweep_0714.md and
engine_update_0718.md both flag Team Rocket's Spidops as "the killer of every
Safeguard deck", and pilkwang measured its share going 1.4% -> 12.3%. Our pool
does not model it at all, so if it is really that common we are eating a hole
that no local number can see.

Scope note: the replay corpus is 12,075 files / 45GB, and loading all of it times
out, so this scans only the recent koff-era directories -- which is also the meta
we actually care about. Our own games only reveal opponents WE faced, so a low
count here is weak evidence about the band as a whole, not proof of absence.

Usage: uv run python scan_spidops.py [dir ...]
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

DIRS = ["0717_54768702", "0718_54783479", "0718_54797761",
        "0719_54797761", "0720_54797761", "0721_54878432"]


def main():
    load_engine()
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}
    spid = {c.cardId for c in all_card_data() if "Spidops" in c.name}
    tr = {c.cardId for c in all_card_data() if c.name.startswith("Team Rocket's")}
    print(f"Spidops cardIds: {sorted(spid)}   Team Rocket cards: {len(tr)}")

    # NOTE: we append "--crn" to sys.argv above, so filter flags BEFORE the
    # `or DIRS` fallback -- doing it after silently yields an empty dir list.
    dirs = [d for d in sys.argv[1:] if not d.startswith("-")] or DIRS
    rec = collections.defaultdict(lambda: [0, 0])
    n_tr = [0, 0]
    seen = 0
    for d in dirs:
        for fp in sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                                "episode-*-replay.json"))):
            try:
                rep = json.load(open(fp))
            except Exception:
                continue
            names = (rep.get("info") or {}).get("TeamNames") or []
            seats = [i for i, x in enumerate(names) if "Morita" in str(x)]
            rw = rep.get("rewards") or []
            if len(seats) != 1 or len(rw) < 2:
                continue
            s = seats[0]
            if rw[s] is None or rw[1 - s] is None:
                continue
            od = None
            for step in rep.get("steps", []):
                if 1 - s < len(step):
                    a = (step[1 - s] or {}).get("action")
                    if isinstance(a, list) and len(a) == 60:
                        od = [int(x) for x in a]
                        break
            if od is None:
                continue
            seen += 1
            won = 1 if rw[s] > rw[1 - s] else 0
            if tr & set(od):
                n_tr[0] += won
                n_tr[1] += 1
            if spid & set(od):
                key = tuple(sorted(collections.Counter(od).items()))
                rec[key][0] += won
                rec[key][1] += 1

    print(f"\nour games scanned: {seen}  (dirs: {', '.join(dirs)})")
    print(f"vs ANY Team Rocket deck: {n_tr[0]}-{n_tr[1]}"
          + (f"  wr={n_tr[0]/n_tr[1]:.3f}  share={n_tr[1]/max(1,seen):.1%}" if n_tr[1] else ""))
    tw = sum(v[0] for v in rec.values())
    tn = sum(v[1] for v in rec.values())
    print(f"vs a SPIDOPS deck:       {tw}-{tn}"
          + (f"  wr={tw/tn:.3f}  share={tn/max(1,seen):.1%}" if tn else "  (never faced)"))
    if not tn:
        print("\nNo Spidops in our own recent games. That is weak evidence -- we only\n"
              "see who the matchmaker paired us with. Check a top player's replays\n"
              "(top_meta.py) before concluding the archetype is absent from the band.")
        return
    key, (w, n) = max(rec.items(), key=lambda kv: kv[1][1])
    print(f"\nmost-played Spidops list ({w}-{n}):")
    deck = []
    for cid, k in sorted(dict(key).items(), key=lambda x: -x[1]):
        print(f"  x{k}  {byid[cid].name if cid in byid else cid}")
        deck += [cid] * k
    json.dump(deck, open(os.path.join(HERE, "real_spidops_deck.json"), "w"))
    print("-> real_spidops_deck.json")


if __name__ == "__main__":
    main()
