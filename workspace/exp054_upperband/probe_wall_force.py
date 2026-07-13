"""exp054 -- counterfactual: force ko_mode OFF (pure mill) / ON vs pure wall.
probe_wall.py showed ko_mode fires 73.2% and LO goes 1-11: the pilot races the
wall and loses the race. Question: would NOT racing (pure mill) win instead?
Usage: uv run python probe_wall_force.py [n_games]
"""
from __future__ import annotations
import importlib.util, os, sys
WS = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp007_anti_crustle"),
          os.path.join(WS, "exp053_bandpool")):
    sys.path.insert(0, p)
from harness import load_engine, run_match  # noqa: E402
load_engine()
import anti_crustle as AC  # noqa: E402
from load_lo import lo_deck  # noqa: E402

LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")
_n = [0]

def make_forced_lo(deck, force):  # force: None|True|False
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"lo_f{_n[0]}", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR); spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if force is not None:
        mod.should_ko_mode = lambda *a, **k: force
    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent

def run(force, n):
    w = l = 0
    for g in range(n):
        lo = make_forced_lo(lo_deck(), force)
        wall = AC.make_crustle_agent()
        a0, a1 = (lo, wall) if g % 2 == 0 else (wall, lo)
        r = run_match(a0, a1)
        seat = 0 if g % 2 == 0 else 1
        if r.winner == seat: w += 1
        else: l += 1
    return w, l

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    for label, force in (("baseline (as-is)", None), ("ko_mode FORCED OFF (pure mill)", False),
                         ("ko_mode FORCED ON (pure race)", True)):
        w, l = run(force, n)
        print(f"{label:32} {w}W-{l}L  wr={w/(w+l):.3f}", flush=True)

if __name__ == "__main__":
    main()
