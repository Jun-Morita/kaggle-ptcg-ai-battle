"""Fetch ALL available replays for our v012-v014-lineage submissions into
references/raw/replays/ladder_<sub>/ (skips files already cached anywhere in
the existing per-day dirs to avoid re-downloading).

Usage: uv run python fetch_ladder_replays.py
"""
from __future__ import annotations
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REPLAYS = os.path.join(ROOT, "references", "raw", "replays")

SUBS = {
    54213076: "ladder_v012",
    54269701: "ladder_v013",
    54315009: "ladder_v014",
    54496255: "ladder_v014clone",   # diag-probe: byte-identical v014 main.py
}
# dirs whose episodes are already on disk (extractor reads these too)
EXISTING = ["0704_54269701", "0705_54315009", "0707_54315009"]


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    have = set()
    for d in EXISTING + list(SUBS.values()):
        p = os.path.join(REPLAYS, d)
        if os.path.isdir(p):
            have |= {f for f in os.listdir(p) if f.endswith("replay.json")}
    total_new = 0
    for sid, tag in SUBS.items():
        out = os.path.join(REPLAYS, tag)
        os.makedirs(out, exist_ok=True)
        eps = api.competition_list_episodes(sid)
        new = 0
        for e in eps:
            fn = f"episode-{e.id}-replay.json"
            if fn in have:
                continue
            try:
                api.competition_episode_replay(e.id, path=out)
                have.add(fn)
                new += 1
                time.sleep(0.2)
            except Exception as ex:
                print(f"  skip {e.id}: {ex}")
        total_new += new
        print(f"{tag} (sub {sid}): {len(eps)} episodes, downloaded {new} new", flush=True)
    print(f"DONE total_new={total_new}")


if __name__ == "__main__":
    main()
