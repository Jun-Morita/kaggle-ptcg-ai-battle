"""exp041 ship-path trial -- bespoke build+smoke for the numpy-FREE MCTS agent.

Unlike scripts/build_submission.py's generic 3-file build (main.py+deck.csv+cg/),
this agent needs a 4th top-level file: the ~51MB weights_pure.pkl weight file
(npmcts_policy.py loads it via a path relative to __file__, same pattern
deck.csv already uses). v015's first submission crashed ("Validation Episode
failed") because it used numpy, which no prior submission ever verified was
available in the sandbox and which cg's own source never imports -- this build
uses the numpy-free npmcts_policy.py (pure math/array/pickle) instead.

Usage: uv run python build_np_submission.py [--n 8]
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import shutil
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CG = os.path.join(ROOT, "data", "sim_sample", "cg")
DECK = os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")
# v017 (2026-07-11): pre3b checkpoint — pre2 + grimmsnarl synthetic + real-ladder
# corpus + Yushin expert x10. eval_raw old-5 total 2.24 (> pre2's 2.14), grimmsnarl
# 0.60, expert-holdout top-1 0.549 (vs pre2's 0.436). Paired mirror vs v014 = 0.483
# (no edge, but not worse); shipped as the ladder RL probe replacing v015-fix4 (pre2).
WEIGHTS_SRC = os.path.join(HERE, "results", "pre3b", "weights_pure.pkl")  # numpy-free, oracle-free-capable
OUT = os.path.join(HERE, "build_np")


def build():
    deck = json.load(open(DECK))
    assert len(deck) == 60
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(os.path.join(HERE, "npmcts_policy.py"), os.path.join(OUT, "main.py"))
    open(os.path.join(OUT, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")
    dst = os.path.join(OUT, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    # weights INSIDE cg/: cg/ contents are proven-delivered (libcg.so must arrive
    # for any agent to run), dodging any top-level-file whitelist in the extractor
    shutil.copy(WEIGHTS_SRC, os.path.join(dst, "weights_pure.pkl"))

    tarp = os.path.join(OUT, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(os.path.join(OUT, "main.py"), arcname="main.py")
        tar.add(os.path.join(OUT, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))
    names = set(tarfile.open(tarp).getnames())
    assert {"main.py", "deck.csv", "cg/weights_pure.pkl", "cg/api.py", "cg/libcg.so"} <= names
    top = sorted(n for n in names if "/" not in n)
    print(f"built {tarp} | top-level={top} | files={len(names)} | "
          f"size={os.path.getsize(tarp) / 1e6:.1f}MB")
    return tarp


def smoke(tarp, n):
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp002_baselines"))
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp007_anti_crustle"))
    from harness import load_engine, run_gauntlet
    load_engine()
    import anti_crustle as AC
    import baselines as B
    import tempfile
    d = tempfile.mkdtemp(prefix="smoke_np_")
    with tarfile.open(tarp) as t:
        t.extractall(d, filter="data")
    spec = importlib.util.spec_from_file_location("built", os.path.join(d, "main.py"))
    m = importlib.util.module_from_spec(spec)
    prev = os.getcwd(); os.chdir(d)
    t0 = time.time()
    spec.loader.exec_module(m)
    load_s = time.time() - t0
    os.chdir(prev)
    print(f"module load (incl. npnet.npz read) took {load_s:.1f}s")

    opps = [("lucario_v2(ex)", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("Crustle", AC.make_crustle_agent),
            ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    print(f"\n=== smoke test (built artifact, n={n}/matchup, search_count={16}) ===")
    ok = True
    t0 = time.time()
    for name, mk in opps:
        st = run_gauntlet(m.agent, mk(), n_games=n, swap_sides=True)
        print(f"  vs {name:14s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) "
              f"err0={st.errors0} err1={st.errors1}")
        if st.errors0:
            ok = False
    dt = time.time() - t0
    ng = n * len(opps) * 2
    print(f"total {dt:.0f}s for {ng} games ({dt/ng:.2f}s/game)")
    print("SMOKE OK (0 errors)." if ok else "SMOKE WARNING: errors raised — investigate.")
    return ok


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=8)
    args = ap.parse_args()
    tarp = build()
    smoke(tarp, args.n)
