"""Local validation of the built submission before uploading.

Checks the two things that matter for the ladder (per the LB-860 notebook):
  1. 0 errors across a mirror self-play batch -> passes Kaggle validation (which
     plays the agent against a copy of itself) and won't forfeit on exceptions.
  2. Crushes a random agent -> the policy is actually playing.
Also re-checks strength vs the exp002 pool (should match unwrapped lucario_v2).

Loads build/main.py as INDEPENDENT modules per player (the policy uses module
globals, so a mirror must not share them).

Usage: uv run python validate_local.py [n_games]
"""
from __future__ import annotations

import importlib.util
import os
import sys

HERE = os.path.dirname(__file__)
BUILD = os.path.join(HERE, "build")
EXP1 = os.path.abspath(os.path.join(HERE, "..", "exp001_harness"))
EXP2 = os.path.abspath(os.path.join(HERE, "..", "exp002_baselines"))
for p in (EXP1, EXP2):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine, run_gauntlet  # noqa: E402
load_engine()
from baselines import make_policy_agent, make_random_agent_with_deck, DECKS  # noqa: E402

_counter = [0]


def load_submission_agent():
    """Load build/main.py as a fresh independent module (own globals)."""
    _counter[0] += 1
    spec = importlib.util.spec_from_file_location(f"submission_{_counter[0]}",
                                                  os.path.join(BUILD, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(BUILD)  # so it finds deck.csv
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    deck = DECKS["lucario_v2"]

    # 1) mirror self-play: independent modules per side
    a = load_submission_agent()
    b = load_submission_agent()
    st = run_gauntlet(a, b, n_games=n, swap_sides=True)
    print(f"[mirror]   n={n} errors=({st.errors0}+{st.errors1}) "
          f"winrate0={st.winrate0:.3f} avg_moves={st.total_moves/st.n:.0f} reasons={st.reasons}")
    mirror_ok = (st.errors0 + st.errors1) == 0

    # 2) vs random
    sub = load_submission_agent()
    rnd = make_random_agent_with_deck(deck, seed=0)
    st_r = run_gauntlet(sub, rnd, n_games=n, swap_sides=True)
    print(f"[vs random] n={n} winrate={st_r.winrate0:.3f} "
          f"errors=({st_r.errors0}+{st_r.errors1}) ({st_r.wins0}-{st_r.wins1}-{st_r.draws})")

    # 3) vs pool (strength sanity)
    print("[vs pool]")
    wrs = []
    for opp_name in ["dragapult", "lucario_v1", "lucario_v2"]:
        sub = load_submission_agent()
        opp = make_policy_agent(opp_name)
        s = run_gauntlet(sub, opp, n_games=n, swap_sides=True)
        wrs.append(s.winrate0)
        print(f"   vs {opp_name:11s} winrate={s.winrate0:.3f} errors=({s.errors0}+{s.errors1})")
    avg = sum(wrs) / len(wrs)
    print(f"   avg vs rule-based = {avg:.3f} (lucario_v2 baseline 0.680)")

    print("\n=== VERDICT ===")
    print(f"mirror crash-free: {'PASS' if mirror_ok else 'FAIL'}")
    print(f"beats random:      {'PASS' if st_r.winrate0 >= 0.9 else 'WEAK'} ({st_r.winrate0:.3f})")
    print(f"strength retained: {'OK' if avg >= 0.6 else 'CHECK'} ({avg:.3f})")


if __name__ == "__main__":
    main()
