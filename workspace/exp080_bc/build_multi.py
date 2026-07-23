"""exp080 step 2b -- multi-day teacher record builder. Merges scan + convert in
one pass over several daily episode zips, so adding days is one flag. Motivation:
the 1-day net had a real Alakazam-defense gap (0.12 vs pub1034-Alakazam; real top
Grimmsnarl is 0.52 there), consistent with too few Alakazam-opponent examples.
More days -> more mixed_ex1-opponent trajectories to imitate.

A teacher seat = a seat whose player is >=MIN_SCORE on the CURRENT leaderboard
(proxy for "was strong"), played the target archetype, and WON. Same definition
as scan_teachers.py; here we convert on the fly instead of writing an index first.

Usage: uv run python build_multi.py [archetype] [min_score]
  scans every references/raw/episodes_*/**.zip. Writes data/<archetype>_multi_w7.pkl.
"""
from __future__ import annotations
import os, sys, json, csv, io, glob, zipfile, pickle
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

import train_mcts as tm  # noqa: E402
from analyze import card_map, archetype  # noqa: E402
import build_records as BR  # noqa: E402  (convert_seat + decks_from_ep, WID)

SCRATCH = "/tmp/claude-1000/-home-jun-kaggle-ptcg-ai-battle/72211639-6cbb-440b-b464-28d9f494ca62/scratchpad"


def lb_scores():
    zp = os.path.join(SCRATCH, "pokemon-tcg-ai-battle.zip")
    with zipfile.ZipFile(zp) as z:
        rows = list(csv.DictReader(io.TextIOWrapper(z.open(z.namelist()[0]), encoding="utf-8-sig")))
    return {r["TeamName"]: float(r["Score"]) for r in rows}


def main():
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].replace(".", "").isdigit() else "mixed_ex3"
    min_score = next((float(a) for a in sys.argv[1:] if a.replace(".", "").isdigit()), 1000.0)

    zips = sorted(glob.glob(os.path.join(ROOT, "references/raw/episodes_*/*.zip")))
    scores = lb_scores()
    byid = card_map()
    print(f"target={target}  min_score={min_score}  days={len(zips)}", flush=True)
    for z in zips:
        print("  ", os.path.basename(z), flush=True)

    stats = Counter()
    chunk, games, seen = [], 0, set()
    out_pkl = os.path.join(HERE, "data", f"{target}_multi_w{BR.WID}.pkl")
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(out_pkl, "wb") as fout:
        for zp in zips:
            z = zipfile.ZipFile(zp)
            day_g = 0
            for member in z.namelist():
                if not member.endswith(".json"):
                    continue
                try:
                    ep = json.loads(z.read(member))
                except Exception:
                    stats["skip_bad_json"] += 1
                    continue
                inf = ep.get("info") or {}
                epid = inf.get("EpisodeId") or ep.get("id")
                if epid in seen:            # de-dup across overlapping days
                    stats["skip_dup"] += 1
                    continue
                seen.add(epid)
                tn = inf.get("TeamNames") or []
                rw = ep.get("rewards") or []
                if len(tn) < 2 or len(rw) < 2 or rw[0] is None or rw[1] is None:
                    continue
                decks = BR.decks_from_ep(ep)
                for s in (0, 1):
                    if decks.get(s) is None:
                        continue
                    if archetype(decks[s], byid) != target:
                        continue
                    if scores.get(tn[s], 0.0) < min_score:
                        continue
                    if not (rw[s] > rw[1 - s]):   # WON only
                        continue
                    n0 = stats["recorded"]
                    for rec in BR.convert_seat(ep, s, byid, stats):
                        chunk.append(rec)
                        if len(chunk) >= 20000:
                            pickle.dump(chunk, fout, protocol=4)
                            chunk = []
                    if stats["recorded"] > n0:
                        games += 1
                        day_g += 1
            print(f"  {os.path.basename(zp)}: teacher games {day_g}, cum recorded {stats['recorded']}", flush=True)
        if chunk:
            pickle.dump(chunk, fout, protocol=4)

    out_json = os.path.join(HERE, "data", f"{target}_multi_w{BR.WID}_stats.json")
    json.dump({"stats": dict(stats), "games": games, "days": len(zips), "target": target},
              open(out_json, "w"), indent=1)
    print(f"\n[{target}] recorded={stats['recorded']} from games={games} over {len(zips)} days")
    print("opp mix:", sorted(((k[3:], v) for k, v in stats.items() if k.startswith('mu_')), key=lambda x: -x[1]))
    print(f"wrote {out_pkl} ({os.path.getsize(out_pkl)/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
