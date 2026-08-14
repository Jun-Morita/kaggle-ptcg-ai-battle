"""Regenerate feats.OPP_CARDS: the opponent cards worth naming individually.

Union of the current archetypes' most common 60-card lists, weighted by their
share of the 08-12 field, minus anything already in our own deck (those cards
have per-card columns already). Prints the list to paste into feats.py.
"""
import json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp001_harness", "exp040_mctsv2", "exp011_meta_watch", "exp080_bc"):
    sys.path.insert(0, os.path.join(WS, p))
sys.path.insert(0, HERE)
import feats  # noqa: E402

SHARE = {"mixed_ex4": .158, "dragapult": .258, "ex_beatdown": .206,
         "lucario_ex": .066, "mixed_ex1": .114}
NAME = {int(c.cardId): c.name for c in feats.all_card_data()}
OURS = set(json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json"))))
w = Counter()
for a, s in SHARE.items():
    p = os.path.join(HERE, f"deck_{a}.json")
    if os.path.exists(p):
        for cid, k in Counter(json.load(open(p))).items():
            w[int(cid)] += s * k
od = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
for cid, k in Counter(od.get("crustle_control", [])).items():
    w[int(cid)] += .053 * k
# Our own 19 also get OPPONENT-side columns. Leaving them out was the flaw in
# the first attempt: "already covered" was true of our side of the board, not
# theirs, so in the mirror -- 42% of the gate and the heaviest cell -- all 80
# added columns were identically zero. LightGBM samples 80% of features per
# tree, so dead columns are not free: the mirror fell 0.593 -> 0.541 and the
# build lost overall despite gaining in crustle, ex_beatdown and Alakazam.
top = [c for c, _ in w.most_common() if c not in OURS][:40] + sorted(OURS)
json.dump(top, open(os.path.join(HERE, "opp_cards.json"), "w"))
for c in top:
    print(f"  {c:>5}  {NAME.get(c, '?')}")
print("\nOPP_CARDS =", top)
