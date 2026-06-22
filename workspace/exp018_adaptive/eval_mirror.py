"""Mirror test via independent BUILT artifacts (no module contamination).

Load two built submission main.py files as separate modules and play them head to
head. This is the trustworthy harness (each artifact is self-contained), unlike
multi-module local evals. Default: discipline vs v008 (both charmq non-ex) — the
key question is whether the prize-liability discipline raises the non-ex mirror
(our ladder weakness 0.38).

Usage: uv run python eval_mirror.py [n] [buildA] [buildB]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine, run_gauntlet  # noqa
load_engine()


def load_built(build_dir):
    main = os.path.join(build_dir, "main.py")
    spec = importlib.util.spec_from_file_location(f"built_{os.path.basename(build_dir)}", main)
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(build_dir)        # main.py reads deck.csv from cwd
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    a_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "build_disc")
    b_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "workspace", "exp017_metatiming", "build_v008_ref")
    a = load_built(a_dir)
    b = load_built(b_dir)
    st = run_gauntlet(a, b, n_games=n, swap_sides=True)
    print(f"{os.path.basename(a_dir)} vs {os.path.basename(b_dir)} (MIRROR)")
    print(f"   winrate(A)={st.winrate0:.3f}  (w={st.wins0} l={st.wins1} d={st.draws})  "
          f"err=({st.errors0},{st.errors1})  max_move_s=({st.max_move_time0:.2f},{st.max_move_time1:.2f})")


if __name__ == "__main__":
    main()
