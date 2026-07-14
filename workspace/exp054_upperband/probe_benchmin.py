"""exp054-C2 -- counterfactual: force MINIMAL BENCH on the LO pilot.

Silver-band LO players (same 60/60 deck, LB 965/938/923) diverge from our pilot
mainly by benching NOTHING at setup (0/3 match) and declining TO_BENCH (0/12).
Mechanism: LO's only loss route is giving up 6 prizes; every benched Pokemon is
a free gust target. Force [] on SETUP_BENCH_POKEMON / TO_BENCH when minCount==0
and compare vs stock on shared CRN seeds.

Usage: uv run python probe_benchmin.py [n_per_arm]
"""
from __future__ import annotations
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in (os.path.join(WS, "exp052_crn"), os.path.join(WS, "exp001_harness"),
          os.path.join(WS, "exp013_router"), os.path.join(WS, "exp025_unkoable"),
          os.path.join(WS, "exp053_bandpool")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness_crn import load_engine, run_gauntlet  # noqa: E402
api, _ = load_engine()
import policy_diff as PD  # noqa: E402
from load_lo import lo_deck  # noqa: E402
import eval_both_bands as EB  # noqa: E402

name_of = PD.ctx_namer()
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
SEED = 20260717
_n = [0]


def make_lo(deck, benchmin=False, koff=False):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_b{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if koff:
        mod.should_ko_mode = lambda *a, **k: False

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        if benchmin:
            sel = obs["select"]
            ctx = name_of(sel.get("context"))
            if ctx in ("SETUP_BENCH_POKEMON", "TO_BENCH") and sel.get("minCount", 1) == 0:
                return []
        return mod.agent(obs)
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    opp = EB.opponents()
    arms = (("stock", dict()), ("koff", dict(koff=True)),
            ("benchmin", dict(benchmin=True)), ("koff+benchmin", dict(koff=True, benchmin=True)))
    for oname in ("archaludon", "alakazam", "marnie", "dragapult"):
        deck, fac = opp[oname]
        print(f"--- vs {oname} (n={n}/arm, shared seeds) ---", flush=True)
        for label, kw in arms:
            agent = make_lo(lo_deck(), **kw)
            st = run_gauntlet(agent, fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=SEED + abs(hash(oname)) % 9999)
            print(f"  {label:14} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})", flush=True)


if __name__ == "__main__":
    main()
