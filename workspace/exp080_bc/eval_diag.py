"""exp081 -- koff (LO/mill) vs our BC net piloting Grimmsnarl (mixed_ex3),
the one fresh, well-motivated improvement target: koff's ladder matchup vs
Grimmsnarl is 0.29 (2-5) and Grimmsnarl is 43% (rising) of the upper band --
koff's climb-cap toward silver, and the ONLY matchup koff was never tuned for
(Grimmsnarl is new to the meta; past NO-GOs were vs old Lucario/Crustle).

The BC net (mirror 0.91 vs pub1034) is our strongest available Grimmsnarl
sparring partner -- pub1034 off-deck systematically over-estimates, so we use
the imitation net instead. Absolute winrate is a LOWER bound on koff's real
difficulty (the net is pure-argmax, weaker than real top pilots); the real
value is the LOSS-MODE split: does koff lose a prize RACE (Grimmsnarl takes 6
prizes before koff mills = structural, deck problem) or does koff fail to close
the mill it should (patchable gated-decision leak)?

Seat is alternated. koff is loaded fresh per game (no cross-game global state).

Usage: uv run python eval_diag.py [n]           (default 100)
"""
from __future__ import annotations
import os, sys, json, time, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402

KOFF_DIR = os.path.join(WS, "exp071_bundlefix", "build")
_n = [0]


def load_koff_deck():
    with open(os.path.join(KOFF_DIR, "deck.csv")) as f:
        return [int(x) for x in f.read().splitlines()[:60]]


def make_koff(deck):
    """Fresh koff agent instance piloting `deck` (no shared module globals)."""
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"koff81_{_n[0]}", os.path.join(KOFF_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.read_deck_csv = lambda: list(deck)
    mod.my_deck = list(deck)
    return mod.agent


def snapshot(obs_dict):
    """(turn, deckCount[0], deckCount[1], prizes_left[0], prizes_left[1]) or None."""
    try:
        o = to_observation_class(obs_dict)
        cur = o.current
        ps = cur.players
        return (cur.turn, ps[0].deckCount, ps[1].deckCount, len(ps[0].prize), len(ps[1].prize))
    except Exception:
        return None


def main():
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 100)
    grimm = json.load(open(os.path.join(HERE, "grimmsnarl_deck.json")))
    koff_deck = load_koff_deck()

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model_path = os.path.join(WS, "exp041_pilotnet", "results", "pre_grimm10", "model_ep2.pth")
    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    print(f"DIAG  koff(LO) vs BC-net(Grimmsnarl, oracle-free)  n={n}  net={os.path.basename(model_path)}", flush=True)
    t0 = time.time()
    # net seat = Grimmsnarl (my_deck), koff = opp
    koff_w = net_w = draws = errors = 0
    games = []  # per game: {winner, last snapshot, seat}
    for g in range(n):
        net_seat = g % 2
        koff_seat = 1 - net_seat
        decks = [None, None]
        decks[net_seat] = grimm
        decks[koff_seat] = list(koff_deck)
        net_agent = ER.make_raw_agent(model, grimm, list(koff_deck), oracle_free=True)
        koff_agent = make_koff(list(koff_deck))
        last = None
        try:
            obs, sd = battle_start(decks[0], decks[1])
            while obs["current"]["result"] < 0:
                snap = snapshot(obs)
                if snap is not None:
                    last = snap
                if obs["current"]["yourIndex"] == net_seat:
                    sel = net_agent(obs)
                else:
                    sel = koff_agent(obs)
                obs = battle_select(sel)
            battle_finish()
            r = obs["current"]["result"]
            if r == koff_seat:
                koff_w += 1; winner = "koff"
            elif r == net_seat:
                net_w += 1; winner = "net"
            else:
                draws += 1; winner = "draw"
            games.append({"winner": winner, "koff_seat": koff_seat, "last": last})
        except Exception as e:
            errors += 1
            print(f"  game {g} error: {e!r}", flush=True)
            try:
                battle_finish()
            except Exception:
                pass
    played = koff_w + net_w + draws
    kr = koff_w / played if played else 0.0
    print(f"\nkoff {koff_w}-{net_w}-{draws}  errors={errors}  koff_winrate={kr:.3f}  ({time.time()-t0:.0f}s)")

    # loss-mode split: at last snapshot, for koff seat, deck sizes and prizes.
    def agg(subset, label):
        rows = [gm for gm in subset if gm["last"]]
        if not rows:
            print(f"  {label}: (no snapshots)"); return
        import statistics as st
        turns = [gm["last"][0] for gm in rows]
        koff_deck_end = [gm["last"][1 + gm["koff_seat"]] for gm in rows]
        net_deck_end = [gm["last"][1 + (1 - gm["koff_seat"])] for gm in rows]
        koff_prize_left = [gm["last"][3 + gm["koff_seat"]] for gm in rows]
        net_prize_left = [gm["last"][3 + (1 - gm["koff_seat"])] for gm in rows]
        print(f"  {label} (n={len(rows)}): turn~{st.median(turns):.0f}  "
              f"koff_deck_end~{st.median(koff_deck_end):.0f}  net_deck_end~{st.median(net_deck_end):.0f}  "
              f"koff_prize_left~{st.median(koff_prize_left):.0f}  net_prize_left~{st.median(net_prize_left):.0f}")

    print("\nLoss-mode split (median of last pre-terminal snapshot):")
    agg([gm for gm in games if gm["winner"] == "koff"], "koff WINS ")
    agg([gm for gm in games if gm["winner"] == "net"], "koff LOSES")
    print("\nInterpretation: koff mills the opp's DECK to 0. If in LOSSES net_deck_end is\n"
          "still high AND net_prize_left is low -> Grimmsnarl won the PRIZE RACE (structural).\n"
          "If net_deck_end is low (koff nearly milled) but koff lost on prizes -> koff was\n"
          "too slow / a closable mill it didn't close (patchable).")
    json.dump({"n": n, "koff_w": koff_w, "net_w": net_w, "draws": draws, "errors": errors,
               "koff_winrate": kr, "games": games},
              open(os.path.join(HERE, "diag_koff_grimm.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
