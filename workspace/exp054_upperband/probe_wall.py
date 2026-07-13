"""exp054 -- instrument the LO pilot's mode predicates in the pure-wall matchup.

Why: LO-mill loses to pure-wall Crustle 0.033, and the loss reason is the
opponent taking all 6 prizes (14/20) -- LO never pressures. Reading the pilot
suggested a structural void:

  should_wall_mode(): `if not opponent_has_ex_or_ex_line_pressure(opponent):
                          return False`
      -> a PURE-WALL Crustle deck runs ZERO ex, so wall_mode can never fire.
  attack_score(GIANT_TUSK): `return 300000 if ko_mode else -5000`
      -> Great Tusk's 160-damage attack is ACTIVELY AVOIDED outside ko_mode.

But should_ko_mode() does real race arithmetic (mill_turns vs attack plans), so
code-reading alone can't settle whether the pilot is stuck in mill-only mode.
Per disc721338's lesson ("instrument so 'never fires' is distinguishable from
'fires wrong'"), MEASURE the firing rates instead of guessing.

Usage: uv run python probe_wall.py [n_games]
"""
from __future__ import annotations
import importlib.util
import os
import sys
from collections import Counter

WS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp007_anti_crustle"),
          os.path.join(WS, "exp053_bandpool")):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import load_engine, run_match  # noqa: E402
load_engine()
import anti_crustle as AC  # noqa: E402
from load_lo import lo_deck  # noqa: E402

LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
stats = Counter()
_n = [0]


def make_instrumented_lo(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_ins{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)

    orig_wall, orig_ko = mod.should_wall_mode, mod.should_ko_mode

    def wall(me, opp, state):
        r = orig_wall(me, opp, state)
        stats["wall_TRUE" if r else "wall_false"] += 1
        return r

    def ko(me, opp, state):
        r = orig_ko(me, opp, state)
        stats["ko_TRUE" if r else "ko_false"] += 1
        return r

    mod.should_wall_mode = wall
    mod.should_ko_mode = ko

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    for g in range(n):
        lo = make_instrumented_lo(lo_deck())
        wall_ag = AC.make_crustle_agent()
        a0, a1 = (lo, wall_ag) if g % 2 == 0 else (wall_ag, lo)
        r = run_match(a0, a1)
        seat = 0 if g % 2 == 0 else 1
        stats["LO_win" if r.winner == seat else "LO_loss"] += 1

    print(f"LO-mill vs PURE-WALL Crustle (n={n}) -- mode firing rates")
    w, wf = stats["wall_TRUE"], stats["wall_false"]
    k, kf = stats["ko_TRUE"], stats["ko_false"]
    if w + wf:
        print(f"  wall_mode: TRUE {w:6} / FALSE {wf:6}  -> fires {w/(w+wf)*100:5.1f}% of calls")
    if k + kf:
        print(f"  ko_mode  : TRUE {k:6} / FALSE {kf:6}  -> fires {k/(k+kf)*100:5.1f}% of calls")
    print(f"  record: {stats['LO_win']}W-{stats['LO_loss']}L")


if __name__ == "__main__":
    main()
