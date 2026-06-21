"""exp015 eval: does the tactical exact-search layer beat / not-regress v008?

  tactical(charmq) vs v008(charmq)   -> mirror, pure value of the search layer
  tactical(charmq) vs lucario_v2(ex) -> no regression vs ex (ref: v008)
Usage: uv run python eval_tactical.py [n]
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
from tactical_search import make_tactical_agent  # noqa: E402


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    charmq = R.charmq_deck()

    pairs = [
        ("tactical(charmq) vs v008(charmq) [MIRROR]",
         make_tactical_agent(charmq), R.make_agent(charmq)),
        ("tactical(charmq) vs lucario_v2 (ex)",
         make_tactical_agent(charmq), B.make_policy_agent("lucario_v2")),
        ("v008(charmq) vs lucario_v2 (ex) [ref]",
         R.make_agent(charmq), B.make_policy_agent("lucario_v2")),
    ]
    for label, a0, a1 in pairs:
        st = run_gauntlet(a0, a1, n_games=n, swap_sides=True)
        print(f"{label}\n   winrate(agent0)={st.winrate0:.3f}  "
              f"max_move_s=({st.max_move_time0:.2f},{st.max_move_time1:.2f})  "
              f"err0={st.errors0} avg_moves={st.total_moves/st.n:.0f}")


if __name__ == "__main__":
    main()
