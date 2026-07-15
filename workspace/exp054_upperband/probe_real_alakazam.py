"""exp054-E -- reproduce v023's LIVE alakazam number (0.48, n=23) locally.

4-cell matrix: {old proxy list, real silver list} x {generic RVP pilot,
public dedicated 5th-place pilot}. Which cell explains live 0.48 vs local 0.84?
Usage: uv run python probe_real_alakazam.py [n]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp023_revenge", "exp016_pubnb",
          "exp053_bandpool", "exp054_upperband"):
    sys.path.insert(0, os.path.join(WS, p))

from harness_crn import load_engine, run_gauntlet  # noqa: E402
load_engine()
import revenge_policy as RVP  # noqa: E402
from load_alakazam import make_alakazam_agent, alakazam_deck, ALAKAZAM_DIR  # noqa: E402
from load_lo import lo_deck  # noqa: E402

SEED = 20260721
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
_n = [0]


def make_koff(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_e{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.should_ko_mode = lambda *a, **k: False

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def make_pub_alakazam(deck):
    base = make_alakazam_agent()

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return base(obs)
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    old_list = json.load(open(os.path.join(WS, "exp053_bandpool", "band_mixed_ex1.json")))
    real_list = json.load(open(os.path.join(HERE, "real_silver_alakazam.json")))
    pub_own = alakazam_deck()
    ov = sum((Counter(real_list) & Counter(pub_own)).values())
    print(f"real silver list vs public notebook's own deck: {ov}/60 overlap")
    cells = [
        ("old_list + RVP     (current pool)", old_list, lambda d: RVP.make_agent(d)),
        ("real_list + RVP    (list effect)", real_list, lambda d: RVP.make_agent(d)),
        ("pub_own + PUBpilot (pilot effect)", pub_own, lambda d: make_pub_alakazam(d)),
        ("real_list + PUBpilot (closest)", real_list, lambda d: make_pub_alakazam(d)),
    ]
    print(f"v023-koff vs alakazam cells, n={n}, CRN shared seeds  (live reference: 0.48)")
    for label, deck, fac in cells:
        st = run_gauntlet(make_koff(lo_deck()), fac(list(deck)), n_games=n, swap_sides=True,
                          crn_seed_base=SEED)
        print(f"  {label:36} our wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1})", flush=True)


if __name__ == "__main__":
    main()
