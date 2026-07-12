"""exp046 ablation control: strip ENC_V2's 2 appended encoder words (25, 26)
from already-generated records to produce a MATCHED same-games/same-count
ENC_V2=0 dataset for a clean, confound-free comparison against pre5.

Since ENC_V2 appends new words strictly AFTER the original 25 (word 25 =
revenge window, word 26 = prized bag), truncating the encoder's offset list to
25 entries and dropping any index/value entries at or past that word's start
reproduces EXACTLY what get_encoder_input would have written with ENC_V2=0 on
the same game states -- no need to regenerate data.

Usage: uv run python strip_encv2.py <in.pkl> <out.pkl>
"""
from __future__ import annotations
import pickle
import sys

EI, EV, EO = 0, 1, 2


def strip(rec):
    idx, val, off = rec[EI], rec[EV], rec[EO]
    if len(off) <= 25:
        return rec  # already old-format (shouldn't happen for w40-43)
    cut = off[25]  # index/value position where word 25 starts
    new_idx = idx[:cut]
    new_val = val[:cut]
    new_off = off[:25]
    return (new_idx, new_val, new_off) + tuple(rec[3:])


def main():
    in_path, out_path = sys.argv[1], sys.argv[2]
    n = 0
    with open(in_path, "rb") as fin, open(out_path, "wb") as fout:
        while True:
            try:
                chunk = pickle.load(fin)
            except EOFError:
                break
            out_chunk = [strip(r) for r in chunk]
            pickle.dump(out_chunk, fout, protocol=4)
            n += len(out_chunk)
    print(f"stripped {n} records -> {out_path}")


if __name__ == "__main__":
    main()
