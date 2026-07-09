"""exp043 -- paired candidate-vs-v014 eval using SEPARATE BUILT artifacts
(no shared-module env-var contamination: each main.py is fully flattened/self
-contained text, no `import revenge_policy` at runtime, per tb_patch.py's
PATCH_SRC build). Mirrors exp018's eval_mirror.py pattern.

Usage: uv run python eval_paired.py [n] [buildA] [buildB]
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
        os.chdir(build_dir)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    a_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "build_sp1")
    b_dir = sys.argv[3] if len(sys.argv) > 3 else os.path.join(ROOT, "workspace", "exp035_turnbeam", "build_v014")
    a = load_built(a_dir)
    b = load_built(b_dir)
    st = run_gauntlet(a, b, n_games=n, swap_sides=True)
    print(f"{os.path.basename(a_dir)}(A) vs {os.path.basename(b_dir)}(B), n={n}")
    print(f"  winrate(A)={st.winrate0:.3f}  (w={st.wins0} l={st.wins1} d={st.draws})  "
          f"err=({st.errors0},{st.errors1})  max_move_s=({st.max_move_time0:.2f},{st.max_move_time1:.2f})")


if __name__ == "__main__":
    main()
