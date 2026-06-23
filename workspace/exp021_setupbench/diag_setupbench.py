"""Diagnostic: how often does setup-bench discipline actually change behavior?

Instruments the policy to record, per setup-bench decision: how many Basics the BASE
would bench (=len options) vs how many cap3 benches. If base rarely offers >cap
Basics, the lever is a near no-op for our basic-light deck (explains the neutral result).
Usage: uv run python diag_setupbench.py [n]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp013_router")):
    sys.path.insert(0, p)
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import baselines as B  # noqa
import router_policy as R  # noqa

stats = {"setup_decisions": 0, "base_bench_total": 0, "offered_gt2": 0, "offered_gt3": 0, "max_offered": 0}

INSTR = '''
_orig_choose_diag = LucarioPolicy.choose
def _diag_choose(self):
    if self.context == SelectContext.SETUP_BENCH_POKEMON and self.select.minCount == 0:
        n = len(self.select.option)
        _DIAG["setup_decisions"] += 1
        _DIAG["base_bench_total"] += min(n, self.select.maxCount)
        if n > 2: _DIAG["offered_gt2"] += 1
        if n > 3: _DIAG["offered_gt3"] += 1
        _DIAG["max_offered"] = max(_DIAG["max_offered"], n)
    return _orig_choose_diag(self)
LucarioPolicy.choose = _diag_choose
'''


def make_instrumented(deck):
    spec = importlib.util.spec_from_file_location("diag", os.path.join(R.POLICIES, "lucario_v2.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(R.POLICIES)
        open("deck.csv", "w").write("\n".join(map(str, deck)) + "\n")
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.__dict__["_DIAG"] = stats
    exec(R.PATCH_SRC + "\n" + INSTR, mod.__dict__)

    def agent(obs_dict):
        o = mod.to_observation_class(obs_dict)
        return list(deck) if o.select is None else mod.agent(obs_dict)
    return agent


def main():
    import json
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    deck = json.load(open(os.path.join(HERE, "nonex_deck.json")))
    me = make_instrumented(deck)
    run_gauntlet(me, B.make_policy_agent("lucario_v2"), n_games=n, swap_sides=True)
    d = stats
    sd = max(1, d["setup_decisions"])
    print(f"setup-bench decisions: {d['setup_decisions']}")
    print(f"  avg Basics base benches at setup: {d['base_bench_total']/sd:.2f}")
    print(f"  decisions offering >2 Basics: {d['offered_gt2']} ({100*d['offered_gt2']/sd:.1f}%)  [cap3 would trim only these... actually >3]")
    print(f"  decisions offering >3 Basics: {d['offered_gt3']} ({100*d['offered_gt3']/sd:.1f}%)  <- cap3 only changes these")
    print(f"  max Basics ever offered: {d['max_offered']}")


if __name__ == "__main__":
    main()
