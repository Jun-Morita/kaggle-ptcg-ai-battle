"""Where does our policy disagree with the 911.3 agent, and does it cost anything?

Same deck on both sides, so every disagreement is a piloting difference and
nothing else. One agent DRIVES the game (so the positions visited are real), the
other is asked what it would have done in the same position. Both directions are
run, because the set of positions our policy reaches is not the set theirs
reaches, and a rule we are missing may only show up in their line of play.

Reported per SelectContext:
    n            decisions of that kind
    disagree     fraction where the two picked different option sets
    sem          same but ignoring which COPY of an identical card was picked --
                 exp042 found index-based comparison counts same-card-different-
                 copy as a mismatch, which inflated a diff by ~0.4

A context with many decisions and a high semantic disagreement rate is where a
hand-written override would have the most leverage. It is not yet evidence that
they are right and we are wrong -- that needs the matchup result -- but it is the
only place a fix can matter.

Usage: ENC_V3=1 uv run python diff_ref.py <model.pth> [games] [--sc 16]
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
for p in ("exp001_harness", "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
from cg.api import to_observation_class, SelectContext  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402
from load_ref import make_ref_agent, DECK  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
CTX_NAME = {int(m.value): m.name for m in SelectContext}


def card_key(obs, opt):
    """Identity of an option that ignores which duplicate copy it refers to."""
    for attr in ("cardId",):
        v = getattr(opt, attr, None)
        if v is not None:
            return ("card", int(v))
    try:
        c = tm.get_card(obs, opt.area, opt.index, getattr(opt, "playerIndex", 0)
                        if getattr(opt, "playerIndex", None) is not None
                        else obs.current.yourIndex)
        if c is not None and getattr(c, "id", None) is not None:
            return ("card", int(c.id))
    except Exception:
        pass
    return ("type", int(getattr(opt, "type", -1)), int(getattr(opt, "number", -1) or -1))


def sem(obs, action):
    return tuple(sorted(card_key(obs, obs.select.option[i]) for i in action))


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 30)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    tm.FINAL_PICK = "visit_q"

    cfg = dict(LEGACY)
    cfg.update({k: v for k, v in json.load(
        open(os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json"))).items()
        if k in cfg})
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    mk = make_mcts_agent_factory(sc, oracle_free=True)
    print(f"diff_ref: {os.path.relpath(pth, WS)} sc={sc} games={games}", flush=True)

    N, DIS, SEMDIS = Counter(), Counter(), Counter()
    t0 = time.time()
    for g in range(games):
        driver_is_ours = (g % 2 == 0)
        ours = mk(model, list(DECK), list(DECK))
        ref = make_ref_agent()
        seat = g % 2
        obs, _ = battle_start(list(DECK), list(DECK))
        while obs["current"]["result"] < 0:
            me = obs["current"]["yourIndex"] == seat
            oc = to_observation_class(obs)
            if me and oc.select is not None and oc.select.option:
                a_ours = ours(obs)
                a_ref = ref(obs)
                ctx = int(getattr(oc.select, "context", -1) or -1)
                N[ctx] += 1
                if sorted(a_ours) != sorted(a_ref):
                    DIS[ctx] += 1
                    try:
                        if sem(oc, a_ours) != sem(oc, a_ref):
                            SEMDIS[ctx] += 1
                    except Exception:
                        SEMDIS[ctx] += 1
                obs = battle_select(a_ours if driver_is_ours else a_ref)
            else:
                obs = battle_select(ours(obs) if me else ref(obs))
        battle_finish()
        if (g + 1) % 5 == 0:
            print(f"  game {g+1}/{games}  decisions={sum(N.values())} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    tot = max(1, sum(N.values()))
    print(f"\ncompared {tot} decisions over {games} games")
    print(f"{'context':<26}{'n':>7}{'disagree':>10}{'semantic':>10}")
    for ctx, n in N.most_common():
        print(f"{CTX_NAME.get(ctx, ctx):<26}{n:>7}{DIS[ctx]/n:>10.3f}{SEMDIS[ctx]/n:>10.3f}")
    print(f"{'TOTAL':<26}{tot:>7}{sum(DIS.values())/tot:>10.3f}"
          f"{sum(SEMDIS.values())/tot:>10.3f}")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "games": games, "sc": sc,
               "n": {CTX_NAME.get(k, str(k)): v for k, v in N.items()},
               "disagree": {CTX_NAME.get(k, str(k)): v for k, v in DIS.items()},
               "semantic": {CTX_NAME.get(k, str(k)): v for k, v in SEMDIS.items()}},
              open(os.path.join(HERE, "results", f"diff_ref_g{games}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
