"""exp083e: generate AlphaZero-style training targets by SEARCHING with the
current shipped net.

Why this is worth doing now and was not before: the improvement operator is
measured. On this exact net, self-mirror MCTS(sc16) vs raw argmax = 0.825
(z=+5.81). So search IS a stronger policy than the net that guides it, and
training the net toward search's own value/advantage estimates is the classic
policy-improvement step. exp080 killed this lane on the grounds that "search
makes it worse" (0.300, z=-3.10) -- but that measurement was taken with a value
head trained on a won-games-only corpus, i.e. a constant (stdev 2e-5). The
premise is dead; the loop is worth one iteration.

train_mcts.selfplay() already returns LearnSamples carrying exactly the targets
we want: root value blended back through the game (TD-ish, LAMBDA=0.9) and a
per-candidate advantage vector clipped to [-1,1] -- the same tanh/Huber shape
the policy head is already trained against. This script only has to convert
them into the 12(+1)-tuple record layout pretrain.py consumes and chunk them to
disk. Element 12 (the soft search policy) is the new part; records without it
keep the old one-hot behaviour.

Usage: ENC_V3=1 uv run python selfplay_gen.py [--games 600] [--sc 16] [--out data/sp_v3s_w0.pkl]
"""
from __future__ import annotations
import json, os, pickle, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402

NET = os.path.join(WS, "exp041_pilotnet", "results", "sc083_v3s", "model_ep15.pth")
DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")


def arg(flag, default, cast=int):
    return cast(sys.argv[sys.argv.index(flag) + 1]) if flag in sys.argv else default


def to_record(sample, gid):
    """LearnSample -> pretrain.py's record layout, plus element 12 = soft policy."""
    e, d = sample.sv_enc, sample.sv_dec
    pol = list(sample.policy)
    nc = len(pol)
    chosen = max(range(nc), key=lambda i: pol[i]) if nc else 0
    return (list(e.index), list(e.value), list(e.offset),
            list(d.index), list(d.value), list(d.offset),
            nc, chosen, 0, float(sample.value), "selfplay", gid, pol)


def main():
    games = arg("--games", 600)
    sc = arg("--sc", 16)
    out = os.path.join(WS, "exp080_bc", "data",
                       sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv
                       else "sp_v3s_w0.pkl")
    cfg = json.load(open(os.path.join(os.path.dirname(NET), "arch.json")))
    assert tm.ENC_V3 == 1, "set ENC_V3=1 -- the net was trained on v3 features"

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
    model.load_state_dict(torch.load(NET, map_location=device))
    model.eval()
    deck = json.load(open(DECK))
    print(f"selfplay: net={os.path.basename(NET)} {cfg} sc={sc} games={games}\n"
          f"out={out}", flush=True)

    t0, done, chunk = time.time(), 0, []
    with open(out, "wb") as f:
        while done < games:
            batch = min(10, games - done)
            with torch.no_grad():
                samples = tm.selfplay(deck, model, sc, batch)
            for s in samples:
                chunk.append(to_record(s, done))
            done += batch
            if len(chunk) >= 20000:
                pickle.dump(chunk, f, protocol=4); chunk = []
            el = time.time() - t0
            print(f"  games {done}/{games}  records~{done and len(chunk)}  "
                  f"{el/done:.1f}s/game  eta {(games-done)*el/done/60:.0f}min", flush=True)
        if chunk:
            pickle.dump(chunk, f, protocol=4)
    print(f"done in {(time.time()-t0)/60:.1f}min -> {out} "
          f"({os.path.getsize(out)/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
