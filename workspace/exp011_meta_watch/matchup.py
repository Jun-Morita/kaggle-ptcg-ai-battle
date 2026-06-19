"""Verify the rotated meta locally: does anti-ex Crustle control beat the now-
dominant Lucario-ex field? Confirm v003 loses the ex mirror.

Agents:
  v003           = anti-Crustle patched lucario_v2 on LUCARIO deck (our submitted best)
  lucario_v2     = stock lucario_v2 policy on LUCARIO deck (the dominant field ~57%)
  crustle_v005   = dedicated Crustle control policy (exp009) on CRUSTLE deck
  crustle_v004   = generic lucario_v2 policy piloting CRUSTLE deck (the weak mimic)
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
EXP1 = os.path.join(ROOT, "workspace", "exp001_harness")
EXP2 = os.path.join(ROOT, "workspace", "exp002_baselines")
EXP7 = os.path.join(ROOT, "workspace", "exp007_anti_crustle")
EXP9 = os.path.join(ROOT, "workspace", "exp009_crustle_policy")
POLICIES = os.path.join(EXP2, "policies")
for p in (EXP1, EXP2, EXP7):
    sys.path.insert(0, p)

from harness import load_engine, run_gauntlet  # noqa
load_engine()
import anti_crustle as AC  # noqa
from cg.api import to_observation_class  # noqa

LUCARIO = AC.LUCARIO_DECK
CRUSTLE = AC.CRUSTLE_DECK

_n = [0]


def _load_module(pyfile, deck, workdir):
    """Load a policy module fresh with deck.csv written into workdir."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"m_{_n[0]}", pyfile)
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(workdir)
        with open("deck.csv", "w") as f:
            f.write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def make_v003():
    mod = _load_module(os.path.join(EXP7, "policy_anticrustle.py"), LUCARIO, POLICIES)
    def agent(obs):
        o = to_observation_class(obs)
        return list(LUCARIO) if o.select is None else mod.agent(obs)
    return agent


def make_lucario_v2():
    return AC.make_agent(LUCARIO)


def make_crustle_v005():
    mod = _load_module(os.path.join(EXP9, "crustle_policy.py"), CRUSTLE, EXP9)
    def agent(obs):
        o = to_observation_class(obs)
        return list(CRUSTLE) if o.select is None else mod.agent(obs)
    return agent


def make_crustle_v004():
    return AC.make_crustle_agent()


def show(name, st):
    print(f"  {name:32s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err0={st.errors0} err1={st.errors1}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"n={n} games/matchup (swap sides)\n")
    print("== current meta = Lucario-ex (57% of field). Counter candidates ==")
    show("crustle_v005 vs lucario_v2", run_gauntlet(make_crustle_v005(), make_lucario_v2(), n_games=n, swap_sides=True))
    show("crustle_v004 vs lucario_v2", run_gauntlet(make_crustle_v004(), make_lucario_v2(), n_games=n, swap_sides=True))
    show("v003        vs lucario_v2", run_gauntlet(make_v003(), make_lucario_v2(), n_games=n, swap_sides=True))
    print("\n== rock-paper-scissors check ==")
    show("crustle_v005 vs v003", run_gauntlet(make_crustle_v005(), make_v003(), n_games=n, swap_sides=True))
    show("v003        vs crustle_v004", run_gauntlet(make_v003(), make_crustle_v004(), n_games=n, swap_sides=True))


if __name__ == "__main__":
    main()
