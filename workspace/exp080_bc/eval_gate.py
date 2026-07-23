"""exp080 pre-registered kill-gate -- the RAW BC net (policy argmax, NO search),
piloting the canonical Grimmsnarl (mixed_ex3) list, vs pub1034 stock on the SAME
deck (mirror). Seat-alternated, n>=200. Pass line: winrate >= 0.55.

Rationale for the opponent: exp080's top-band scan shows Grimmsnarl is 43% of the
silver band and its own mirror is the single largest matchup a Grimmsnarl agent
faces (37.5% of the teacher corpus's opponents). pub1034 is our strongest
available generic pilot (the one that re-piloted the pool in exp074). Beating it
in the mirror is the cheapest honest read on whether the BC net actually pilots.

We evaluate the torch .pth directly: npnet.py parity confirmed the numpy net that
would ship makes byte-identical argmax picks (500/500), so the torch argmax IS the
shipped policy. oracle-free is forced (real ladder opp deck is unknown; the net was
trained with opp-word dropout 0.5).

Usage: uv run python eval_gate.py [model.pth] [n]
"""
from __future__ import annotations
import os, sys, json, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402  (reuses make_raw_agent + run_matchup)
import importlib.util  # noqa: E402

PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def make_pub1034(deck):
    """Load a fresh pub1034 agent instance piloting `deck`."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pub80_{_n[0]}", os.path.join(PUB, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(PUB)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.read_deck_csv = lambda: list(deck)
    return mod.agent


def raw_oraclefree(model, my_deck, opp_deck):
    """agent_factory for run_matchup that forces oracle-free (ship condition)."""
    return ER.make_raw_agent(model, my_deck, opp_deck, oracle_free=True)


def main():
    model_path = next((a for a in sys.argv[1:] if a.endswith(".pth")),
                      os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm1", "model_ep2.pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 200)

    deck = json.load(open(os.path.join(HERE, "grimmsnarl_deck.json")))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    print(f"KILL-GATE  net={os.path.relpath(model_path, WS)}  deck=Grimmsnarl(modal)  "
          f"opp=pub1034 mirror  n={n}  pass>=0.55", flush=True)
    t0 = time.time()
    w, l, d, e = ER.run_matchup(model, deck, deck, make_pub1034, n, agent_factory=raw_oraclefree)
    played = w + l + d
    wr = w / played if played else 0.0
    print(f"\nnet {w}-{l}-{d}  errors={e}  winrate={wr:.3f}  ({time.time()-t0:.0f}s)")
    print("VERDICT:", "PASS (>=0.55) -> distill+ship path" if wr >= 0.55 else
          "FAIL (<0.55) -> retire, record as negative")
    json.dump({"model": model_path, "n": n, "w": w, "l": l, "d": d, "errors": e, "winrate": wr},
              open(os.path.join(HERE, f"gate_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
