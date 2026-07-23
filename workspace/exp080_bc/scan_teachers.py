"""exp080 step 1 -- how much TEACHER data does one day of official episodes hold?

Before investing in a multi-day BC project, count the supply. The official daily
dataset (disc709160) is ~4,600 episodes / 21.5GB per day, streamed straight out
of the zip (never extracted).

Episode JSON carries TeamNames but no rating and no submission id, so "is this a
strong player" is resolved by joining team name against the public leaderboard
CSV we already downloaded. A teacher sample = one seat of one episode where:
    - that seat's player is at/above MIN_SCORE on the leaderboard, and
    - that seat played the archetype we want to learn (default: Alakazam), and
    - that seat WON (we imitate winning play, not merely strong players)

Output: counts by archetype x rating band, plus a compact index of the qualifying
(file, seat) pairs so step 2 can convert only those without re-parsing 21.5GB.

Usage: uv run python scan_teachers.py [zip_path] [min_score]
"""
from __future__ import annotations
import os, sys, csv, json, glob, zipfile, collections, io

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
    """team name -> public LB score, from the leaderboard zip we already pulled."""
    zp = os.path.join(SCRATCH, "pokemon-tcg-ai-battle.zip")
    with zipfile.ZipFile(zp) as z:
        name = z.namelist()[0]
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(name), encoding="utf-8-sig")))
    return {r["TeamName"]: float(r["Score"]) for r in rows}


def main():
    zp = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".zip") else \
        glob.glob(os.path.join(ROOT, "references/raw/episodes_*/*.zip"))[0]
    min_score = 1000.0
    for a in sys.argv[1:]:
        if a.replace(".", "").isdigit():
            min_score = float(a)

    load_engine()
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}
    scores = lb_scores()
    print(f"leaderboard names loaded: {len(scores)}")
    print(f"zip: {os.path.basename(zp)}   MIN_SCORE={min_score}\n")

    z = zipfile.ZipFile(zp)
    names = z.namelist()
    arch_all = collections.Counter()
    arch_top = collections.Counter()
    teach = []                     # (member, seat, archetype, score)
    seen = unknown = 0
    for i, member in enumerate(names):
        if not member.endswith(".json"):
            continue
        try:
            d = json.loads(z.read(member))
        except Exception:
            continue
        seen += 1
        inf = d.get("info") or {}
        tn = inf.get("TeamNames") or []
        rw = d.get("rewards") or []
        if len(tn) < 2 or len(rw) < 2 or rw[0] is None or rw[1] is None:
            continue
        decks = [None, None]
        for st in d.get("steps", []):
            for s in (0, 1):
                if decks[s] is None and s < len(st):
                    a = (st[s] or {}).get("action")
                    if isinstance(a, list) and len(a) == 60:
                        decks[s] = [int(x) for x in a]
            if decks[0] is not None and decks[1] is not None:
                break
        for s in (0, 1):
            if decks[s] is None:
                continue
            lab = A.archetype(decks[s], byid)
            arch_all[lab] += 1
            sc = scores.get(tn[s])
            if sc is None:
                unknown += 1
                continue
            won = rw[s] > rw[1 - s]
            if sc >= min_score:
                arch_top[lab] += 1
                if won:
                    teach.append([member, s, lab, sc])
        if (i + 1) % 500 == 0:
            print(f"  ...{i+1}/{len(names)} parsed, teachers so far {len(teach)}", flush=True)

    print(f"\nepisodes parsed: {seen}   seats with unknown team name: {unknown}")
    print(f"\n{'archetype':22}{'all seats':>11}{'>=min_score':>13}")
    for k in sorted(arch_all, key=lambda x: -arch_all[x]):
        print(f"{k:22}{arch_all[k]:11d}{arch_top.get(k,0):13d}")
    print(f"\nTEACHER SAMPLES (>= {min_score}, and WON): {len(teach)}")
    tb = collections.Counter(t[2] for t in teach)
    for k, c in tb.most_common():
        print(f"  {k:22} {c}")
    out = os.path.join(HERE, "teachers_index.json")
    json.dump({"zip": zp, "min_score": min_score, "teachers": teach}, open(out, "w"))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
