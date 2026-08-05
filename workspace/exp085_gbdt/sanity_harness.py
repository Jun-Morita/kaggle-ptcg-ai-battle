"""Does run_gauntlet reproduce a number we already trust?

Before re-running every GBDT gate on this harness, check it against a known value:
the shipped v3s+MCTS build scores ~0.40 vs Mega Lucario ex in gate_field.py
(0.330 and 0.470 in two n=100 runs). If run_gauntlet lands in that range, the
harness is sound and the GBDT numbers it produces can be read at face value.

This is the step eval_gbdt.py skipped, and skipping it cost a night of numbers.
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
for p in ("exp001_harness", "exp007_anti_crustle", "exp040_mctsv2",
          "exp041_pilotnet", "exp019_finisher", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))
import feats  # noqa: E402
from harness import run_gauntlet  # noqa: E402
from eval_h2h import opponent, with_deck  # noqa: E402

n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 60
grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
ship = opponent("ship", grimm)
import anti_crustle as AC  # noqa: E402
t0 = time.time()
st = run_gauntlet(ship, AC.make_agent(AC.LUCARIO_DECK), n_games=n, swap_sides=True)
wr = st.wins0 / max(1, st.n)
print(f"SHIP v3s+MCTS vs lucario_v2 on run_gauntlet: {st.wins0}-{st.wins1}-{st.draws} "
      f"wr {wr:.3f} err_us {st.errors0} ({time.time()-t0:.0f}s)")
print("gate_field reference for the same pairing: 0.330 / 0.470 (n=100 each)")
