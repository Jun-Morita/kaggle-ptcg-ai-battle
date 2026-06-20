"""Does the dedicated non-ex policy beat the generic one in the MIRROR (head-to-head),
without regressing vs ex / Crustle? Mirror is symmetric, so smart-vs-generic > 0.50
means a real piloting edge (the whole point — same deck, better play)."""
from __future__ import annotations
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))

from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
import baselines as B  # noqa
import nonex_policy as NP  # noqa


def show(name, st):
    print(f"  {name:36s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err0={st.errors0} err1={st.errors1}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    print(f"n={n}/matchup, swap sides\n")
    print("== KEY: dedicated (smart) vs generic, SAME non-ex deck (mirror, >0.50 = real edge) ==")
    show("smart vs generic (mirror)", run_gauntlet(NP.make_smart_agent(), NP.make_generic_agent(), n_games=n, swap_sides=True))
    print("\n== regression check: smart vs the meta ==")
    show("smart vs lucario_v2 (ex)", run_gauntlet(NP.make_smart_agent(), AC.make_agent(AC.LUCARIO_DECK), n_games=n, swap_sides=True))
    show("smart vs Crustle",         run_gauntlet(NP.make_smart_agent(), AC.make_crustle_agent(), n_games=n, swap_sides=True))
    show("smart vs dragapult",       run_gauntlet(NP.make_smart_agent(), B.make_policy_agent("dragapult"), n_games=n, swap_sides=True))


if __name__ == "__main__":
    main()
