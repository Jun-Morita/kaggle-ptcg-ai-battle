"""Measure the strong Dragapult: threat to v009 + meta fit (0623 shares).

v009 loaded as a BUILT artifact (independent); Dragapult as a module; field
opponents via router/baselines/alakazam loaders.
Usage: uv run python eval_dragapult.py [n]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp013_router"),
          os.path.join(ROOT, "workspace", "exp016_pubnb"), HERE):
    sys.path.insert(0, p)
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import baselines as B  # noqa
import router_policy as R  # noqa
from load_alakazam import make_alakazam_agent  # noqa
from load_dragapult import make_dragapult_agent  # noqa


def load_built(d):
    spec = importlib.util.spec_from_file_location(f"b_{os.path.basename(d)}", os.path.join(d, "main.py"))
    m = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(d); spec.loader.exec_module(m)
    finally:
        os.chdir(prev)
    return m.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    v009 = load_built(os.path.join(ROOT, "workspace", "exp018_adaptive", "build_disc"))
    crustle = R.charmq_deck  # placeholder import check
    CRUSTLE = __import__("json").load(open(os.path.join(ROOT, "workspace", "exp007_anti_crustle", "crustle_deck.json")))

    # Dragapult (agent0) vs each opponent. share = 0623 meta-watch field.
    opps = [
        ("v009 non-ex (OUR deck)", lambda: v009, 0.26),
        ("lucario_ex",            lambda: B.make_policy_agent("lucario_v2"), 0.39),
        ("Alakazam",              lambda: make_alakazam_agent(), 0.11),
        ("crustle(v004)",         lambda: R.make_agent(CRUSTLE), 0.11),
    ]
    wsum = sum(w for *_, w in opps)
    exp = 0.0
    print(f"strong Dragapult vs field (n={n}/matchup):")
    for name, mk, w in opps:
        st = run_gauntlet(make_dragapult_agent(), mk(), n_games=n, swap_sides=True)
        exp += (w / wsum) * st.winrate0
        print(f"  vs {name:24s} wr={st.winrate0:.3f}  (w0={st.wins0} w1={st.wins1}) err=({st.errors0},{st.errors1})")
    print(f"  --> weighted (over {wsum:.2f} of field): {exp:.3f}")
    print("\n(threat read: 'vs v009 non-ex' is how hard Dragapult counters our deck)")


if __name__ == "__main__":
    main()
