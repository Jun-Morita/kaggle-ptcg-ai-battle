"""exp083c gate 2, cross-encoder version: sc083_v3s (ENC_V3, 26 words, vocab
34000) vs sc083_deep (v1, 25 words, vocab 24000).

The two nets do not merely have different weights -- they consume DIFFERENT
INPUT FEATURES, and train_mcts exposes the feature version as module globals
(ENC_V3 / num_words_encoder / encoder_size) that MyModel and get_encoder_input
read at call time. So a normal head-to-head silently feeds one net the other's
features (or fails to even load). Here each side is wrapped so the globals are
switched to ITS version around both feature construction and forward.

Both nets are otherwise identical d128/h4/enc2+dec2, raw argmax, oracle-free,
seats alternated -- so this measures exactly the exp083c changes (ENC_V3
features + lost games in the corpus + margin policy loss).

Usage: uv run python eval_cross.py [--n 400]
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp019_finisher"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
from cg.api import to_observation_class  # noqa: E402

V3 = os.path.join(WS, "exp041_pilotnet", "results", "sc083_v3s", "model_ep15.pth")
DEEP = os.path.join(WS, "exp041_pilotnet", "results", "sc083_deep", "model_ep23.pth")
DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")


@contextlib.contextmanager
def enc_version(v3):
    """Swap train_mcts' feature-version globals for the duration of a call."""
    old = (tm.ENC_V3, tm.num_words_encoder, tm.encoder_size)
    tm.ENC_V3 = 1 if v3 else 0
    tm.num_words_encoder = 26 if v3 else 25
    tm.encoder_size = 34000 if v3 else 24000
    try:
        yield
    finally:
        tm.ENC_V3, tm.num_words_encoder, tm.encoder_size = old


def load(pth, device):
    cfg = json.load(open(os.path.join(os.path.dirname(pth), "arch.json")))
    v3 = cfg.get("enc_version", 1) >= 3
    with enc_version(v3):
        m = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
        m.load_state_dict(torch.load(pth, map_location=device))
    m.eval()
    return m, v3, cfg


def make_agent(model, v3, my_deck):
    """Raw argmax, oracle-free, pinned to this net's own feature version."""
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
    n = int(sys.argv[sys.argv.index("--n") + 1]) if "--n" in sys.argv else 400
    deck = json.load(open(DECK))
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    new, v3n, cfgn = load(V3, device)
    old, v3o, cfgo = load(DEEP, device)
    print(f"NEW sc083_v3s  enc_v3={v3n}  {cfgn}")
    print(f"OLD sc083_deep enc_v3={v3o}  {cfgo}")
    print(f"raw argmax, oracle-free, seats alternated, n={n}\n", flush=True)

    t0 = time.time()
    w, l, d, e = ER.run_matchup(
        new, deck, deck, lambda dk: make_agent(old, v3o, dk), n,
        agent_factory=lambda _m, my, _o: make_agent(new, v3n, my))
    played = w + l + d
    wr = w / played if played else 0.0
    z = (wr - 0.5) / ((0.25 / played) ** 0.5) if played else 0.0
    print(f"v3s vs deep: {w}-{l}-{d}  errors={e}  v3s_winrate={wr:.3f}  z={z:+.2f}  "
          f"({time.time()-t0:.0f}s)")
    print("VERDICT:", "PASS -- the exp083c fixes bought real strength" if wr >= 0.55
          else ("FLAT -- fixes did not convert to strength" if wr >= 0.45
                else "NEGATIVE -- v3s is worse than deep"))
    json.dump({"new": V3, "old": DEEP, "n": n, "w": w, "l": l, "d": d, "errors": e,
               "winrate": wr, "z": z},
              open(os.path.join(HERE, "results", f"v3s_vs_deep_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
