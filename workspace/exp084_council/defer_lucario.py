"""Does deferring damage placement to the 911.3 agent fix the lucario_v2 hole?

diff_lucario.py found that against Mega Lucario ex we disagree with the reference
on 75.5% of DAMAGE_COUNTER decisions and 50.8% of DAMAGE decisions -- and "damage
transfer control" is the reference notebook's own headline mechanic. Disagreement
alone is not evidence we are wrong, so this asks the causal question directly:

    we drive the game against lucario_v2, except at decisions whose SelectContext
    is in --defer, where we play the reference agent's choice instead.

Baseline is ours (~0.475 at n=40); the reference scores 0.600 in the same cell.
If deferring damage placement moves us toward 0.600, that is the patch. If it does
not, the gap is elsewhere and we stop here rather than hand-writing a rule on the
strength of a disagreement count.

Unlike the mirror version of this experiment (defer_ref.py, where every context
left the 0.325 baseline flat or worse), this cell has real headroom.

The reference is consulted on EVERY decision even when ignored: it keeps cross-turn
ledgers and starving them would degrade its later advice.

--defer all is the control: the reference driving our seat should reproduce ~0.600.

Usage: ENC_V3=1 uv run python defer_lucario.py <model.pth> [n] --defer DAMAGE_COUNTER
"""
from __future__ import annotations
import json
import os
import sys
import time

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

LEGACY = {"d_model": 128, "heads": 2, "enc_layers": 1, "dec_layers": 1, "d_ff": 256}
CTX_ID = {m.name: int(m.value) for m in SelectContext}
BASE = 0.475


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 200)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    spec = sys.argv[sys.argv.index("--defer") + 1] if "--defer" in sys.argv else ""
    tm.FINAL_PICK = "visit_q"
    defer = None if spec == "all" else ({CTX_ID[s] for s in spec.split(",")} if spec else set())

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
    print(f"defer_lucario: defer={spec or 'none (baseline)'} n={n} sc={sc}", flush=True)

    w = l = dr = err = used = 0
    t0 = time.time()
    for g in range(n):
        seat = g % 2
        ours = mk(model, list(grimm), list(AC.LUCARIO_DECK))
        opp = AC.make_agent(AC.LUCARIO_DECK)
        advisor = make_ref_agent()
        try:
            obs, _ = battle_start(list(grimm), list(AC.LUCARIO_DECK)) if seat == 0 \
                else battle_start(list(AC.LUCARIO_DECK), list(grimm))
            while obs["current"]["result"] < 0:
                if obs["current"]["yourIndex"] == seat:
                    oc = to_observation_class(obs)
                    ctx = int(getattr(oc.select, "context", -1) or -1) \
                        if oc.select is not None else -1
                    advice = advisor(obs)
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
                dr += 1
        except Exception as e:
            err += 1
            print(f"  game {g} error: {e!r}", flush=True)
            try:
                battle_finish()
            except Exception:
                pass
        if (g + 1) % 25 == 0:
            print(f"  {g+1}/{n}  {w}-{l}-{dr}  ({time.time()-t0:.0f}s)", flush=True)

    played = max(1, w + l + dr)
    wr = w / played
    z = (wr - BASE) / ((BASE * (1 - BASE) / played) ** 0.5)
    print(f"\n  defer={spec or 'none'}  {w}-{l}-{dr}  wr {wr:.3f}  "
          f"z-vs-base({BASE}) {z:+.2f}  deferred {used}  err {err}  "
          f"({time.time()-t0:.0f}s)")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"model": pth, "defer": spec, "n": n, "w": w, "l": l, "d": dr,
               "err": err, "wr": wr, "deferred_decisions": used},
              open(os.path.join(HERE, "results",
                                f"deferluca_{(spec or 'baseline').replace(',', '_')}_n{n}.json"),
                   "w"), indent=1)


if __name__ == "__main__":
    main()
