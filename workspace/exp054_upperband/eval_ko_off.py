"""exp054-B -- does GLOBAL ko_mode=False improve LO-mill across BOTH bands?

probe_arch.py (n=100/arm, CRN): vs archaludon baseline 0.680 -> ko OFF 0.830.
Mechanism hypothesis: Neutralization Zone + Crustle Safeguard blank the ex
attacker, so the mill clock wins; ko_mode's race math ignores opponent healing
(Jumbo/Cape) and enters races it loses. Before any ship decision, measure the
side effects on every other matchup (alakazam etc. may need ko_mode for wins).

Usage: uv run python eval_ko_off.py [n] [--crn]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eval_both_bands as EB  # noqa: E402  (loads engine + paths)

LO_DIR = os.path.join(EB.WS, "exp053_bandpool", "lo_opp")
_n = [0]


def make_lo_koforce(deck, force_ko):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_k{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if force_ko is not None:
        mod.should_ko_mode = lambda *a, **k: force_ko

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def main():
    from load_lo import lo_deck
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 300
    use_crn = "--crn" in sys.argv or EB.USE_CRN
    from harness_crn import run_gauntlet
    opp = EB.opponents()
    needed = sorted(set(EB.OUR_BAND) | set(EB.SILVER_BAND))
    print(f"LO stock vs LO ko-OFF, n={n}/matchup, CRN={use_crn}\n")
    results = {}
    for cname, fko in (("stock", None), ("ko_OFF", False)):
        wr = {}
        print(f"=== {cname} ===", flush=True)
        for oname in needed:
            deck, fac = opp[oname]
            t0 = time.time()
            kw = {"crn_seed_base": EB.SEED + abs(hash(oname)) % 99991} if use_crn else {}
            agent = make_lo_koforce(lo_deck(), fko)
            st = run_gauntlet(agent, fac(deck), n_games=n, swap_sides=True, **kw)
            wr[oname] = st.winrate0
            print(f"  {oname:14} wr={st.winrate0:.3f}  ({st.wins0}-{st.wins1}-{st.draws}) "
                  f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
        ours = sum(w * wr[o] for o, w in EB.OUR_BAND.items())
        silv = sum(w * wr[o] for o, w in EB.SILVER_BAND.items()) / sum(EB.SILVER_BAND.values())
        results[cname] = {"wr": wr, "our_band": ours, "silver_band": silv}
        print(f"  --> OUR band {ours:.4f} | SILVER band {silv:.4f}\n", flush=True)

    json.dump(results, open(os.path.join(HERE, f"ko_off_n{n}.json"), "w"), indent=1)
    s, k = results["stock"], results["ko_OFF"]
    print(f"{'opponent':14} {'stock':>7} {'ko_OFF':>7} {'delta':>7}")
    for o in needed:
        print(f"{o:14} {s['wr'][o]:7.3f} {k['wr'][o]:7.3f} {k['wr'][o]-s['wr'][o]:+7.3f}")
    print(f"{'OUR band':14} {s['our_band']:7.4f} {k['our_band']:7.4f} {k['our_band']-s['our_band']:+7.4f}")
    print(f"{'SILVER band':14} {s['silver_band']:7.4f} {k['silver_band']:7.4f} {k['silver_band']-s['silver_band']:+7.4f}")


if __name__ == "__main__":
    main()
