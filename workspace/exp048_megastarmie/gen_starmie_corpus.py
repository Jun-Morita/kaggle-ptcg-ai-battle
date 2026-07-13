"""exp048(a) prep -- convert tomatomato's + taksai's cached ladder replays
(Mega Starmie ex / Mega Froslass ex, IDENTICAL decklist, LB top players) into
the exp041 datagen_bc-format training records, ready for pretrain.py the
moment the GPU frees up. Pure CPU work: reuses exp041's replay_to_records.py
convert_replay() (fixed next-step pairing, verified 2026-07-10) unchanged,
just pooling TWO team names' cached dirs into one corpus instead of one.

Usage: uv run python gen_starmie_corpus.py [out_wid]
  writes data/starmie_w<wid>.pkl (+ stats json) under exp041_pilotnet/data/
  (kept alongside ladder_w9.pkl/expert_w8.pkl so pretrain.py's existing
  path conventions need no changes).
"""
from __future__ import annotations
import json
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
PILOTNET = os.path.join(WS, "exp041_pilotnet")
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
sys.path.insert(0, PILOTNET)

from analyze import card_map  # noqa: E402
from replay_to_records import convert_replay  # noqa: E402  (unchanged, verified pairing)

# team name -> cached replay dirs (references/raw/replays/<dir>), same deck (60/60
# confirmed via /extract-deck: Mega Froslass ex x3 + Mega Starmie ex x3 + Snorunt/
# Staryu x4 + Basic {W} Energy x9 + heavy search suite)
CORPORA = {
    "tomatomato": ["top_tomatomato_0712", "top_tomatomato_0624"],
    "taksai": ["top_taksai_0712"],
}


def main():
    out_wid = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out_pkl = os.path.join(PILOTNET, "data", f"starmie_w{out_wid}.pkl")
    out_json = os.path.join(PILOTNET, "data", f"starmie_w{out_wid}_stats.json")
    os.makedirs(os.path.join(PILOTNET, "data"), exist_ok=True)
    byid = card_map()
    stats = Counter()
    games = Counter()
    chunk = []
    seen_epids = set()
    with open(out_pkl, "wb") as fout:
        for team, dirs in CORPORA.items():
            for tag in dirs:
                raw = os.path.join(ROOT, "references", "raw", "replays", tag)
                if not os.path.isdir(raw):
                    print(f"  !! missing dir {tag}")
                    continue
                files = sorted(f for f in os.listdir(raw) if f.endswith("replay.json"))
                n_before = stats["recorded"]
                for fn in files:
                    try:
                        rep = json.load(open(os.path.join(raw, fn)))
                    except Exception:
                        stats["skip_bad_json"] += 1
                        continue
                    epid = rep.get("info", {}).get("EpisodeId")
                    key = (team, epid)
                    if key in seen_epids:
                        stats["skip_dup_episode"] += 1
                        continue
                    seen_epids.add(key)
                    n0 = stats["recorded"]
                    for rec in convert_replay(rep, byid, stats, team):
                        chunk.append(rec)
                        if len(chunk) >= 20000:
                            pickle.dump(chunk, fout, protocol=4)
                            chunk = []
                    if stats["recorded"] > n0:
                        games[f"{team}/{tag}"] += 1
                print(f"{team}/{tag}: {len(files)} files, +{stats['recorded']-n_before} records", flush=True)
        if chunk:
            pickle.dump(chunk, fout, protocol=4)
    json.dump({"stats": dict(stats), "games": dict(games)}, open(out_json, "w"), indent=1)
    print(f"\n[starmie] total recorded={stats['recorded']} games={sum(games.values())} "
          f"nomatch={stats['skip_nomatch']} obs_convert_fail={stats['skip_obs_convert']}")
    print(f"wrote {out_pkl} ({os.path.getsize(out_pkl)/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
