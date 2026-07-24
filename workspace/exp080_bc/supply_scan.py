"""exp080 Front-2(all-band BC) step 0 -- how many LOWER-band Grimmsnarl WINNING
games does the official dataset actually hold? The daily top-episodes zips are
~99% >=1000-rated (measured), so before deciding between the cheap path (lower
the min_score threshold and re-scan the zips) and the expensive path (pull
lower-rated ladder replays), count the real supply by rating band AND by opponent
archetype (we specifically need Grimmsnarl-vs-lower-band-meta wins, e.g. vs
Archaludon, which the climb needs and the >=1000 corpus lacks).

Usage: uv run python supply_scan.py
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


def lb_scores():
    with zipfile.ZipFile(os.path.join(SCRATCH, "pokemon-tcg-ai-battle.zip")) as z:
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8-sig")))
    return {r["TeamName"]: float(r["Score"]) for r in rows}


def band(sc):
    if sc is None:
        return "unknown"
    return ">=1000" if sc >= 1000 else ("900-1000" if sc >= 900 else
           ("800-900" if sc >= 800 else ("700-800" if sc >= 700 else "<700")))


def main():
    load_engine()
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}
    scores = lb_scores()
    zips = sorted(glob.glob(os.path.join(ROOT, "references/raw/episodes_*/*.zip")))
    print(f"days={len(zips)}  leaderboard names={len(scores)}\n", flush=True)

    band_wins = collections.Counter()          # winning Grimmsnarl seats by band
    band_opp = collections.defaultdict(collections.Counter)
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
            for s in (0, 1):
                if A.archetype(decks[s], byid) != "mixed_ex3":
                    continue
                if not (rw[s] > rw[1 - s]):
                    continue
                b = band(scores.get(tn[s]))
                band_wins[b] += 1
                band_opp[b][A.archetype(decks[1 - s], byid)] += 1
        print(f"  scanned {os.path.basename(zp)}  cum wins so far {sum(band_wins.values())}", flush=True)

    print("\nGrimmsnarl WINNING seats by rating band (10 days, de-duped):")
    order = [">=1000", "900-1000", "800-900", "700-800", "<700", "unknown"]
    for b in order:
        n = band_wins.get(b, 0)
        arch = band_opp[b].get("mixed_ex4", 0)
        luc = band_opp[b].get("lucario_ex", 0)
        print(f"  {b:9} wins={n:5}  vs-Archaludon={arch:4}  vs-lucario_ex={luc:4}  "
              f"top-opps={band_opp[b].most_common(4)}")
    below = sum(band_wins.get(b, 0) for b in ["900-1000", "800-900", "700-800", "<700"])
    below_arch = sum(band_opp[b].get("mixed_ex4", 0) for b in ["900-1000", "800-900", "700-800", "<700"])
    print(f"\nTOTAL <1000 Grimmsnarl wins = {below}  (of which vs-Archaludon = {below_arch})")
    print(f"vs the >=1000 supply = {band_wins.get('>=1000',0)}")


if __name__ == "__main__":
    main()
