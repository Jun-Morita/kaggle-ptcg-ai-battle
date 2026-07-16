"""exp058 -- mirror-focused weight tuning of the v025 pub-alakazam pilot.

WHY: myso1987's team-stratified band meta shows 900-999 (the silver band) is
43.4% Alakazam MIRROR, where v025's live winrate is 0.35. The pilot exposes a
built-in weight-override hook (WEIGHTS dict, read via W[...] at decision time),
so mirror-focused tuning is the designed-in extension path. This is a
continuation of the author's own memetic tuning, but aimed at the mirror.

Method: coordinate screen over mirror-relevant knobs; each arm plays the
CANDIDATE (weights overridden in-place after module load) vs the STOCK pilot,
CRN shared seeds across arms (swap pair shares a seed). Sanity arm: stock vs
stock must be ~0.5.

Usage: uv run python tune_mirror.py [n_per_arm]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp057_pubalakazam"):
    sys.path.insert(0, os.path.join(WS, p))

from harness_crn import load_engine, run_gauntlet  # noqa: E402
load_engine()
from load_pub1034 import AGENT_DIR, pub1034_deck  # noqa: E402

SEED = 20260723
_n = [0]


def make_pub(overrides=None):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pub_t{_n[0]}", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if overrides:
        mod.WEIGHTS.update(overrides)  # W is the same dict object, read at decision time
    deck = pub1034_deck()

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


KNOBS = ["hammer_target", "hammer_any", "xerosic", "cape_alak", "play_bench_penalty",
         "boss_kill", "attack_powerful", "dawn", "mine_counter"]


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    # read defaults
    tmp = importlib.util.spec_from_file_location("pub_defaults", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(tmp)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        tmp.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    defaults = {k: mod.WEIGHTS[k] for k in KNOBS}
    print("defaults:", defaults, flush=True)

    arms = [("STOCK(sanity)", None)]
    for k in KNOBS:
        v = defaults[k]
        arms.append((f"{k}=0", {k: 0}))
        arms.append((f"{k}x2", {k: v * 2}))

    results = {}
    for label, ov in arms:
        st = run_gauntlet(make_pub(ov), make_pub(None), n_games=n, swap_sides=True,
                          crn_seed_base=SEED)
        results[label] = st.winrate0
        print(f"  {label:24} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1})", flush=True)
    json.dump(results, open(os.path.join(HERE, f"mirror_screen_n{n}.json"), "w"), indent=1)
    best = sorted(results.items(), key=lambda kv: -kv[1])[:5]
    print("\ntop arms:", best)


if __name__ == "__main__":
    main()
