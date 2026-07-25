"""exp081 Track B step 1 -- the anti-Alakazam lever is REAL (mixed_ex2 holds
Alakazam to 0.310 over n=2985 silver-band games; dragapult 0.447). But a counter
is only a silver vehicle if it also holds its OWN vs the rest of the field. So
build the FULL archetype-vs-archetype win matrix in ONE pass over the episode zips
(silver band, both >=900), then for each candidate counter print its whole spread
AND a meta-weighted overall winrate using the stable shares. Pick the best-
positioned archetype, not just the best anti-Alakazam tech.

Usage: uv run python matchup_matrix.py
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
# stable meta shares (7-snapshot avg, n=562) from exp081 reweight
SHARES = {
    "mixed_ex1": 0.233, "mixed_ex4": 0.206, "mixed_ex3": 0.112,
    "non_ex_attackers": 0.109, "lucario_ex": 0.098, "crustle_control": 0.085,
    "dragapult": 0.069, "ex_beatdown": 0.053, "mixed_ex2": 0.020,
    "mixed_ex5": 0.012, "sylveon_control": 0.002,
}


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
    print(f"days={len(zips)}  silver band both>=900\n", flush=True)

    # M[a][b] = [wins_of_a_vs_b, games_a_vs_b]
    M = collections.defaultdict(lambda: collections.defaultdict(lambda: [0, 0]))
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
            if not (scores.get(tn[0], 0) >= 900 and scores.get(tn[1], 0) >= 900):
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
            if rw[0] == rw[1]:
                continue
            w = 0 if rw[0] > rw[1] else 1
            M[arch[w]][arch[1 - w]][0] += 1
            M[arch[w]][arch[1 - w]][1] += 1
            M[arch[1 - w]][arch[w]][1] += 1
        print(f"  scanned {os.path.basename(zp)}", flush=True)

    json.dump({a: {b: v for b, v in row.items()} for a, row in M.items()},
              open(os.path.join(HERE, "matchup_matrix.json"), "w"), indent=1)

    archs = sorted(M.keys(), key=lambda a: -SHARES.get(a, 0))
    # overall meta-weighted winrate for each archetype
    print("=== meta-weighted overall winrate (silver band, stable shares) ===")
    overall = {}
    for a in archs:
        num = den = 0.0
        for b, sh in SHARES.items():
            w, n = M[a].get(b, [0, 0])
            if n == 0:
                continue
            num += (w / n) * sh
            den += sh
        overall[a] = num / den if den else float("nan")
    for a in sorted(overall, key=lambda a: -overall[a]):
        print(f"  {a:22} {overall[a]:.3f}  (share {SHARES.get(a,0):.3f})")

    # full spread for the top anti-Alakazam candidates
    for cand in ["mixed_ex2", "dragapult", "ex_beatdown", "mixed_ex4", "crustle_control"]:
        print(f"\n=== {cand} full spread (silver band) ===")
        row = M[cand]
        for b in sorted(row, key=lambda b: -SHARES.get(b, 0)):
            w, n = row[b]
            if n < 10:
                continue
            print(f"  vs {b:22} {w/n:.3f}  (n={n}, meta {SHARES.get(b,0):.3f})")


if __name__ == "__main__":
    main()
