"""Generic head-to-head gate: any two nets, same deck, raw argmax, oracle-free.

Generalises eval_cross.py (which hardcoded v3s vs deep) so exp083e (SP) and the
15-day rebuild (V15S) can be gated by the same code path. Each side is wrapped in
enc_version() so a net always sees the feature version it was TRAINED on -- the
globals live on train_mcts and are read at call time, so without this a v1 and a
v3 net silently feed each other the wrong features.

Raw argmax on both sides: search is a separate, later gate. If the net itself did
not improve, adding search on top only measures search.

Usage:
  uv run python gate.py --new results/sc083_sp/model_ep3.pth \
                        --old results/sc083_v3s/model_ep15.pth [--n 400]
(paths are relative to exp041_pilotnet/)
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
PILOT = os.path.join(WS, "exp041_pilotnet")
sys.path.insert(0, PILOT)
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402
from cg.api import to_observation_class  # noqa: E402

DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


@contextlib.contextmanager
def enc_version(v3):
    old = (tm.ENC_V3, tm.num_words_encoder, tm.encoder_size)
    tm.ENC_V3 = 1 if v3 else 0
    tm.num_words_encoder = 26 if v3 else 25
    tm.encoder_size = 34000 if v3 else 24000
    try:
        yield
    finally:
        tm.ENC_V3, tm.num_words_encoder, tm.encoder_size = old


def load(pth, device):
    pth = pth if os.path.isabs(pth) else os.path.join(PILOT, pth)
    cfg = json.load(open(os.path.join(os.path.dirname(pth), "arch.json")))
    v3 = cfg.get("enc_version", 1) >= 3
    with enc_version(v3):
        m = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
        m.load_state_dict(torch.load(pth, map_location=device))
    m.eval()
    return m, v3, cfg, pth


def make_agent(model, v3, my_deck, sc=0):
    """sc>0 wraps the net in MCTS -- the SHIP configuration. sc=0 is raw argmax,
    which isolates the net itself (search helps both sides, so it dilutes a net
    comparison while costing ~5x the wall clock)."""
    if sc:
        mk = make_mcts_agent_factory(sc, oracle_free=True)

        def agent_s(obs_dict):
            with enc_version(v3):
                return mk(model, my_deck, my_deck)(obs_dict)
        return agent_s

    def agent(obs_dict):
        oc = to_observation_class(obs_dict)
        cands = tm.enumerate_candidates(oc)
        if len(cands) == 1:
            return cands[0]
        with enc_version(v3):
            sv_e = tm.get_encoder_input(oc, my_deck, None)
            sv_d = tm.get_decoder_input(oc, cands)
            _, policy = tm.eval_nn(sv_e, sv_d, model)
        return cands[max(range(len(cands)), key=lambda i: policy[i])]
    return agent


def main():
    n = int(arg("--n", "400"))
    sc = int(arg("--sc", "0"))
    tag = arg("--tag", "gate")
    deck = json.load(open(DECK))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    new, v3n, cfgn, pn = load(arg("--new"), device)
    old, v3o, cfgo, po = load(arg("--old"), device)
    print(f"NEW {pn}  enc_v3={v3n}  {cfgn}")
    print(f"OLD {po}  enc_v3={v3o}  {cfgo}")
    print(f"{'MCTS sc=%d' % sc if sc else 'raw argmax'}, oracle-free, "
          f"seats alternated, n={n}\n", flush=True)

    t0 = time.time()
    w, l, d, e = ER.run_matchup(
        new, deck, deck, lambda dk: make_agent(old, v3o, dk, sc), n,
        agent_factory=lambda _m, my, _o: make_agent(new, v3n, my, sc))
    played = w + l + d
    wr = w / played if played else 0.0
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"NEW vs OLD: {w}-{l}-{d}  errors={e}  new_winrate={wr:.3f}  z={z:+.2f}  "
          f"({time.time()-t0:.0f}s)")
    print("VERDICT:", "PASS" if wr >= 0.55 else ("FLAT" if wr >= 0.45 else "NEGATIVE"))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"new": pn, "old": po, "n": n, "w": w, "l": l, "d": d, "errors": e,
               "winrate": wr, "z": z},
              open(os.path.join(HERE, "results", f"{tag}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
