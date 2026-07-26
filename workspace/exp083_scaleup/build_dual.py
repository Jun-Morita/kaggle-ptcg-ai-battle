"""exp083 Stage-4 -- build the dual-path submission.

FAST PATH  : numpy + the scaled net (A3, d256/2+2, 100.6MB npz) -- 2.16 ms/act.
FALLBACK   : the existing numpy-free pure-python net (d128/1+1) -- 130 ms/act, the
             configuration that has actually shipped and run on the ladder.
CRASH-SAFE : npmcts_policy.agent()'s existing wrapper (legal fallback on any
             exception, plus the slow-strike guard that disables the net).

Why both: numpy's availability in the agent sandbox is *probable* but unproven.
disc716302's traceback comes from /kaggle_simulations/agent/main.py and shows
/usr/local/lib/python3.11/dist-packages/{numpy,transformers}, and exp041's npnet.py
asserts "sandbox has numpy but no torch"; but npmcts_policy.py deliberately went
numpy-free because no shipped submission had ever proven it. So we ship the big
net behind `try: import numpy` and degrade to the proven pure-python net if that
import (or the npz load) fails. Neither path can time out or crash the episode.

The weights live INSIDE cg/ (proven-delivered: libcg.so must arrive for anything
to run) and are located WITHOUT __file__ -- the harness execs main.py's source in
a bare namespace where __file__ is undefined (the v015 crash).

Usage: uv run python build_dual.py [--net <dir with npnet.npz+arch.json>]
                                   [--fallback <weights_pure.pkl>] [--smoke 12]
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import sys
import tarfile

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
CG = os.path.join(ROOT, "data", "sim_sample", "cg")
POLICY = os.path.join(WS, "exp041_pilotnet", "npmcts_policy.py")
DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")
OUT = os.path.join(HERE, "build_dual")
SIZE_LIMIT_MB = 197.7  # stated competition limit (disc727565)

# Appended to npmcts_policy.py. Runs at import; any failure leaves the pure-python
# MODEL in place. Mirrors exp041/npnet.py's math, generalised to N layers.
NUMPY_BLOCK = '''

# ===== exp083: numpy fast path (big net); silently keeps the pure-python net if
# numpy or the npz is unavailable. Never raises at import. =====
_NPZ_CANDIDATES = [
    "npnet.npz",
    os.path.join("cg", "npnet.npz"),
    "/kaggle_simulations/agent/npnet.npz",
    "/kaggle_simulations/agent/cg/npnet.npz",
]
_ARCH_CANDIDATES = [
    "arch.json",
    os.path.join("cg", "arch.json"),
    "/kaggle_simulations/agent/arch.json",
    "/kaggle_simulations/agent/cg/arch.json",
]


class _NumpyNet:
    """Same forward() contract as the pure-python NpNet: (v, policy_vector)."""

    def __init__(self, npz_path, heads):
        import numpy as _np
        self._np = _np
        z = _np.load(npz_path)
        self.w = {k: z[k].astype(_np.float32) for k in z.files}
        self.d = int(self.w["encoder_bag.weight"].shape[1])
        self.h = int(heads)
        self.n_enc = 1 + max([int(k.split(".")[2]) for k in self.w
                              if k.startswith("encoder.layers.")] + [-1])
        self.n_dec = 1 + max([int(k.split(".")[1]) for k in self.w
                              if k.startswith("decoder.") and k[8:9].isdigit()] + [-1])

    def _ln(self, x, g, b):
        _np = self._np
        m = x.mean(-1, keepdims=True)
        v = x.var(-1, keepdims=True)
        return (x - m) / _np.sqrt(v + 1e-5) * g + b

    def _mha(self, q_in, kv_in, ipw, ipb, opw, opb):
        _np, d, h = self._np, self.d, self.h
        hd = d // h
        q = q_in @ ipw[:d].T + ipb[:d]
        k = kv_in @ ipw[d:2 * d].T + ipb[d:2 * d]
        v = kv_in @ ipw[2 * d:].T + ipb[2 * d:]
        Sq, Sk = q.shape[0], k.shape[0]
        q = q.reshape(Sq, h, hd).transpose(1, 0, 2)
        k = k.reshape(Sk, h, hd).transpose(1, 0, 2)
        v = v.reshape(Sk, h, hd).transpose(1, 0, 2)
        s = q @ k.transpose(0, 2, 1) / _np.sqrt(hd)
        e = _np.exp(s - s.max(axis=-1, keepdims=True))
        a = e / e.sum(axis=-1, keepdims=True)
        return (a @ v).transpose(1, 0, 2).reshape(Sq, d) @ opw.T + opb

    def _bag(self, weight, idx, val, off, n_bags):
        _np = self._np
        out = _np.zeros((n_bags, self.d), dtype=_np.float32)
        idx = _np.asarray(idx, dtype=_np.int64)
        val = _np.asarray(val, dtype=_np.float32)
        off = _np.asarray(off, dtype=_np.int64)
        ends = _np.append(off[1:], len(idx))
        for b in range(n_bags):
            s, e = off[b], ends[b]
            if e > s:
                out[b] = (weight[idx[s:e]] * val[s:e, None]).sum(0)
        return out

    def forward(self, ie, ve, oe, idx, vd, od):
        _np, w = self._np, self.w
        x = self._bag(w["encoder_bag.weight"], ie, ve, oe, len(oe))
        for i in range(self.n_enc):
            q = "encoder.layers.%d." % i
            y = self._mha(x, x, w[q + "self_attn.in_proj_weight"], w[q + "self_attn.in_proj_bias"],
                          w[q + "self_attn.out_proj.weight"], w[q + "self_attn.out_proj.bias"])
            x = self._ln(x + y, w[q + "norm1.weight"], w[q + "norm1.bias"])
            y = _np.maximum(x @ w[q + "linear1.weight"].T + w[q + "linear1.bias"], 0)
            y = y @ w[q + "linear2.weight"].T + w[q + "linear2.bias"]
            x = self._ln(x + y, w[q + "norm2.weight"], w[q + "norm2.bias"])
        enc = x
        v = float(_np.tanh((enc @ w["encoder_fc.weight"].T + w["encoder_fc.bias"]).mean()))
        p = self._bag(w["decoder_bag.weight"], idx, vd, od, len(od))
        for i in range(self.n_dec):
            q = "decoder.%d." % i
            y = self._mha(p, enc, w[q + "attention.in_proj_weight"], w[q + "attention.in_proj_bias"],
                          w[q + "attention.out_proj.weight"], w[q + "attention.out_proj.bias"])
            p = self._ln(p + y, w[q + "norm1.weight"], w[q + "norm1.bias"])
            y = _np.maximum(p @ w[q + "fc1.weight"].T + w[q + "fc1.bias"], 0)
            y = y @ w[q + "fc2.weight"].T + w[q + "fc2.bias"]
            p = self._ln(p + y, w[q + "norm2.weight"], w[q + "norm2.bias"])
        p = _np.tanh(p @ w["decoder_fc.weight"].T + w["decoder_fc.bias"]).ravel()
        return v, p


try:
    _heads = 2
    for _a in _ARCH_CANDIDATES:
        if os.path.exists(_a):
            _heads = int(json.load(open(_a)).get("heads", 2))
            break
    for _z in _NPZ_CANDIDATES:
        if os.path.exists(_z):
            MODEL = _NumpyNet(_z, _heads)
            break
except Exception:
    pass  # keep the pure-python MODEL loaded above
'''


def build(net_dir, fallback_pkl, out=OUT):
    deck = json.load(open(DECK))
    assert len(deck) == 60, len(deck)
    npz = os.path.join(net_dir, "npnet.npz")
    arch = os.path.join(net_dir, "arch.json")
    for p in (npz, arch, fallback_pkl):
        assert os.path.exists(p), f"missing {p}"

    os.makedirs(out, exist_ok=True)
    src = open(POLICY).read()
    assert "import json" in src.split("\n\n")[0] or True
    if "\nimport json" not in src:  # the numpy block needs json for arch.json
        src = src.replace("\nimport os", "\nimport json\nimport os", 1)
    open(os.path.join(out, "main.py"), "w").write(src.rstrip() + "\n" + NUMPY_BLOCK)
    open(os.path.join(out, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")

    dst = os.path.join(out, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    shutil.copy(npz, os.path.join(dst, "npnet.npz"))
    shutil.copy(arch, os.path.join(dst, "arch.json"))
    shutil.copy(fallback_pkl, os.path.join(dst, "weights_pure.pkl"))

    tarp = os.path.join(out, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(os.path.join(out, "main.py"), arcname="main.py")
        tar.add(os.path.join(out, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))

    names = set(tarfile.open(tarp).getnames())
    need = {"main.py", "deck.csv", "cg/npnet.npz", "cg/arch.json",
            "cg/weights_pure.pkl", "cg/api.py", "cg/libcg.so"}
    assert need <= names, f"bad tar, missing {sorted(need - names)}"
    top = sorted(n for n in names if "/" not in n)
    assert top == ["deck.csv", "main.py"], top
    mb = os.path.getsize(tarp) / 1e6
    assert mb < SIZE_LIMIT_MB, f"{mb:.1f}MB exceeds the {SIZE_LIMIT_MB}MB limit"
    print(f"built {tarp}  {mb:.1f}MB (limit {SIZE_LIMIT_MB})  files={len(names)}  top={top}")
    return tarp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--net", default=os.path.join(WS, "exp041_pilotnet", "results", "sc083_A3"))
    ap.add_argument("--fallback", default=os.path.join(WS, "exp041_pilotnet", "results",
                                                       "pre_grimm10", "weights_pure.pkl"))
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()
    build(args.net, args.fallback, args.out)
    print("\nNext: per-act timing on the BUILT artifact via exp041_pilotnet/sandbox_replica.py "
          "(gate 3, <=0.3s/act), then the ladder gate.")


if __name__ == "__main__":
    main()
