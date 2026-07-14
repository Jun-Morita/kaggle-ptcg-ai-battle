"""exp054-B -- instrument + counterfactual-force the LO pilot's mode predicates
vs the ARCHALUDON matchup (45% of v021's current-altitude field, live wr 0.62,
pool wr 0.713). Same method that settled the pure-wall question (probe_wall*).

Arms (CRN: identical seeds across arms, swap-pair shares a seed):
  baseline     -- as-is, with firing-rate counters
  wall_off/on  -- force should_wall_mode False / True
  ko_off/on    -- force should_ko_mode  False / True

Usage: uv run python probe_arch.py [n_games_per_arm]
"""
from __future__ import annotations
import importlib.util
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in (os.path.join(WS, "exp052_crn"), os.path.join(WS, "exp001_harness"),
          os.path.join(WS, "exp025_unkoable"), os.path.join(WS, "exp053_bandpool")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness_crn import load_engine, run_match  # noqa: E402
load_engine()
from load_archaludon import make_archaludon_agent  # noqa: E402
from load_lo import lo_deck  # noqa: E402

LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
SEED = 20260716
_n = [0]


def make_lo(deck, force_wall=None, force_ko=None, stats=None):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_a{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    ow, ok = mod.should_wall_mode, mod.should_ko_mode
    def wall(me, opp, state):
        r = ow(me, opp, state) if force_wall is None else force_wall
        if stats is not None:
            stats["wall_TRUE" if r else "wall_false"] += 1
        return r
    def ko(me, opp, state):
        r = ok(me, opp, state) if force_ko is None else force_ko
        if stats is not None:
            stats["ko_TRUE" if r else "ko_false"] += 1
        return r
    mod.should_wall_mode, mod.should_ko_mode = wall, ko

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def run_arm(label, n, force_wall=None, force_ko=None):
    stats = Counter()
    w = l = d = 0
    for g in range(n):
        lo = make_lo(lo_deck(), force_wall, force_ko, stats)
        opp = make_archaludon_agent()
        a0, a1 = (lo, opp) if g % 2 == 0 else (opp, lo)
        r = run_match(a0, a1, crn_seed=SEED + (g // 2))
        seat = 0 if g % 2 == 0 else 1
        if r.winner == seat:
            w += 1
        elif r.winner == 1 - seat:
            l += 1
        else:
            d += 1
    wr = w / max(1, w + l + d)
    extra = ""
    if force_wall is None and force_ko is None:
        cw, cwf = stats["wall_TRUE"], stats["wall_false"]
        ck, ckf = stats["ko_TRUE"], stats["ko_false"]
        extra = (f"  | wall fires {cw}/{cw+cwf} ({cw/max(1,cw+cwf)*100:.1f}%)"
                 f"  ko fires {ck}/{ck+ckf} ({ck/max(1,ck+ckf)*100:.1f}%)")
    print(f"{label:14} {w}W-{l}L-{d}D  wr={wr:.3f}{extra}", flush=True)


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    print(f"LO-mill vs ARCHALUDON proxy, n={n}/arm, CRN shared seeds across arms\n")
    run_arm("baseline", n)
    run_arm("wall OFF", n, force_wall=False)
    run_arm("wall ON", n, force_wall=True)
    run_arm("ko OFF", n, force_ko=False)
    run_arm("ko ON", n, force_ko=True)


if __name__ == "__main__":
    main()
