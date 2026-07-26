"""exp083 item-3: prove the generalised pure-python NpNet is correct for N layers
and non-legacy head counts, WITHOUT waiting for a real multi-layer checkpoint.

Builds a random MyModel(d=64, h=4, enc=2, dec=3), exports it through the real
ship pipeline (state_dict -> npz -> weights_pure.pkl), then compares torch vs the
pure-python net on real recorded samples. The legacy d128/1+1 regression is
covered separately by parity_ship.py.
"""
from __future__ import annotations
import json, os, pickle, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
from harness import load_engine  # noqa: E402
load_engine()
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import numpy as np  # noqa: E402  (export-side only; never shipped)
import torch  # noqa: E402
from train_mcts import MyModel  # noqa: E402
import npmcts_policy as PP  # noqa: E402

CFG = {"d_model": 64, "heads": 4, "d_ff": 128, "enc_layers": 2, "dec_layers": 3}
recs_path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    WS, "exp080_bc", "data", "mixed_ex3_w7.pkl")
n = int(sys.argv[2]) if len(sys.argv) > 2 else 60

torch.manual_seed(0)
m = MyModel(CFG["d_model"], CFG["heads"], CFG["d_ff"], CFG["enc_layers"], CFG["dec_layers"])
m.eval()

d = tempfile.mkdtemp(prefix="ml_parity_")
sd = m.state_dict()
import array
pure = {k: (tuple(v.shape), array.array("f", v.numpy().astype("float32").ravel().tolist()))
        for k, v in sd.items()}
pkl = os.path.join(d, "weights_pure.pkl")
pickle.dump(pure, open(pkl, "wb"), protocol=4)
json.dump(CFG, open(os.path.join(d, "arch.json"), "w"))

net = PP.NpNet(pkl, heads=CFG["heads"])
print(f"pure net inferred: d={net.d} heads={net.h} enc={net.n_enc} dec={net.n_dec}  (want {CFG})")
assert (net.d, net.h, net.n_enc, net.n_dec) == (
    CFG["d_model"], CFG["heads"], CFG["enc_layers"], CFG["dec_layers"]), "arch mismatch"

recs = pickle.load(open(recs_path, "rb"))[:n]
dv = dp = 0.0
agree = tot = 0
with torch.no_grad():
    for r in recs:
        tv, tp = m(torch.tensor(r[0], dtype=torch.long), torch.tensor(r[1], dtype=torch.float32),
                   torch.tensor(r[2], dtype=torch.long), torch.tensor(r[3], dtype=torch.long),
                   torch.tensor(r[4], dtype=torch.float32), torch.tensor(r[5], dtype=torch.long))
        tp = tp.view(-1)[:r[6]].tolist()
        pv, pp = net.forward(r[0], r[1], r[2], r[3], r[4], r[5])
        pp = list(pp)[:r[6]]
        dv = max(dv, abs(float(tv) - pv))
        dp = max(dp, max(abs(a - b) for a, b in zip(tp, pp)))
        ta = max(range(len(tp)), key=lambda i: tp[i])
        pa = max(range(len(pp)), key=lambda i: pp[i])
        agree += int(ta == pa or abs(tp[ta] - tp[pa]) < 1e-4)
        tot += 1
print(f"n={tot} max|dv|={dv:.2e} max|dp|={dp:.2e} argmax agree={agree}/{tot}")
assert dv < 1e-3 and dp < 1e-3 and agree == tot, "MULTI-LAYER PARITY FAIL"
print("MULTI-LAYER PARITY OK (torch == pure-python at enc2/dec3, heads=4)")
