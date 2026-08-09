"""Is our exact 60-card list still what the top players run?

The archetype label is a fuzzy classifier; the corpus filter is an exact match.
v2 taught us that training on the label rather than the list costs real strength
(fidelity 0.684 -> 0.798 while head-to-head fell 0.510 -> 0.315), so the number
that decides whether a day is usable teacher data is the EXACT match rate.
"""
import glob, json, os, sys, zipfile
from collections import Counter
HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ours = sorted(json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))))

def decks_from_ep(ep):
    d = {}
    for st in ep.get("steps", []):
        for i, ag in enumerate(st):
            a = (ag or {}).get("action")
            if isinstance(a, list) and len(a) == 60 and i not in d:
                d[i] = [int(x) for x in a]
        if len(d) >= 2:
            break
    return d

cap = int(sys.argv[1]) if len(sys.argv) > 1 else 200
print(f"{'day':<12}{'grimm seats':>12}{'sampled':>9}{'exact':>8}{'rate':>8}")
for p in sorted(glob.glob(os.path.join(HERE, "indices", "2026-*.json"))):
    d = json.load(open(p))
    seats = [(m, s) for (m, s, a, _sc) in d["teachers"] if a == "mixed_ex3"]
    if not seats:
        continue
    z = zipfile.ZipFile(d["zip"])
    hit = n = 0
    for m, s in seats[:cap]:
        try:
            ep = json.loads(z.read(m))
        except Exception:
            continue
        dk = decks_from_ep(ep)
        if s not in dk:
            continue
        n += 1
        hit += sorted(dk[s]) == ours
    if n:
        print(f"{os.path.basename(p)[:10]:<12}{len(seats):>12}{n:>9}{hit:>8}{hit/n:>8.1%}")
