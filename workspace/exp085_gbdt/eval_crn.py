"""Paired A/B of two built agents on common random numbers.

Why this exists. Two n=1000 runs of the SAME build against the SAME opponent
came out 0.512 and 0.536 -- a 0.024 swing that is ordinary sampling noise at
that sample size (se ~= 0.016 each, so ~0.022 on the difference). Every change
we have measured in the last two days sits at or below that: teacher quality
+0.017, opponent features +0.019 in the mirror. The gate has been reading
differences it cannot resolve, and separating 0.01 the naive way needs n ~ 10000
games, about three hours per comparison.

CRN fixes the sampling, not the sample size. Games g and g+1 are a swap pair
that share a seed, so both agents see the identical deal from both seats and the
"who got the better hands" component cancels. exp052 measured a 4.66x variance
reduction on our own gate, and then never wired it into one.

IMPORTANT: this runs on the CRN-patched local engine
(workspace/exp052_crn/cg + libcg_crn.so -- the official source with only
ApiBattleStart's seed handling touched). It is a MEASUREMENT tool. Anything we
actually submit is still built and smoke-tested against the official engine by
build_submission.py; never validate a shipping artifact here.

Usage:
  uv run python eval_crn.py --a build_v8 --b build_v6 --n 1600 [--repeats 1]
  uv run python eval_crn.py --a build_v8 --b build_v6 --n 400 --repeats 6 --nocrn
"""
from __future__ import annotations
import importlib.util
import math
import os
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CRN = os.path.join(ROOT, "workspace", "exp052_crn")
sys.path.insert(0, CRN)
from harness_crn import run_gauntlet  # noqa: E402


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def load_built(build_dir, tag):
    """Exec the built main.py the way the sandbox does, from its own directory.

    The build dir carries its own cg/ and model, and main.py resolves them
    relative to the cwd, so the chdir is load-bearing.
    """
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
    a_dir = os.path.join(HERE, arg("--a", "build_v8"))
    b_dir = os.path.join(HERE, arg("--b", "build_v6"))
    n = int(arg("--n", "400"))
    repeats = int(arg("--repeats", "1"))
    crn = "--nocrn" not in sys.argv
    a = load_built(a_dir, "a")
    b = load_built(b_dir, "b")
    print(f"A={os.path.basename(a_dir)}  B={os.path.basename(b_dir)}  "
          f"n={n} x{repeats}  CRN={'on' if crn else 'off'}", flush=True)
    wrs = []
    t0 = time.time()
    for r in range(repeats):
        base = 1000 + r * 100000 if crn else None
        st = run_gauntlet(a, b, n_games=n, swap_sides=True, crn_seed_base=base)
        wr = st.winrate0
        wrs.append(wr)
        print(f"  repeat {r+1}: {st.wins0}-{st.wins1}-{st.draws}  wr {wr:.4f}"
              f"  err {st.errors0}/{st.errors1}  ({time.time()-t0:.0f}s)", flush=True)
    m = statistics.fmean(wrs)
    naive_se = math.sqrt(0.25 / n)
    line = f"\n  mean wr {m:.4f}   naive se at n={n} is {naive_se:.4f}"
    if repeats >= 2:
        sd = statistics.stdev(wrs)
        line += (f"\n  observed sd across repeats {sd:.4f}"
                 f"   variance ratio vs naive {(naive_se/sd)**2 if sd else float('inf'):.2f}x")
    print(line)


if __name__ == "__main__":
    main()
