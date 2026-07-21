"""exp070j — DECISIVE test: remove Dunsparce from EX_EVOLUTION_ANCESTORS.

Story so far, with the measurement bug corrected:
  - Ground truth (303 real games): opponent_has_ex_or_ex_line_pressure fires on
    80.3% of games where the opponent runs NO ex. Culprit cards: Dunsparce 48,
    Applin 6, Dipplin 6, Duraludon 5, Riolu 2 (of 61 false-positive games).
  - EX_EVOLUTION_ANCESTORS collects every name that is transitively an ancestor
    of ANY ex in the card pool (105 names). Basics that evolve into BOTH an ex
    and a non-ex line therefore assert "ex pressure" on sight. Dunsparce is the
    core of the non-ex attacker deck = our largest matchup (weight 0.289).
  - wall_mode's gate is `opponent_ex_pressure(...) OR shows_ex_evolution_line(...)`,
    so fixing ex_pressure alone cannot help -- confirmed: with real CRN the
    ready_now+bench_strict bundle scored EXACTLY +0.0000 in all 8 matchups.
  - Adding the Dunsparce removal: +0.0300, essentially all from alakazam_dun (+0.080).

This run isolates the Dunsparce fix alone at n=600 with TRUE CRN and computes
McNemar significance from discordant paired games (CRN makes most games identical,
so the paired test is the right one -- an unpaired z would waste the pairing).

Harness note (bug found 07-21): eval_both_bands only selects the CRN harness when
"--crn" is in sys.argv; otherwise it caches the PLAIN engine and every later
harness_crn import is inert. Asserted below.
"""
from __future__ import annotations
import os, sys, json, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
assert EB.USE_CRN, "CRN harness not active"
import cg as _cg
assert "exp052_crn" in _cg.__file__, f"plain engine: {_cg.__file__}"
sys.path.insert(0, EB.CRN)
from harness_crn import run_match

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")
_n = [0]


def make_koff(no_dun: bool):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"koffd{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if no_dun:
        mod.EX_EVOLUTION_ANCESTORS = {n for n in mod.EX_EVOLUTION_ANCESTORS
                                      if n != "Dunsparce"}
    return mod.agent


def play(agent, fac, deck, n, seed_base):
    """Return per-game results (1=we won) so paired games can be compared."""
    out = []
    errs = 0
    for g in range(n):
        swapped = (g % 2 == 1)
        opp_agent = fac(deck)
        a0, a1 = (opp_agent, agent) if swapped else (agent, opp_agent)
        r = run_match(a0, a1, crn_seed=seed_base + (g // 2))
        w = r.winner
        if swapped and w in (0, 1):
            w = 1 - w
        if r.error_player != -1:
            errs += 1
        out.append(1 if w == 0 else 0)
    return out, errs


def main():
    n = int([a for a in sys.argv[1:] if a.isdigit()][0]) if any(
        a.isdigit() for a in sys.argv[1:]) else 600
    opp = EB.opponents()
    res, disc_tot = {}, [0, 0]
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        seed = EB.SEED + abs(hash("nodun" + oname)) % 99991
        a, ea = play(make_koff(False), fac, deck, n, seed)
        b, eb = play(make_koff(True), fac, deck, n, seed)
        # discordant pairs: same seed, different outcome
        b_wins = sum(1 for x, y in zip(a, b) if y == 1 and x == 0)   # fix won, base lost
        a_wins = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)   # base won, fix lost
        disc_tot[0] += b_wins
        disc_tot[1] += a_wins
        res[oname] = {"base": sum(a) / n, "no_dun": sum(b) / n,
                      "fix_only_wins": b_wins, "base_only_wins": a_wins,
                      "err": ea + eb}
        print(f"  {oname:16s} w={w:.3f} base {sum(a)/n:.3f} no_dun {sum(b)/n:.3f} "
              f"({sum(b)/n-sum(a)/n:+.3f})  discordant: fix+{b_wins} base+{a_wins}  "
              f"err={ea+eb}", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    sb = sum(w * res[o]["base"] for o, w in EB.SILVER_BAND.items()) / tot
    sf = sum(w * res[o]["no_dun"] for o, w in EB.SILVER_BAND.items()) / tot
    print(f"\nSILVER(V2)  base {sb:.4f}   no_dun {sf:.4f}   delta {sf-sb:+.4f}")
    nb, na = disc_tot
    if nb + na:
        # McNemar exact-ish: under H0 each discordant pair is a fair coin
        z = (nb - na) / ((nb + na) ** 0.5)
        print(f"McNemar over ALL discordant games: fix-wins {nb}, base-wins {na}, "
              f"n_disc {nb+na}  ->  z = {z:+.2f}")
    json.dump(res, open(os.path.join(HERE, f"nodun{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
