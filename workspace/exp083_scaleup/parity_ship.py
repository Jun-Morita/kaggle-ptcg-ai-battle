"""exp083 re-ship parity: torch checkpoint vs the PURE-PYTHON net that actually
ships (npmcts_policy.NpNet + weights_pure.pkl). numpy is used only to drive the
torch reference here; the shipped path never imports it (v015/v042 root cause).

Usage: uv run python parity_ship.py <model.pth> <weights_pure.pkl> <records.pkl> [n]
"""
from __future__ import annotations
import json, os, pickle, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
from harness import load_engine  # noqa: E402
load_engine()
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import torch  # noqa: E402
from train_mcts import MyModel  # noqa: E402
import npmcts_policy as PP  # noqa: E402

EI, EV, EO, DI, DV, DO, NC = range(7)


def main():
    pth, pkl, recs_path = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 300

    cfg = {"d_model": 128, "heads": 2, "d_ff": 256, "enc_layers": 1, "dec_layers": 1}
    cand = os.path.join(os.path.dirname(os.path.abspath(pth)), "arch.json")
    if os.path.exists(cand):
        cfg.update({k: v for k, v in json.load(open(cand)).items() if k in cfg})
    PP.MODEL = PP.NpNet(pkl, heads=cfg["heads"])   # the exact file that ships
    print("arch:", cfg)
    m = MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                cfg["enc_layers"], cfg["dec_layers"])
    m.load_state_dict(torch.load(pth, map_location="cpu"))
    m.eval()

    recs = pickle.load(open(recs_path, "rb"))[:n]
    dv = dp = 0.0
    agree = tot = 0
    with torch.no_grad():
        for r in recs:
            tv, tp = m(torch.tensor(r[EI], dtype=torch.long), torch.tensor(r[EV], dtype=torch.float32),
                       torch.tensor(r[EO], dtype=torch.long), torch.tensor(r[DI], dtype=torch.long),
                       torch.tensor(r[DV], dtype=torch.float32), torch.tensor(r[DO], dtype=torch.long))
            tp = tp.view(-1)[:r[NC]].tolist()
            pv, pp = PP.MODEL.forward(r[EI], r[EV], r[EO], r[DI], r[DV], r[DO])
            pp = list(pp)[:r[NC]]
            dv = max(dv, abs(float(tv) - pv))
            dp = max(dp, max(abs(a - b) for a, b in zip(tp, pp)))
            ta = max(range(len(tp)), key=lambda i: tp[i])
            pa = max(range(len(pp)), key=lambda i: pp[i])
            agree += int(ta == pa or abs(tp[ta] - tp[pa]) < 1e-4)
            tot += 1
    print(f"n={tot} max|dv|={dv:.2e} max|dp|={dp:.2e} argmax agree={agree}/{tot}")
    assert dv < 1e-3 and dp < 1e-3 and agree == tot, "PARITY FAIL"
    print("PARITY OK (torch == shipped pure-python)")


if __name__ == "__main__":
    main()
