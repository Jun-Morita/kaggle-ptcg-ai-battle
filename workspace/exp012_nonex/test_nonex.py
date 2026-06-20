"""exp012: can we pilot charmq's NON-EX attacker deck (the apex archetype)?

charmq (LB #4) runs Hop's Trevenant + Dudunsparce draw engine, all single-prize,
and beats BOTH ex-beatdown (0.69) and Crustle wall (0.70). We have its exact
60-card list. Question: can a policy pilot it? Try the generic lucario_v2 policy
first (it surprisingly piloted the Crustle deck well as v004). If the non-ex deck
needs its complex engine driven, generic will fail and we'll need a dedicated policy.

Tests the non-ex deck vs the meta: stock lucario_v2 (ex), Crustle (v004), dragapult.
"""
from __future__ import annotations
import importlib.util
import json
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
import baselines as B  # noqa
from cg.api import to_observation_class  # noqa

NONEX = json.load(open(os.path.join(HERE, "charmq_deck.json")))
_n = [0]


def _load_module(pyfile, deck, workdir):
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


def make_nonex_generic():
    """charmq's non-ex deck piloted by the generic lucario_v2 policy."""
    mod = _load_module(os.path.join(POLICIES, "lucario_v2.py"), NONEX, POLICIES)
    def agent(obs):
        o = to_observation_class(obs)
        return list(NONEX) if o.select is None else mod.agent(obs)
    return agent


def make_v003():
    mod = _load_module(os.path.join(EXP7, "policy_anticrustle.py"), AC.LUCARIO_DECK, POLICIES)
    def agent(obs):
        o = to_observation_class(obs)
        return list(AC.LUCARIO_DECK) if o.select is None else mod.agent(obs)
    return agent


def show(name, st):
    print(f"  {name:34s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err0={st.errors0} err1={st.errors1}")


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    print(f"non-ex deck (charmq replica), generic lucario_v2 policy. n={n}/matchup\n")
    print("== apex test: does non-ex beat ex AND Crustle (like charmq 0.69/0.70)? ==")
    show("nonex vs lucario_v2 (ex)",  run_gauntlet(make_nonex_generic(), AC.make_agent(AC.LUCARIO_DECK), n_games=n, swap_sides=True))
    show("nonex vs Crustle (v004)",   run_gauntlet(make_nonex_generic(), AC.make_crustle_agent(), n_games=n, swap_sides=True))
    show("nonex vs v003 (our ex)",    run_gauntlet(make_nonex_generic(), make_v003(), n_games=n, swap_sides=True))
    show("nonex vs dragapult",        run_gauntlet(make_nonex_generic(), B.make_policy_agent("dragapult"), n_games=n, swap_sides=True))


if __name__ == "__main__":
    main()
