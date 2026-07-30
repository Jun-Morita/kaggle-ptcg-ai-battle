"""ENC_V4 feature parity: train_mcts.get_encoder_input == npmcts_policy's copy.

The two encoders are hand-mirrored source, not shared code, because the ship path
must run without torch. A divergence produces NO error -- the shipped agent simply
becomes a different function than the one that was trained and gated. ENC_V3 had a
dedicated tar-level check (verify_ship_enc.py) for the same reason; this checks the
level below it: that the feature VECTORS agree index-for-index on real positions.

Usage: uv run python parity_enc.py [--n 300] [--day 0728]
"""
from __future__ import annotations
import glob
import json
import os
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))
from harness import load_engine  # noqa: E402
load_engine()
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

os.environ["ENC_V4"] = "1"
import train_mcts as tm  # noqa: E402
from cg.api import to_observation_class  # noqa: E402


def arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def load_ship():
    """npmcts_policy reads enc_version from arch.json at IMPORT time, so plant one
    in a temp cwd and import from there -- exactly how the shipped tar resolves it."""
    d = tempfile.mkdtemp()
    json.dump({"d_model": 128, "heads": 4, "d_ff": 256, "enc_layers": 2,
               "dec_layers": 2, "enc_version": 4}, open(os.path.join(d, "arch.json"), "w"))
    # the ship module also wants deck.csv next to it
    src = os.path.join(WS, "exp083_scaleup", "build_v15s", "deck.csv")
    if os.path.exists(src):
        open(os.path.join(d, "deck.csv"), "w").write(open(src).read())
    cwd = os.getcwd()
    os.chdir(d)
    try:
        sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
        import npmcts_policy as PP
        return PP
    finally:
        os.chdir(cwd)


def main():
    n_target = int(arg("--n", "300"))
    day = arg("--day", "0728")
    PP = load_ship()
    print(f"train_mcts: ENC_V3={tm.ENC_V3} ENC_V4={tm.ENC_V4} "
          f"words={tm.num_words_encoder} size={tm.encoder_size}")
    print(f"ship      : ENC_V3={PP.ENC_V3} ENC_V4={PP.ENC_V4} "
          f"words={PP.NUM_WORDS_ENCODER}")
    assert PP.ENC_V4 == 1, "ship module did not resolve enc_version=4 from arch.json"
    assert PP.NUM_WORDS_ENCODER == tm.num_words_encoder, "word count differs"
    assert PP.card_count == tm.card_count, (PP.card_count, tm.card_count)

    zp = sorted(glob.glob(os.path.join(ROOT, f"references/raw/episodes_{day}/*.zip")))[0]
    z = zipfile.ZipFile(zp)
    deck = [1] * 60
    n = bad = 0
    maxi = 0
    for name in z.namelist():
        ep = json.load(z.open(name))
        for st in ep.get("steps", []):
            for ti in (0, 1):
                if ti >= len(st):
                    continue
                o = st[ti].get("observation")
                if not isinstance(o, dict) or o.get("select") is None:
                    continue
                try:
                    oc = to_observation_class(o)
                except Exception:
                    continue
                if oc.select is None or not oc.select.option:
                    continue
                a = tm.get_encoder_input(oc, deck, deck)
                b = PP.get_encoder_input(oc, deck, deck)
                if (list(a.index) != list(b.index) or list(a.value) != list(b.value)
                        or list(a.offset) != list(b.offset)):
                    bad += 1
                    if bad == 1:
                        ia, ib = list(a.index), list(b.index)
                        j = next((k for k in range(min(len(ia), len(ib)))
                                  if ia[k] != ib[k]), min(len(ia), len(ib)))
                        print(f"  MISMATCH at record {n}: len {len(ia)} vs {len(ib)}, "
                              f"first diff at {j}: {ia[j:j+4]} vs {ib[j:j+4]}")
                maxi = max(maxi, max(a.index) if a.index else 0)
                n += 1
                if n >= n_target:
                    break
            if n >= n_target:
                break
        if n >= n_target:
            break
    print(f"n={n}  mismatches={bad}  max_index={maxi}  "
          f"headroom={tm.encoder_size - maxi}")
    print("ENC PARITY OK" if bad == 0 else "ENC PARITY FAILED")
    sys.exit(0 if bad == 0 else 1)


if __name__ == "__main__":
    main()
