"""exp041 ship path — pure-numpy inference port of the official MyModel.

The submission sandbox has numpy but no torch (established exp032/033), so the
pretrained transformer must run in numpy. This is a PORT, not a distillation:
same weights, same math, bit-close outputs (parity gate: max|Δ| < 1e-4 and
argmax agreement vs torch on real recorded features).

Export:  uv run python npnet.py export results/pre1b/model_ep2.pth results/pre1b/npnet.npz
Parity:  uv run python npnet.py parity results/pre1b/model_ep2.pth results/pre1b/npnet.npz data/w0_c000.pkl
Speed:   uv run python npnet.py speed results/pre1b/npnet.npz data/w0_c000.pkl

Architecture (train_mcts.py MyModel, d128/h2/ff256, 1 enc + 1 dec layer):
  v = tanh(mean(enc_fc(TransformerEncoderLayer(enc_bag(...)))))
  p = tanh(dec_fc(DecoderLayer(dec_bag(...), enc_out)))
TransformerEncoderLayer is post-norm relu:  x=n1(x+SA(x)); x=n2(x+W2 relu(W1 x)).
DecoderLayer (custom, train_mcts.py):       x=n1(x+CA(x,enc)); x=n2(x+W2 relu(W1 x)).
"""
from __future__ import annotations
import pickle
import sys
import time

import numpy as np

NUM_WORDS_ENCODER = 25
D = 128
H = 2
HD = D // H


# ---- primitives -----------------------------------------------------------------
def layer_norm(x, g, b, eps=1e-5):
    m = x.mean(-1, keepdims=True)
    v = x.var(-1, keepdims=True)
    return (x - m) / np.sqrt(v + eps) * g + b


def softmax(x, axis=-1):
    e = np.exp(x - x.max(axis=axis, keepdims=True))
    return e / e.sum(axis=axis, keepdims=True)


def mha(q_in, kv_in, ipw, ipb, opw, opb):
    """torch MultiheadAttention (batch=1, seq-first collapsed to (S,D))."""
    wq, wk, wv = ipw[:D], ipw[D:2 * D], ipw[2 * D:]
    bq, bk, bv = ipb[:D], ipb[D:2 * D], ipb[2 * D:]
    q = q_in @ wq.T + bq
    k = kv_in @ wk.T + bk
    v = kv_in @ wv.T + bv
    Sq, Sk = q.shape[0], k.shape[0]
    q = q.reshape(Sq, H, HD).transpose(1, 0, 2)          # (H, Sq, HD)
    k = k.reshape(Sk, H, HD).transpose(1, 0, 2)
    v = v.reshape(Sk, H, HD).transpose(1, 0, 2)
    a = softmax(q @ k.transpose(0, 2, 1) / np.sqrt(HD), axis=-1)
    o = (a @ v).transpose(1, 0, 2).reshape(Sq, D)
    return o @ opw.T + opb


def emb_bag(weight, idx, val, off, n_bags):
    """EmbeddingBag(mode=sum) with per_sample_weights, list/array inputs."""
    out = np.zeros((n_bags, D), dtype=np.float64)
    idx = np.asarray(idx, dtype=np.int64)
    val = np.asarray(val, dtype=np.float64)
    off = np.asarray(off, dtype=np.int64)
    ends = np.append(off[1:], len(idx))
    for b in range(n_bags):
        s, e = off[b], ends[b]
        if e > s:
            out[b] = (weight[idx[s:e]] * val[s:e, None]).sum(0)
    return out


# ---- model ------------------------------------------------------------------------
class NpNet:
    def __init__(self, npz_path):
        z = np.load(npz_path)
        self.w = {k: z[k].astype(np.float64) for k in z.files}

    def forward(self, ie, ve, oe, idx, vd, od):
        """Single sample: returns (value_scalar, policy_vector[n_cands])."""
        w = self.w
        n_enc = len(oe)                       # 25 bags
        x = emb_bag(w["encoder_bag.weight"], ie, ve, oe, n_enc)
        # encoder layer (post-norm relu)
        y = mha(x, x, w["encoder.layers.0.self_attn.in_proj_weight"],
                w["encoder.layers.0.self_attn.in_proj_bias"],
                w["encoder.layers.0.self_attn.out_proj.weight"],
                w["encoder.layers.0.self_attn.out_proj.bias"])
        x = layer_norm(x + y, w["encoder.layers.0.norm1.weight"], w["encoder.layers.0.norm1.bias"])
        y = np.maximum(x @ w["encoder.layers.0.linear1.weight"].T + w["encoder.layers.0.linear1.bias"], 0)
        y = y @ w["encoder.layers.0.linear2.weight"].T + w["encoder.layers.0.linear2.bias"]
        enc = layer_norm(x + y, w["encoder.layers.0.norm2.weight"], w["encoder.layers.0.norm2.bias"])
        v = float(np.tanh((enc @ w["encoder_fc.weight"].T + w["encoder_fc.bias"]).mean()))
        # decoder
        n_dec = len(od)                       # n_cands bags
        p = emb_bag(w["decoder_bag.weight"], idx, vd, od, n_dec)
        y = mha(p, enc, w["decoder.0.attention.in_proj_weight"],
                w["decoder.0.attention.in_proj_bias"],
                w["decoder.0.attention.out_proj.weight"],
                w["decoder.0.attention.out_proj.bias"])
        p = layer_norm(p + y, w["decoder.0.norm1.weight"], w["decoder.0.norm1.bias"])
        y = np.maximum(p @ w["decoder.0.fc1.weight"].T + w["decoder.0.fc1.bias"], 0)
        y = y @ w["decoder.0.fc2.weight"].T + w["decoder.0.fc2.bias"]
        p = layer_norm(p + y, w["decoder.0.norm2.weight"], w["decoder.0.norm2.bias"])
        p = np.tanh(p @ w["decoder_fc.weight"].T + w["decoder_fc.bias"]).ravel()
        return v, p


# ---- commands ----------------------------------------------------------------------
def cmd_export(pth, out):
    import torch
    sd = torch.load(pth, map_location="cpu")
    if not isinstance(sd, dict) or "encoder_bag.weight" not in sd:
        sd = sd.get("model", sd.state_dict() if hasattr(sd, "state_dict") else sd)
    np.savez_compressed(out, **{k: v.numpy() for k, v in sd.items()})
    print(f"exported {len(sd)} tensors -> {out}")


def _iter_samples(pkl_path, n):
    recs = pickle.load(open(pkl_path, "rb"))
    for r in recs[:n]:
        # record layout (datagen_bc): enc_idx, enc_val, enc_off, dec_idx, dec_val,
        # dec_off, n_cands, chosen_idx, turn, outcome, matchup, game_idx
        yield r[0], r[1], r[2], r[3], r[4], r[5], r[6]


def cmd_parity(pth, npz, pkl, n=500):
    import torch
    sys.path.insert(0, ".")
    sys.path.insert(0, "../exp040_mctsv2")
    from train_mcts import MyModel
    m = MyModel(128, 2, 256, 1, 1)
    m.load_state_dict(torch.load(pth, map_location="cpu"))
    m.eval()
    net = NpNet(npz)
    dv = dp = 0.0
    agree = tot = 0
    with torch.no_grad():
        for ie, ve, oe, idx, vd, od, nc in _iter_samples(pkl, n):
            tv, tp = m(torch.tensor(ie, dtype=torch.long), torch.tensor(ve, dtype=torch.float32),
                       torch.tensor(oe, dtype=torch.long),
                       torch.tensor(idx, dtype=torch.long), torch.tensor(vd, dtype=torch.float32),
                       torch.tensor(od, dtype=torch.long))
            tp = tp.view(-1)[:nc].numpy()
            nv, np_p = net.forward(ie, ve, oe, idx, vd, od)
            np_p = np_p[:nc]
            dv = max(dv, abs(float(tv) - nv))
            dp = max(dp, float(np.abs(tp - np_p).max()))
            ta, na = int(tp.argmax()), int(np_p.argmax())
            # exact argmax, or a numerical tie (equal-scored duplicate candidates:
            # float32-vs-64 noise flips which copy wins — semantically identical)
            agree += int(ta == na or abs(float(tp[ta]) - float(tp[na])) < 1e-4)
            tot += 1
    print(f"n={tot} max|dv|={dv:.2e} max|dp|={dp:.2e} argmax agree(incl ties)={agree}/{tot}")
    assert dv < 1e-4 and dp < 1e-4 and agree == tot, "PARITY FAIL"
    print("PARITY OK")


def cmd_speed(npz, pkl, n=300):
    net = NpNet(npz)
    samples = list(_iter_samples(pkl, n))
    t0 = time.time()
    for ie, ve, oe, idx, vd, od, nc in samples:
        net.forward(ie, ve, oe, idx, vd, od)
    dt = (time.time() - t0) / len(samples)
    print(f"numpy inference: {dt * 1000:.2f} ms/decision ({len(samples)} samples)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "export":
        cmd_export(sys.argv[2], sys.argv[3])
    elif cmd == "parity":
        cmd_parity(sys.argv[2], sys.argv[3], sys.argv[4])
    elif cmd == "speed":
        cmd_speed(sys.argv[2], sys.argv[3])
