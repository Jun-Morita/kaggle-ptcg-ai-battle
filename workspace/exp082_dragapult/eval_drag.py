"""exp082 -- evaluate the adopted skarin/Phantom-Dive dragapult agent (public,
OSI, attribution: skarin/phantom-dive-or-go-home-a-dragapult-ex-deck; ladder
proof SK Arin #735 = 827.5, above our koff 766 / alakazam 789) on OUR harness,
independently -- the author's matchup table contradicts our systematic silver-band
matrix (author claims 81% vs wall; our matrix has dragapult vs crustle 0.468), so
trust the harness, not the notebook.

dragapult is the best-positioned silver-band archetype (0.576 overall, 0.553 vs
Alakazam) per exp081's matchup_matrix. This checks whether skarin's PILOT realizes
that, head-to-head vs the strongest pilots we can field:
  - pub-alakazam on its Alakazam deck  = the anti-Alakazam target (real pilot)
  - koff on its LO deck                = head-to-head vs our current build
  - BC-net on Grimmsnarl               = (weak pilot, directional only)

Seat-alternated, fresh agent instances per game, error count = crash-safety check.

Usage: uv run python eval_drag.py [n] [opp]   opp in {koff,alakazam,grimm,all}
"""
from __future__ import annotations
import os, sys, json, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB  # noqa
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine  # noqa
load_engine()

from cg.api import to_observation_class  # noqa
from cg.game import battle_start, battle_finish, battle_select  # noqa

DRAG_DIR = os.environ.get("DRAG_DIR", os.path.join(HERE, "build_drag"))
KOFF_DIR = os.path.join(WS, "exp071_bundlefix", "build")
PUB_DIR = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]


def _load_module_agent(d, deck):
    """Generic: load main.py from dir d, force its deck, return (agent, deck)."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"m82_{_n[0]}", os.path.join(d, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(d)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if hasattr(mod, "read_deck_csv"):
        mod.read_deck_csv = lambda: list(deck)
    mod.my_deck = list(deck)
    return mod.agent


def read_deck(d):
    with open(os.path.join(d, "deck.csv")) as f:
        return [int(x) for x in f.read().splitlines()[:60]]


def make_drag(deck):
    return _load_module_agent(DRAG_DIR, deck)


def make_koff(deck):
    return _load_module_agent(KOFF_DIR, deck)


def make_pub(deck):
    return _load_module_agent(PUB_DIR, deck)


def run(a_factory, a_deck, b_factory, b_deck, n, label):
    """a = dragapult (seat-alternated). Returns a's winrate."""
    aw = bw = dr = err = 0
    t0 = time.time()
    for g in range(n):
        a_seat = g % 2
        decks = [None, None]
        decks[a_seat] = list(a_deck)
        decks[1 - a_seat] = list(b_deck)
        A = a_factory(list(a_deck))
        B = b_factory(list(b_deck))
        try:
            obs, sd = battle_start(decks[0], decks[1])
            while obs["current"]["result"] < 0:
                sel = A(obs) if obs["current"]["yourIndex"] == a_seat else B(obs)
                obs = battle_select(sel)
            battle_finish()
            r = obs["current"]["result"]
            if r == a_seat: aw += 1
            elif r == 1 - a_seat: bw += 1
            else: dr += 1
        except Exception as e:
            err += 1
            print(f"  {label} game {g} error: {e!r}", flush=True)
            try: battle_finish()
            except Exception: pass
    played = aw + bw + dr
    wr = aw / played if played else 0.0
    print(f"  dragapult vs {label:10} {aw}-{bw}-{dr}  err={err}  drag_wr={wr:.3f}  ({time.time()-t0:.0f}s)", flush=True)
    return wr, aw, bw, dr, err


def main():
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 100)
    which = next((a for a in sys.argv[1:] if a in ("koff", "alakazam", "grimm", "all")), "all")
    drag_deck = read_deck(DRAG_DIR)
    koff_deck = read_deck(KOFF_DIR)
    alak_deck = read_deck(PUB_DIR) if os.path.exists(os.path.join(PUB_DIR, "deck.csv")) else None

    print(f"EVAL skarin-dragapult (adopted)  n={n}  opp={which}", flush=True)
    out = {}
    if which in ("koff", "all"):
        out["koff"] = run(make_drag, drag_deck, make_koff, koff_deck, n, "koff(LO)")
    if which in ("alakazam", "all") and alak_deck:
        out["alakazam"] = run(make_drag, drag_deck, make_pub, alak_deck, n, "pub-alakazam")
    json.dump(out, open(os.path.join(HERE, "eval_drag.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
