"""exp081 Track B step 0 -- MEASURE THE LEVER before building an anti-Alakazam
agent. Alakazam (mixed_ex1) is the meta's single largest archetype (~23% stable)
and every build we have goes 0.36-0.46 vs it. Before designing a counter, ask the
data: does ANY archetype beat Alakazam on the real ladder? If some archetype holds
Alakazam < ~0.45, that's the template to adopt (deck + we can scout its pilots). If
nothing beats it, Alakazam is structurally dominant and the anti-Alakazam lever is
dead -- report cheaply and stop.

Computes, across all daily episode zips, Alakazam's WIN RATE vs each opponent
archetype (de-duped by EpisodeId), plus a rating-band filter so we read the
silver-band matchup, not the mu600 lower band.

Usage: uv run python alakazam_predator_scan.py
"""
from __future__ import annotations
import os, sys, json, csv, io, glob, zipfile, collections

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

SCRATCH = "/tmp/claude-1000/-home-jun-kaggle-ptcg-ai-battle/72211639-6cbb-440b-b464-28d9f494ca62/scratchpad"
TARGET = "mixed_ex1"  # Alakazam


def lb_scores():
    with zipfile.ZipFile(os.path.join(SCRATCH, "pokemon-tcg-ai-battle.zip")) as z:
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8-sig")))
    return {r["TeamName"]: float(r["Score"]) for r in rows}


def main():
    load_engine()
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}
    scores = lb_scores()
    zips = sorted(glob.glob(os.path.join(ROOT, "references/raw/episodes_*/*.zip")))
    print(f"days={len(zips)}  target={TARGET} (Alakazam)\n", flush=True)

    # opponent archetype -> [alakazam_wins, alakazam_losses]  (silver band: both >=900)
    wl = collections.defaultdict(lambda: [0, 0])
    wl_all = collections.defaultdict(lambda: [0, 0])
    seen = set()
    for zp in zips:
        z = zipfile.ZipFile(zp)
        for m in z.namelist():
            if not m.endswith(".json"):
                continue
            try:
                ep = json.loads(z.read(m))
            except Exception:
                continue
            inf = ep.get("info") or {}
            epid = inf.get("EpisodeId") or ep.get("id")
            if epid in seen:
                continue
            seen.add(epid)
            tn = inf.get("TeamNames") or []
            rw = ep.get("rewards") or []
            if len(tn) < 2 or len(rw) < 2 or rw[0] is None or rw[1] is None:
                continue
            decks = [None, None]
            for st in ep.get("steps", []):
                for s in (0, 1):
                    if decks[s] is None and s < len(st):
                        a = (st[s] or {}).get("action")
                        if isinstance(a, list) and len(a) == 60:
                            decks[s] = [int(x) for x in a]
                if decks[0] and decks[1]:
                    break
            if not decks[0] or not decks[1]:
                continue
            arch = [A.archetype(decks[0], byid), A.archetype(decks[1], byid)]
            for s in (0, 1):
                if arch[s] != TARGET:
                    continue
                opp = arch[1 - s]
                if opp == TARGET:
                    opp = "mixed_ex1(mirror)"
                won = rw[s] > rw[1 - s]
                lost = rw[s] < rw[1 - s]
                if not (won or lost):
                    continue
                wl_all[opp][0 if won else 1] += 1
                if scores.get(tn[s], 0) >= 900 and scores.get(tn[1 - s], 0) >= 900:
                    wl[opp][0 if won else 1] += 1
        print(f"  scanned {os.path.basename(zp)}", flush=True)

    def report(d, title):
        print(f"\n=== Alakazam WIN RATE by opponent archetype -- {title} ===")
        rows = sorted(d.items(), key=lambda kv: -(kv[1][0] + kv[1][1]))
        print(f"  {'opponent':22} {'AlakWR':>7} {'n':>5}   {'<-- predator if <0.45'}")
        for opp, (w, l) in rows:
            n = w + l
            wr = w / n if n else 0.0
            flag = "  <== ALAKAZAM LOSES" if (n >= 20 and wr < 0.45) else ""
            print(f"  {opp:22} {wr:>7.3f} {n:>5}{flag}")

    report(wl_all, "ALL bands")
    report(wl, "silver band (both >=900)")


if __name__ == "__main__":
    main()
