"""Value-head AUC on OTHER archetypes' seats -- the metric exp083m actually targets.

pretrain.py's own eval cannot report this. It reads files in sorted order and stops
at max_val=200000, and "mix28..." sorts before "seat28...", so the Grimmsnarl corpus
alone fills the quota and the seat records are never scored.

The question: MCTS calls the net at opponent nodes, i.e. it asks "how is this
position going for the player to move" when that player is piloting Alakazam /
Crustle / Lucario. No such position was ever in the training data (build_multi.py
only kept seats playing OUR archetype), and the value head is what search consumes
(zeroing it drops self-play strength to 0.308). exp083m added those seats as
value-only records; this measures whether that worked, on held-out games.

Run it on the OLD net too -- the number is only meaningful as a difference.

Usage: uv run python eval_seat_auc.py <model.pth> [<model2.pth> ...] [--max-val 60000]
"""
from __future__ import annotations
import glob
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import pretrain as P  # noqa: E402

DATA = os.path.join(WS, "exp080_bc", "data")
CORPORA = {"own": [os.path.join(DATA, "mix28v3wl_multi_w7.pkl")],
           "other": sorted(glob.glob(os.path.join(DATA, "seat28*_multi_w7.pkl")))}


def auc(pairs):
    pairs = sorted(pairs)
    pos = sum(l for _, l in pairs)
    neg = len(pairs) - pos
    if not pos or not neg:
        return None
    rank_sum = sum(j + 1 for j, (_, l) in enumerate(pairs) if l)
    return (rank_sum - pos * (pos + 1) / 2) / (pos * neg)


@torch.no_grad()
def score(model, files, device, max_val, batch_size=256):
    """Held-out records only (same is_val hash as training), value head vs outcome."""
    val, game_maxturn = [], {}
    for wid, fid, chunk, _pw, _vw in P.iter_chunks(files):
        for r in chunk:
            if P.is_val(wid, r[P.GID]):
                key = (fid, r[P.GID])
                game_maxturn[key] = max(game_maxturn.get(key, 0), r[P.TURN])
                val.append((fid, r))
        if len(val) >= max_val:
            break            # chunk boundary, so no game's maxturn is truncated
    buckets = defaultdict(list)
    for i in range(0, len(val), batch_size):
        part = val[i:i + batch_size]
        # opp_drop=1.0 = the oracle-free condition the shipped agent runs in
        t = P.make_batch([r for _, r in part], device, opp_drop=1.0)
        oe, _od = model(*t[:6])
        for (fid, r), v in zip(part, oe.view(-1).tolist()):
            mx = max(game_maxturn[(fid, r[P.GID])], 1)
            buckets[min(int(4 * r[P.TURN] / mx), 3)].append((v, 1 if r[P.OUT] > 0 else 0))
            buckets["all"].append((v, 1 if r[P.OUT] > 0 else 0))
    out = {"n": len(val), "all": auc(buckets["all"])}
    out.update({f"q{b+1}": auc(buckets[b]) for b in range(4) if buckets[b]})
    return out


def load(pth, device):
    cfg = json.load(open(os.path.join(os.path.dirname(pth), "arch.json")))
    v = int(cfg.get("enc_version", 1))
    tm.ENC_V3 = 1 if v >= 3 else 0
    tm.ENC_V4 = 1 if v >= 4 else 0
    tm.num_words_encoder = 28 if v >= 4 else (26 if v >= 3 else 25)
    tm.encoder_size = 38000 if v >= 4 else (34000 if v >= 3 else 24000)
    m = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                   cfg["enc_layers"], cfg["dec_layers"]).to(device)
    m.load_state_dict(torch.load(pth, map_location=device))
    m.eval()
    return m


def main():
    paths = [a for a in sys.argv[1:] if a.endswith(".pth")]
    max_val = int(sys.argv[sys.argv.index("--max-val") + 1]) if "--max-val" in sys.argv else 60000
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    rows = {}
    for pth in paths:
        model = load(pth, device)
        name = os.path.basename(os.path.dirname(pth))
        rows[name] = {}
        for seat, files in CORPORA.items():
            r = score(model, files, device, max_val)
            rows[name][seat] = r
            cols = "  ".join(f"{k} {r[k]:.4f}" for k in ("all", "q1", "q2", "q3", "q4")
                             if r.get(k) is not None)
            print(f"{name:<16} {seat:<6} n={r['n']:<7} {cols}", flush=True)
    json.dump(rows, open(os.path.join(HERE, "results", "seat_auc.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
