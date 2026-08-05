"""Which decisions actually cost us the 66 points? Defer one context at a time.

We lose to the public 911.3 agent 0.325 (39-81, z=-3.83) with an identical deck,
so the whole gap is piloting. diff_ref.py says WHERE we choose differently; it
cannot say where being different is expensive. This does:

    our agent drives the game, except at decisions whose SelectContext is in
    --defer, where we play the reference agent's choice instead.

Baseline 0.325 -> 0.5 means that context alone held the gap. Baseline unchanged
means we already play it as well as they do, however much we disagree there.

The reference agent is consulted on EVERY decision even when we ignore its answer:
it keeps cross-turn ledgers, and starving them would make its later advice worse
than the agent we are trying to measure.

--defer all is the control. It should land near 0.5 (their policy driving both
seats); anything else means the deferral harness itself is broken -- worth knowing
before reading a single per-context number.

Usage: ENC_V3=1 uv run python defer_ref.py <model.pth> [n] --defer TO_HAND[,ATTACH_TO]
"""
from __future__ import annotations
import json
import os
import sys
import time

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
CTX_ID = {m.name: int(m.value) for m in SelectContext}


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 120)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    spec = sys.argv[sys.argv.index("--defer") + 1] if "--defer" in sys.argv else ""
    tm.FINAL_PICK = "visit_q"
    if spec == "all":
        defer = None                      # every context
    elif spec:
        defer = {CTX_ID[s] for s in spec.split(",")}
    else:
        defer = set()                     # baseline

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
    print(f"defer_ref: defer={spec or 'none (baseline)'} n={n} sc={sc}", flush=True)

    w = l = d = err = 0
    used = 0
    t0 = time.time()
    for g in range(n):
        seat = g % 2
        ours = mk(model, list(DECK), list(DECK))
        opp = make_ref_agent()
        advisor = make_ref_agent()
        try:
            obs, _ = battle_start(list(DECK), list(DECK))
            while obs["current"]["result"] < 0:
                if obs["current"]["yourIndex"] == seat:
                    oc = to_observation_class(obs)
                    ctx = int(getattr(oc.select, "context", -1) or -1) \
                        if oc.select is not None else -1
                    advice = advisor(obs)          # always consulted: keeps its ledgers live
                    if defer is None or ctx in defer:
                        sel = advice
                        used += 1
                    else:
                        sel = ours(obs)
                else:
                    sel = opp(obs)
                obs = battle_select(sel)
            r = obs["current"]["result"]
            battle_finish()
            if r == seat:
                w += 1
            elif r == 1 - seat:
                l += 1
            else:
                d += 1
        except Exception as e:
            err += 1
            print(f"  game {g} error: {e!r}", flush=True)
            try:
                battle_finish()
            except Exception:
                pass
        if (g + 1) % 20 == 0:
            print(f"  {g+1}/{n}  {w}-{l}-{d}  ({time.time()-t0:.0f}s)", flush=True)

    played = max(1, w + l + d)
    wr = w / played
    z = (wr - 0.325) / ((0.325 * 0.675 / played) ** 0.5)
    print(f"\n  defer={spec or 'none'}  {w}-{l}-{d}  wr {wr:.3f}  "
          f"z-vs-baseline(0.325) {z:+.2f}  deferred-decisions {used}  err {err}  "
          f"({time.time()-t0:.0f}s)")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    tag = (spec or "baseline").replace(",", "_")
    json.dump({"model": pth, "defer": spec, "n": n, "w": w, "l": l, "d": d,
               "err": err, "wr": wr, "deferred_decisions": used},
              open(os.path.join(HERE, "results", f"defer_{tag}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
