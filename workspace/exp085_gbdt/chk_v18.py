import json, zipfile, collections
import build_rows as BR, feats
from feats import all_card_data
d = json.load(open("indices/2026-08-14.json")); z = zipfile.ZipFile(d["zip"])
byid = {int(c.cardId): c for c in all_card_data()}
st = collections.Counter(); n = 0
for (m, s, a, sc) in d["teachers"]:
    if a != "mixed_ex3": continue
    for ch in BR.convert_seat(json.loads(z.read(m)), s, byid, st, 0,
                              exact=feats.DECK, score=sc) or []:
        for x in ch[3]:
            assert len(x) == feats.N_FEATURES, (len(x), feats.N_FEATURES)
            n += 1
    if n > 800: break
print(f"rows {n}, width {feats.N_FEATURES} -- consistent")
