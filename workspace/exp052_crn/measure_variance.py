"""exp052 -- measure whether CRN actually reduces run-to-run variance of a
paired winrate estimate, using our own real gate (build_sp3 = SEARCH_PRI3
candidate, vs build_v014 = baseline), on the CRN-patched local engine.

Method: run R independent repeats of an n-game swap_sides gauntlet, once with
crn_seed_base=None (today's behavior) and once with a fresh crn_seed_base per
repeat (so each repeat still samples fresh deals, but swap-pairs WITHIN a
repeat share a seed). Compare the between-repeat std-dev of winrate(candidate)
under each condition -- a real std-dev shrink is the actual PokéForge-style
claim, on our own gate.

Usage: uv run python measure_variance.py [n_per_repeat] [n_repeats]
"""
from __future__ import annotations
import importlib.util
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
from harness_crn import run_gauntlet  # noqa

A_DIR = os.path.join(ROOT, "workspace", "exp047_pri_tobench", "build_sp3")
B_DIR = os.path.join(ROOT, "workspace", "exp035_turnbeam", "build_v014")


def load_built(build_dir, tag):
    main = os.path.join(build_dir, "main.py")
    spec = importlib.util.spec_from_file_location(f"built_{tag}", main)
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(build_dir)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 8

    a = load_built(A_DIR, "sp3")
    b = load_built(B_DIR, "v014")

    print(f"CRN variance-reduction measurement: {reps} repeats x n={n} games "
          f"(A=SEARCH_PRI3 candidate, B=v014 baseline)")

    no_crn_rates = []
    t0 = time.time()
    for r in range(reps):
        st = run_gauntlet(a, b, n_games=n, swap_sides=True, crn_seed_base=None)
        no_crn_rates.append(st.winrate0)
        print(f"  [no-CRN]  repeat {r}: winrate(A)={st.winrate0:.3f} "
              f"(w={st.wins0} l={st.wins1} d={st.draws}) err=({st.errors0},{st.errors1})", flush=True)
    t_no_crn = time.time() - t0

    crn_rates = []
    t0 = time.time()
    for r in range(reps):
        st = run_gauntlet(a, b, n_games=n, swap_sides=True, crn_seed_base=1000 + r * 997)
        crn_rates.append(st.winrate0)
        print(f"  [CRN]     repeat {r}: winrate(A)={st.winrate0:.3f} "
              f"(w={st.wins0} l={st.wins1} d={st.draws}) err=({st.errors0},{st.errors1})", flush=True)
    t_crn = time.time() - t0

    sd_no_crn = statistics.pstdev(no_crn_rates)
    sd_crn = statistics.pstdev(crn_rates)
    print()
    print(f"no-CRN: mean={statistics.mean(no_crn_rates):.4f} sd={sd_no_crn:.4f} "
          f"values={[round(x,3) for x in no_crn_rates]} ({t_no_crn:.0f}s)")
    print(f"CRN:    mean={statistics.mean(crn_rates):.4f} sd={sd_crn:.4f} "
          f"values={[round(x,3) for x in crn_rates]} ({t_crn:.0f}s)")
    if sd_crn > 0:
        print(f"variance ratio (no-CRN/CRN) = {(sd_no_crn/sd_crn)**2:.2f}x "
              f"  |  std-dev ratio = {sd_no_crn/sd_crn:.2f}x")
    else:
        print("CRN sd is exactly 0 in this sample (all repeats identical) -- can't form a finite ratio")


if __name__ == "__main__":
    main()
