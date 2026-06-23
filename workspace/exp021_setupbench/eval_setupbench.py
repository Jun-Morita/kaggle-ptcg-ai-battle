"""exp021: does SETUP-BENCH discipline beat v009? Paired, built artifacts only.

The signal is the MIRROR (v010-cap vs v009): v009's weakness is the non-ex mirror
(0.40), and setup-bench over-commitment is a prize-liability leak there. We also
spot-check the field (ex / Crustle / dragapult) for regressions. Built artifacts are
loaded independently (no STATE-contamination). n>=200 to clear the +-0.05 noise floor.

Usage: uv run python eval_setupbench.py [n]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp007_anti_crustle"),
          os.path.join(ROOT, "workspace", "exp016_pubnb")):
    sys.path.insert(0, p)
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
from load_alakazam import make_alakazam_agent  # noqa


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
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    v009 = load_built(os.path.join(ROOT, "workspace", "exp018_adaptive", "build_disc"))
    caps = {c: load_built(os.path.join(HERE, f"build_cap{c}")) for c in (2, 3, 4)}

    # --- 1) MIRROR: each cap variant (agent0) vs v009 (agent1). >0.50 = improvement.
    print(f"=== MIRROR vs v009 (n={n}) — the key signal ===")
    for c, ag in caps.items():
        st = run_gauntlet(ag, v009, n_games=n, swap_sides=True)
        print(f"  cap{c} vs v009: wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{n*2-st.wins0-st.wins1}) err=({st.errors0},{st.errors1})")

    # --- 2) FIELD regression check: best-looking cap vs the rest of the field, paired w/ v009.
    nf = max(80, n // 2)
    field = [("lucario_ex", lambda: AC.make_agent(AC.LUCARIO_DECK)),
             ("Crustle",    AC.make_crustle_agent),
             ("Alakazam",   lambda: make_alakazam_agent()),
             ("dragapult",  lambda: B.make_policy_agent("dragapult"))]
    print(f"\n=== FIELD (n={nf}) — cap3 vs v009 per opponent (delta = regression check) ===")
    print(f"{'opponent':14s} {'cap3':>8s} {'v009':>8s}  delta")
    for name, mk in field:
        sc = run_gauntlet(caps[3], mk(), n_games=nf, swap_sides=True).winrate0
        sv = run_gauntlet(v009, mk(), n_games=nf, swap_sides=True).winrate0
        print(f"{name:14s} {sc:8.3f} {sv:8.3f}  {sc-sv:+.3f}")


if __name__ == "__main__":
    main()
