"""exp019 eval: does the prize-aware verified-lethal finisher add wins over v009?

Minimal imports (finisher + discipline only) to avoid the multi-module
contamination seen in exp017. Mirror = finisher(charmq) vs v009(charmq).
Usage: uv run python eval_finisher.py [n]
"""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp013_router"),
          os.path.join(ROOT, "workspace", "exp018_adaptive"), HERE):
    sys.path.insert(0, p)

from harness import run_gauntlet  # noqa
import router_policy as R  # noqa
import discipline_policy as D  # noqa
import finisher_policy as F  # noqa


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    charmq = R.charmq_deck()
    st = run_gauntlet(F.make_agent(charmq), D.make_agent(charmq), n_games=n, swap_sides=True)
    print(f"finisher(v009+lethal) vs v009  winrate={st.winrate0:.3f} "
          f"(w={st.wins0} l={st.wins1} d={st.draws}) err=({st.errors0},{st.errors1}) "
          f"max_move_s=({st.max_move_time0:.2f},{st.max_move_time1:.2f})")
    print(f"finisher STATS: {F.STATS}  "
          f"(searched=near-lethal decisions, known=prize-set deduced, fired=verified-lethal override)")


if __name__ == "__main__":
    main()
