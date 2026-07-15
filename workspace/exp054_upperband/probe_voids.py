"""exp054-D -- quantitative VOID INVENTORY of the LO pilot's select scoring.

"Has a scoring branch" != "effectively scores": if all/most options tie at the
top score, choose() picks arbitrarily = a de-facto structural void (the only
place learned overrides have ever paid: SEARCH_PRI3 precedent, static top-1
0.22 -> learned 0.34-0.42, shipped z=2.40).

Measures per select-context, over real games (koff pilot vs 3 opponents):
  - decisions, mean options, top-tie width (how many options share the max
    score), % of decisions where the top is tied (width>1) -> arbitrary pick.
Usage: uv run python probe_voids.py [n_games_per_opp]
"""
from __future__ import annotations
import importlib.util
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp013_router", "exp007_anti_crustle",
          "exp025_unkoable", "exp023_revenge", "exp053_bandpool", "exp054_upperband"):
    sys.path.insert(0, os.path.join(WS, p))

from harness_crn import load_engine, run_match  # noqa: E402
api, _ = load_engine()
import policy_diff as PD  # noqa: E402
from load_lo import lo_deck  # noqa: E402
import eval_both_bands as EB  # noqa: E402

name_of = PD.ctx_namer()
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
SEED = 20260720
_n = [0]

stats = defaultdict(lambda: {"dec": 0, "opts": 0, "tied": 0, "tie_width": 0})


def make_instrumented(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_v{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.should_ko_mode = lambda *a, **k: False  # v023 config

    orig_score = mod.select_card_score
    rec = []

    def score(card, player_index, context, me, opponent, state, wall_mode, ko_mode):
        s = orig_score(card, player_index, context, me, opponent, state, wall_mode, ko_mode)
        rec.append((context, s))
        return s

    mod.select_card_score = score

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        sel = obs["select"]
        ctx = name_of(sel.get("context"))
        n_opts = len(sel.get("option", []))
        rec.clear()
        out = mod.agent(obs)
        if n_opts >= 2 and rec:
            scores = [s for c, s in rec]
            top = max(scores)
            width = sum(1 for s in scores if s == top)
            st = stats[ctx]
            st["dec"] += 1
            st["opts"] += n_opts
            st["tie_width"] += width
            st["tied"] += int(width > 1)
        return out
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    opp = EB.opponents()
    for oname in ("archaludon", "alakazam", "pure_wall"):
        deck, fac = opp[oname]
        for g in range(n):
            lo = make_instrumented(lo_deck())
            other = fac(deck)
            a0, a1 = (lo, other) if g % 2 == 0 else (other, lo)
            run_match(a0, a1, crn_seed=SEED + g)
        print(f"done vs {oname}", flush=True)

    print(f"\n{'context':24} {'dec':>5} {'avg_opts':>8} {'tie%':>6} {'avg_tie_width':>13}")
    for ctx, st in sorted(stats.items(), key=lambda kv: -kv[1]["dec"]):
        d = st["dec"]
        print(f"{ctx:24} {d:5} {st['opts']/d:8.1f} {st['tied']/d*100:5.1f}% {st['tie_width']/d:13.2f}")


if __name__ == "__main__":
    main()
