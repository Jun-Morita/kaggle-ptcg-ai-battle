"""Where do we and the 911.3 agent diverge AGAINST Mega Lucario ex, and does it cost?

The field gate, run with the reference agent in our seat, says lucario_v2 is our
largest unsaturated hole:

                    ours(v3s)   ref(911.3)
    lucario_v2        0.400       0.600     <- +0.20, the biggest per-cell gap
    Alakazam          0.810       0.900
    Crustle           0.485       0.567
    Archaludon        0.710       0.700
    Grimmsnarl mirror 0.970       0.983     (both pinned)

It matters more than its 3.9% share in the 800-899 band suggests: the public
score-band snapshot puts Mega Lucario at 24-30% in the 500-699 bands, which every
new submission must climb through from mu=600.

This is diff_ref.py with the OPPONENT swapped from the mirror to lucario_v2. We
drive; the reference is asked what it would have done in the same position (and is
consulted on every decision so its cross-turn ledgers stay live). Reported per
SelectContext with the semantic (same-card-different-copy) normalisation.

Usage: ENC_V3=1 uv run python diff_lucario.py <model.pth> [games] [--sc 16]
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
for p in ("exp001_harness", "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher",
          "exp007_anti_crustle", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import anti_crustle as AC  # noqa: E402
from cg.api import to_observation_class, SelectContext  # noqa: E402
from cg.game import battle_start, battle_select, battle_finish  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402
from load_ref import make_ref_agent  # noqa: E402
from diff_ref import card_key, sem  # noqa: E402

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
CTX_NAME = {int(m.value): m.name for m in SelectContext}


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    games = next((int(a) for a in sys.argv[1:] if a.isdigit()), 40)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    tm.FINAL_PICK = "visit_q"

    d = os.path.dirname(os.path.abspath(pth))
    arch = json.load(open(os.path.join(d, "arch.json")))
    cfg = dict(LEGACY)
    cfg.update({k: v for k, v in arch.items() if k in cfg})
    v = int(arch.get("enc_version", 1))
    tm.ENC_V3 = 1 if v >= 3 else 0
    tm.ENC_V4 = 1 if v >= 4 else 0
    tm.num_words_encoder = 28 if v >= 4 else (26 if v >= 3 else 25)
    tm.encoder_size = 38000 if v >= 4 else (34000 if v >= 3 else 24000)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(pth, map_location=device))
    model.eval()
    mk = make_mcts_agent_factory(sc, oracle_free=True)
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    print(f"diff_lucario: {os.path.relpath(pth, WS)} enc_v{v} sc={sc} games={games}",
          flush=True)

    # split by outcome: a divergence that only shows up in games we LOSE is the
    # one worth patching; one spread evenly across wins and losses is style.
    N, DIS, SEM = Counter(), Counter(), Counter()
    NL, SEML = Counter(), Counter()
    w = l = dr = err = 0
    t0 = time.time()
    for g in range(games):
        seat = g % 2
        ours = mk(model, list(grimm), list(AC.LUCARIO_DECK))
        opp = AC.make_agent(AC.LUCARIO_DECK)
        advisor = make_ref_agent()
        per_game = []
        try:
            obs, _ = battle_start(list(grimm), list(AC.LUCARIO_DECK)) if seat == 0 \
                else battle_start(list(AC.LUCARIO_DECK), list(grimm))
            while obs["current"]["result"] < 0:
                if obs["current"]["yourIndex"] == seat:
                    oc = to_observation_class(obs)
                    a_ours = ours(obs)
                    a_ref = advisor(obs)
                    if oc.select is not None and oc.select.option:
                        ctx = int(getattr(oc.select, "context", -1) or -1)
                        N[ctx] += 1
                        if sorted(a_ours) != sorted(a_ref):
                            DIS[ctx] += 1
                            try:
                                bad = sem(oc, a_ours) != sem(oc, a_ref)
                            except Exception:
                                bad = True
                            if bad:
                                SEM[ctx] += 1
                                per_game.append(ctx)
                    obs = battle_select(a_ours)
                else:
                    obs = battle_select(opp(obs))
            r = obs["current"]["result"]
            battle_finish()
            if r == seat:
                w += 1
            elif r == 1 - seat:
                l += 1
                for ctx in per_game:
                    SEML[ctx] += 1
            else:
                dr += 1
        except Exception as e:
            err += 1
            print(f"  game {g} error: {e!r}", flush=True)
            try:
                battle_finish()
            except Exception:
                pass
        if (g + 1) % 10 == 0:
            print(f"  {g+1}/{games}  {w}-{l}-{dr}  decisions={sum(N.values())} "
                  f"({time.time()-t0:.0f}s)", flush=True)

    tot = max(1, sum(N.values()))
    print(f"\nvs lucario_v2: {w}-{l}-{dr} (wr {w/max(1,w+l+dr):.3f}, err {err}); "
          f"{tot} decisions over {games} games")
    print(f"{'context':<26}{'n':>7}{'disagree':>10}{'semantic':>10}{'sem/loss':>10}")
    for ctx, n in N.most_common():
        print(f"{CTX_NAME.get(ctx, ctx):<26}{n:>7}{DIS[ctx]/n:>10.3f}"
              f"{SEM[ctx]/n:>10.3f}{SEML[ctx]:>10}")
    print(f"{'TOTAL':<26}{tot:>7}{sum(DIS.values())/tot:>10.3f}"
          f"{sum(SEM.values())/tot:>10.3f}{sum(SEML.values()):>10}")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "games": games, "sc": sc, "w": w, "l": l, "d": dr,
               "n": {CTX_NAME.get(k, str(k)): v for k, v in N.items()},
               "disagree": {CTX_NAME.get(k, str(k)): v for k, v in DIS.items()},
               "semantic": {CTX_NAME.get(k, str(k)): v for k, v in SEM.items()},
               "semantic_in_losses": {CTX_NAME.get(k, str(k)): v for k, v in SEML.items()}},
              open(os.path.join(HERE, "results", f"diff_lucario_g{games}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
