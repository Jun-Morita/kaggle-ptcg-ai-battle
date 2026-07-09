"""Export npnet.npz (numpy) -> a pure-stdlib pickle (array.array('f',...) per
tensor + shapes) so the submission can load weights WITHOUT numpy at all.

Root cause of the v015 Kaggle "Validation Episode failed" error (2026-07-09):
none of our 14 prior shipped submissions ever used numpy, and cg's own source
has zero numpy imports -- the "cg depends on numpy so it's available" assumption
was never actually verified and is now empirically refuted. np.load() itself
also requires numpy, so the .npz format is unusable at inference time too, not
just the forward-pass math.

Usage: uv run python export_pure.py results/pre2/npnet.npz results/pre2/weights_pure.pkl
"""
from __future__ import annotations
import array
import pickle
import sys

import numpy as np


def main():
    npz_path, out_path = sys.argv[1], sys.argv[2]
    z = np.load(npz_path)
    out = {}
    for k in z.files:
        a = z[k].astype("float32")
        out[k] = (a.shape, array.array("f", a.ravel().tolist()))
    with open(out_path, "wb") as f:
        pickle.dump(out, f, protocol=4)
    import os
    print(f"wrote {out_path} ({os.path.getsize(out_path) / 1e6:.1f}MB, {len(out)} tensors)")


if __name__ == "__main__":
    main()
