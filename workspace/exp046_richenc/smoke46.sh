#!/usr/bin/env bash
# exp046 ENC_V2 smoke: 6 games of crustle-only datagen with the new encoder words,
# then inspect the produced records (word count must be 27, new words populated).
set -euo pipefail
cd "$(dirname "$0")/../exp041_pilotnet"
export ENC_V2=1 DATAGEN_ONLY=crustle
uv run python datagen_bc.py 30 6 turnbeam
uv run python - <<'EOF'
import pickle
recs = []
with open("data/samples_turnbeam_w30.pkl", "rb") as f:
    while True:
        try:
            recs.extend(pickle.load(f))
        except EOFError:
            break
print("records:", len(recs))
n_words = [len(r[2]) for r in recs]
print("encoder word-counts (offsets len) sample:", sorted(set(n_words)))
# word 25 = revenge window scalar; word 26 = prized bag.
win = prized_known = 0
for r in recs:
    idx, val, off = r[0], r[1], r[2]
    # offsets are word-start positions into idx/val
    def word(w):
        s = off[w]
        e = off[w + 1] if w + 1 < len(off) else len(idx)
        return list(zip(idx[s:e], val[s:e]))
    w25 = word(25)
    w26 = word(26)
    if any(v == 1.0 for _i, v in w25):
        win += 1
    # prized known = unknown-flag scalar ABSENT (add_single(0) writes nothing) AND bag entries present
    if w26 and all(v != 1.0 or True for _i, v in w26):
        pass
    # simpler: unknown flag occupies the word's FIRST position; value 1.0 = unknown
    unk = any(v == 1.0 and (i == (0 if not w26 else w26[0][0])) for i, v in w26[:1])
    if w26 and not (w26[0][1] == 1.0 and len(w26) == 1):
        prized_known += 1
print(f"revenge-window ON in {win}/{len(recs)} decisions ({win/len(recs):.1%})")
print(f"prized-bag populated in {prized_known}/{len(recs)} decisions ({prized_known/len(recs):.1%})")
EOF
