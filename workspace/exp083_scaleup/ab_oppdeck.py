"""Does the search's wrong guess about the opponent's DECK cost us anything?

main.py ships this line:

    sel = mcts_agent(obs_dict, my_deck, MODEL, _sc, opp_deck=my_deck)

so determinize() draws the opponent's hidden hand / deck / prizes out of OUR
Grimmsnarl list, in every game. Grimmsnarl is 46.5% of the ladder (disc730823),
so in a bit over half of our games the search is simulating an opponent holding
cards they do not own. The net is not misled -- the encoder is oracle-free, the
opp_deck word is fed as None -- only the search's world model is.

This measures the ceiling before building any inference: give the agent the TRUE
opponent deck and see what it is worth, per archetype. If the oracle is worth
nothing the lane closes today; if it is worth something, the deck still has to be
inferred from observed cards at run time, so treat the oracle as an upper bound.

The mirror is skipped on purpose: there my_deck IS the opponent's deck, so the two
conditions are identical by construction.

Usage: ENC_V3=1 uv run python ab_oppdeck.py <model.pth> [n] [--only mixed_ex1]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import torch  # noqa: E402
import gate_field as GF  # noqa: E402  (loads the engine, sys.path, tm, ER, ...)
from gate_field import ER, enc_version  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402

SKIP = {"mixed_ex3"}  # the mirror: oracle and baseline are the same thing


def make_agent(model, v, my_deck, opp_deck, sc):
    """opp_deck is what determinize() samples the hidden cards from."""
    mk = make_mcts_agent_factory(sc, oracle_free=True)

    def agent(obs_dict):
        with enc_version(v):
            return mk(model, my_deck, opp_deck)(obs_dict)
    return agent


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 120)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, v, _cfg, _p = GF.load(pth, device)
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    opp_decks = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
    opps = [o for o in GF.opponents(grimm, opp_decks)
            if o[0] not in SKIP and (only is None or o[0] == only)]

    print(f"oppdeck oracle: {os.path.relpath(pth, WS)} sc={sc} n={n}\n", flush=True)
    out = {}
    for k, odeck, fac in opps:
        row = {}
        for cond in ("oracle", "mirror_assumption"):
            t0 = time.time()
            w, l, d, e = ER.run_matchup(
                model, grimm, odeck, fac, n,
                agent_factory=(
                    (lambda _m, my, opp: make_agent(model, v, my, opp, sc))
                    if cond == "oracle" else
                    (lambda _m, my, _o: make_agent(model, v, my, my, sc))))
            played = max(1, w + l + d)
            row[cond] = {"wr": w / played, "w": w, "l": l, "d": d, "err": e}
            print(f"  {GF.LABEL[k]:<20} {cond:<18} {w/played:.3f}  ({w}-{l}-{d}, "
                  f"err={e})  ({time.time()-t0:.0f}s)", flush=True)
        delta = row["oracle"]["wr"] - row["mirror_assumption"]["wr"]
        se = (2 * 0.25 / max(1, n)) ** 0.5
        row["delta"] = delta
        row["weight"] = GF.WEIGHT[k]
        print(f"  {GF.LABEL[k]:<20} delta {delta:+.3f}  (se {se:.3f}, "
              f"weight {GF.WEIGHT[k]:.2f})\n", flush=True)
        out[k] = row

    wsum = sum(GF.WEIGHT[k] for k in out)
    gain = sum(GF.WEIGHT[k] * out[k]["delta"] for k in out)
    print(f"weighted delta over the non-mirror {wsum:.2f} of the field: {gain:+.4f}")
    print(f"(as a share of the whole field, mirror included: "
          f"{gain / sum(GF.WEIGHT.values()):+.4f})")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    tag = only or "all"
    json.dump({"model": pth, "sc": sc, "n": n, "rows": out, "weighted_delta": gain},
              open(os.path.join(HERE, "results", f"ab_oppdeck_{tag}_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
