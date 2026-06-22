"""Paired apples-to-apples: discipline-built vs v008-built against the SAME opponents.

Runs both built artifacts (independent modules, no contamination) against each meta
opponent at the same n, back to back, so the comparison is fair (absolute level may
shift run-to-run, but the disc-vs-v008 delta per opponent is the signal).
Usage: uv run python eval_compare.py [n]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp007_anti_crustle")):
    sys.path.insert(0, p)
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import baselines as B  # noqa
import anti_crustle as AC  # noqa


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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    disc = load_built(os.path.join(HERE, "build_disc"))
    v008 = load_built(os.path.join(ROOT, "workspace", "exp017_metatiming", "build_v008_ref"))
    opps = [("lucario_v2(ex)", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("Crustle", AC.make_crustle_agent),
            ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    print(f"{'opponent':16s} {'discipline':>11s} {'v008':>8s}  delta")
    for name, mk in opps:
        sd = run_gauntlet(disc, mk(), n_games=n, swap_sides=True).winrate0
        sv = run_gauntlet(v008, mk(), n_games=n, swap_sides=True).winrate0
        print(f"{name:16s} {sd:11.3f} {sv:8.3f}  {sd-sv:+.3f}")


if __name__ == "__main__":
    main()
