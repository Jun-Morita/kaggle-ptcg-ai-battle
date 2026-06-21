"""Eval our agents vs the public 5th-place Alakazam (new top-meta opponent).

  v008(charmq non-ex) vs Alakazam   -> does our deck handle Alakazam?
  lucario_v2 (ex)      vs Alakazam   -> reference (ex vs Alakazam)
Note: Alakazam runs Enhanced Hammer (strips Mist/Rock special energy) -- our
charmq deck uses Mist Energy, so this matchup is worth checking.
Usage: uv run python eval_vs_alakazam.py [n]
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp013_router"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import run_gauntlet  # noqa: E402
import baselines as B  # noqa: E402
import router_policy as R  # noqa: E402
from load_alakazam import make_alakazam_agent  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    charmq = R.charmq_deck()
    pairs = [
        ("v008(charmq non-ex) vs Alakazam", R.make_agent(charmq), make_alakazam_agent()),
        ("lucario_v2 (ex) vs Alakazam", B.make_policy_agent("lucario_v2"), make_alakazam_agent()),
    ]
    for label, a0, a1 in pairs:
        st = run_gauntlet(a0, a1, n_games=n, swap_sides=True)
        print(f"{label}\n   winrate(agent0)={st.winrate0:.3f}  "
              f"(w0={st.wins0} w1={st.wins1} draw={st.draws})  "
              f"err0={st.errors0} err1={st.errors1} max_move_s=({st.max_move_time0:.2f},{st.max_move_time1:.2f})")


if __name__ == "__main__":
    main()
