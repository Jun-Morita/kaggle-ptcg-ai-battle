"""Convert exp064 mirror chunks -> exp041 pretrain.py-compatible files.

In:  data/mirror_w{wid}_{chunk}.pkl  (list of games; game = list of 10-tuples
     (enc_i, enc_v, enc_o, dec_i, dec_v, dec_o, n_cands, idx, turn, won_int))
Out: data/samples_mirror_w{wid}.pkl  (appended pickle dumps; chunk = flat list
     of 12-tuples r9 + (outcome_float, matchup, game_id)) -- matches datagen_bc.
"""
import glob, os, pickle, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
gid = 0
for wid in range(4):
    out = os.path.join(DATA, f"samples_mirror_w{wid}.pkl")
    if os.path.exists(out):
        os.remove(out)
    fout = open(out, "ab")
    n_rec = 0
    for path in sorted(glob.glob(os.path.join(DATA, f"mirror_w{wid}_*.pkl"))):
        games = pickle.load(open(path, "rb"))
        flat = []
        for game in games:
            gid += 1
            for r in game:
                flat.append(tuple(r[:9]) + (float(r[9]), "mirror", gid))
        pickle.dump(flat, fout, protocol=4)
        n_rec += len(flat)
    fout.close()
    print(f"w{wid}: {n_rec} records -> {out}")
