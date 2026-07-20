"""exp069: restate every historical benchmark on the calibrated (V2) pool.

We are not re-running any games -- every winrate below is an existing measured
number (n=200-300 CRN). Only the WEIGHTS change, so this is pure re-aggregation.
Purpose: after calibration, all future gates compare against a bar expressed in
the same units. Prints V1 vs V2 side by side so nothing silently shifts.
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB

V1, V2 = EB.SILVER_BAND_V1, EB.SILVER_BAND_V2

ko = json.load(open(os.path.join(WS, "exp054_upperband", "ko_off_n300.json")))
BUILDS = {
    "koff (SHIPPED)": ko["ko_OFF"]["wr"],
    "stock LO (pre KO_OFF)": ko["stock"]["wr"],
    # exp066 screen n=200
    "megaluc cand (exp066)": {"alakazam_dun": 0.495, "archaludon": 0.345, "alakazam": 0.680,
                              "marnie": 0.935, "lucario_ex": 0.585, "dragapult": 0.640,
                              "pure_wall": 0.650, "crustle_LO": 0.400},
    # exp065 screen n=200
    "dragapult cand (exp065)": {"alakazam_dun": 0.725, "archaludon": 0.425, "alakazam": 0.605,
                                "marnie": 0.810, "lucario_ex": 0.450, "dragapult": 0.500,
                                "pure_wall": 0.000, "crustle_LO": 0.700},
    # exp068 lever arms n=200 (pub1034)
    "pub1034 search ON": {"alakazam_dun": 0.950, "archaludon": 0.835, "alakazam": 0.910,
                          "marnie": 0.900, "lucario_ex": 0.875, "dragapult": 0.425,
                          "pure_wall": 0.945, "crustle_LO": 0.385},
    "pub1034 search OFF": {"alakazam_dun": 0.915, "archaludon": 0.810, "alakazam": 0.890,
                           "marnie": 0.920, "lucario_ex": 0.825, "dragapult": 0.415,
                           "pure_wall": 0.890, "crustle_LO": 0.320},
}


def score(wr, W):
    return sum(w * wr[o] for o, w in W.items()) / sum(W.values())


print(f"{'build':26s}{'V1 (07-13)':>12}{'V2 (calib)':>12}{'delta':>9}")
print("-" * 59)
out = {}
for name, wr in BUILDS.items():
    a, b = score(wr, V1), score(wr, V2)
    out[name] = {"v1": a, "v2": b}
    print(f"{name:26s}{a:12.4f}{b:12.4f}{b-a:+9.4f}")

bar = out["koff (SHIPPED)"]
print(f"\nADOPTION BAR: was {bar['v1']:.4f} (V1) -> now {bar['v2']:.4f} (V2, calibrated)")
print("A candidate must beat koff on the SAME pool; only the bar's value changes.\n")

print("loss decomposition under V2 (share of all koff losses):")
wr = BUILDS["koff (SHIPPED)"]
rows = sorted(((w * (1 - wr[o]), o, w, wr[o]) for o, w in V2.items()), reverse=True)
tot = sum(r[0] for r in rows)
v1rows = {o: V1[o] * (1 - wr[o]) for o in V1}
v1tot = sum(v1rows.values())
for loss, o, w, r in rows:
    print(f"  {o:15s} share {w:.3f}  wr {r:.3f}  ->{100*loss/tot:6.1f}% of losses "
          f"(V1 said {100*v1rows[o]/v1tot:5.1f}%)")

json.dump(out, open(os.path.join(HERE, "restated.json"), "w"), indent=1)
