"""exp041 Phase 2 decisive gate -- play the RAW pretrained net (policy argmax,
NO search) against the established 5-matchup field and compare to the pilot
(v014 turnbeam) it was cloned from.

This is the experiment that decides the whole line (SESSION_NOTES 原因5):
- raw net ~ pilot  => the official architecture CAN represent our heuristic;
  proceed to Phase 3 (MCTS on top).
- raw net << pilot => decisive representation negative with unlimited
  same-deck data (kills the neural line cheaply, unlike exp022's confounded
  2752-decision cross-expert attempt).

Reference pilot baselines (v014, n=200, exp035): crustle 0.905 ex_lucario 0.77
dragapult 0.17 archaludon 0.195 mirror 0.585 (total 2.67).

Usage: uv run python eval_raw.py results/pre1/model_ep2.pth --n 50
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))  # PrizeTracker (ENC_V2)

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
from teacher_pool import build_teacher_pool  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402


def make_raw_agent(model, my_deck, opp_deck, oracle_free=False):
    """argmax(policy head) over the official candidate enumeration; no MCTS.
    oracle_free=True feeds opp_deck=None (ship-relevant condition: exp041's A2
    re-pretrain trained with opp_deck-word dropout so this should barely move).
    Under ENC_V2 (exp046) the closure keeps per-game trackers (revenge window +
    PrizeTracker) -- a fresh agent is built per game so they reset naturally."""
    fed_opp_deck = None if oracle_free else opp_deck
    if tm.ENC_V2:
        from prize_tracker import PrizeTracker
        ptrack = PrizeTracker(my_deck)
        rev = {"turn": None, "last_opp": None, "window": False}
    else:
        ptrack = None

    def agent(obs_dict):
        oc = to_observation_class(obs_dict)
        cands = tm.enumerate_candidates(oc)
        extra = None
        if ptrack is not None:
            ptrack.update(oc)
            yi = oc.current.yourIndex
            t = oc.current.turn
            cur_opp = len(oc.current.players[1 - yi].prize)
            if t != rev["turn"]:
                rev["window"] = rev["last_opp"] is not None and cur_opp < rev["last_opp"]
                rev["last_opp"] = cur_opp
                rev["turn"] = t
            extra = {"window": rev["window"], "prized": ptrack.prized()}
        if len(cands) == 1:
            return cands[0]
        sv_e = tm.get_encoder_input(oc, my_deck, fed_opp_deck, extra=extra)
        sv_d = tm.get_decoder_input(oc, cands)
        _, policy = tm.eval_nn(sv_e, sv_d, model)
        best = max(range(len(cands)), key=lambda i: policy[i])
        return cands[best]
    return agent


def run_matchup(model, my_deck, opp_deck, opp_factory, n_games, agent_factory=None):
    """`agent_factory(model, my_deck, opp_deck) -> agent`; defaults to the raw
    argmax net. eval_mcts.py passes an MCTS factory for the same game loop."""
    if agent_factory is None:
        agent_factory = make_raw_agent
    wins = losses = draws = errors = 0
    for g in range(n_games):
        my_seat = g % 2
        decks = [None, None]
        decks[my_seat] = my_deck
        decks[1 - my_seat] = list(opp_deck)
        agent = agent_factory(model, my_deck, list(opp_deck))
        opp = opp_factory(list(opp_deck))
        try:
            obs, sd = battle_start(decks[0], decks[1])
            while obs["current"]["result"] < 0:
                if obs["current"]["yourIndex"] == my_seat:
                    sel = agent(obs)
                else:
                    sel = opp(obs)
                obs = battle_select(sel)
            battle_finish()
            r = obs["current"]["result"]
            if r == my_seat:
                wins += 1
            elif r == 1 - my_seat:
                losses += 1
            else:
                draws += 1
        except Exception as e:
            errors += 1
            print(f"  game {g} error: {e!r}", flush=True)
            try:  # leave the engine clean for the next battle_start
                battle_finish()
            except Exception:
                pass
    return wins, losses, draws, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model_path")
    ap.add_argument("--n", type=int, default=50)
    ap.add_argument("--d-model", type=int, default=128)
    ap.add_argument("--oracle-free", action="store_true",
                    help="feed opp_deck=None (ship-relevant; needs opp_drop-trained model)")
    ap.add_argument("--only", default="",
                    help="comma-separated matchup names to evaluate (default: all)")
    args = ap.parse_args()
    only = {s for s in args.only.split(",") if s}

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(args.d_model, 2, args.d_model * 2, 1, 1).to(device)
    model.load_state_dict(torch.load(args.model_path, map_location=device))
    model.eval()

    my_deck = tm.load_deck("charmq")
    # pilot_ref = the pilot's winrates measured under the SAME conditions as
    # this eval (datagen_bc bulk, 39,858 games, fresh agent per game, direct
    # battle_start loop) -- the apples-to-apples clone target. For context,
    # v014's exp035 n=200 harness numbers were crustle .905 / ex .77 /
    # drag .17 / arch .195 / mirror .585 (total 2.67).
    pilot_ref = {"crustle": 0.827, "ex_lucario": 0.775, "dragapult": 0.160,
                 "archaludon": 0.158, "mirror_revenge": 0.576,
                 # grimmsnarl (new ladder-#1 deck, added 2026-07-10): v014
                 # turnbeam measured 0.600 vs the generic-piloted clone at
                 # n=100; datagen smoke was 7/10. Treat 0.60 as the ref.
                 "grimmsnarl": 0.600}
    out = {}
    t0 = time.time()
    for name, opp_deck, factory, _ in build_teacher_pool(my_deck):
        if name not in pilot_ref or (only and name not in only):
            continue
        af = (lambda m, md, od: make_raw_agent(m, md, od, oracle_free=args.oracle_free))
        w, l, d, e = run_matchup(model, my_deck, opp_deck, factory, args.n, agent_factory=af)
        wr = w / max(w + l + d, 1)
        out[name] = {"wr": round(wr, 3), "record": f"{w}-{l}-{d}", "errors": e,
                     "pilot_ref": pilot_ref[name]}
        print(f"{name:15s} raw={wr:.3f} ({w}-{l}-{d}, err={e}) pilot_ref={pilot_ref[name]}",
              flush=True)
    total = sum(v["wr"] for v in out.values())
    print(f"TOTAL raw={total:.3f} pilot_ref={sum(pilot_ref.values()):.3f} "
          f"({time.time()-t0:.0f}s)")
    json.dump(out, open(os.path.join(os.path.dirname(args.model_path),
                                     "eval_raw.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
