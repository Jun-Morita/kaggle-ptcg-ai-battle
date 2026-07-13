"""exp053 step 4 -- deck-ratio sweep on the LO-mill list to close its dragapult hole.

Hypothesis (mechanism-driven, not blind search):
  LO-mill's ONLY real bleed is dragapult (0.297; everything else >= 0.5), while
  v016-wall -- the SAME Crustle shell -- beats dragapult 1.000. The difference
  between the two lists in durability terms:
                        Jumbo Ice Cream   Hero's Cape
      v016-wall (1.000)        x4              x1
      LO-mill   (0.297)        x1              x0
  Dragapult is a SPREAD deck (Phantom Dive drops counters on the bench), so
  healing + raw HP is exactly what blunts it.

  Crucially, the LO pilot ALREADY implements both cards at top priority
  (main.py:716 Jumbo heals at >=40 dmg & >=3 energy, score 350000;
   main.py:838 Hero's Cape scores 260000 on a wall-mode Crustle / 210000 on
   Great Tusk) -- the pilot can use them, the DECK just doesn't run them.
  So this is the exp027 "deck-ratio" lever (which improved every matchup at
  once), NOT speculative deck design, and NOT a deck<->pilot mismatch (contrast:
  v016-wall's Cook/Waitress healers are NOT in the pilot's card table at all,
  so importing those would just be dead cards -- deliberately not done).

Cuts are taken from the cards least essential to the mill win condition:
  Xerosic's Machinations x4 (hand disruption), Lisia's Appeal x2 (switch-style
  control, redundant with Switch x4 + Boss's Orders x4).

ACE SPEC constraint (verified against card data, engine enforces it in
Api.h::ApiBattleStart -> error type 4): **Hero's Cape AND Neutralization Zone
are BOTH ACE SPEC**, and a deck may contain at most ONE ACE SPEC card total.
The LO list already runs Neutralization Zone x1, so Hero's Cape can only be
added by SWAPPING OUT Neutralization Zone, and only ever x1. (v016-wall runs
Hero's Cape x1 as its single ACE SPEC -- same rule.) Every variant below is
asserted 60 cards AND <=1 ACE SPEC before being written.

Usage: uv run python gen_variants.py   -> writes lo_v_*.json (each asserted 60)
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))
from analyze import card_map  # noqa: E402

JUMBO, CAPE, XEROSIC, LISIA = 1147, 1159, 1197, 1204
NEUTRAL_ZONE = 1247  # ACE SPEC, currently the LO list's only one


def base_deck():
    with open(os.path.join(HERE, "lo_opp", "deck.csv")) as f:
        return [int(x) for x in f.read().split() if x.strip().isdigit()]


def variant(base, deltas):
    """deltas: {card_id: signed count change}. Returns a new 60-card list."""
    ctr = Counter(base)
    for cid, dc in deltas.items():
        ctr[cid] = max(0, ctr[cid] + dc)
        if ctr[cid] == 0:
            del ctr[cid]
    deck = [cid for cid, k in ctr.items() for _ in range(k)]
    return deck


VARIANTS = {
    # bump the healer the pilot already prioritizes; pay for it from disruption
    "jumbo4": {JUMBO: +3, XEROSIC: -3},
    # swap the ACE SPEC: Neutralization Zone -> Hero's Cape (+100HP on the wall),
    # which is v016-wall's ACE SPEC choice. Exactly 1 ACE SPEC either way.
    "cape": {CAPE: +1, NEUTRAL_ZONE: -1},
    # both levers: v016-wall's durability profile ported onto the mill shell
    "both": {JUMBO: +3, XEROSIC: -3, CAPE: +1, NEUTRAL_ZONE: -1},
    # heavier durability skew (stress the far end of the ratio curve): cut ALL
    # the disruption/redundant-switch slots, refill with the 2nd Terrakion (607,
    # backup attacker the pilot knows) + a 2nd Ultra Ball (1121, also known)
    "maxdur": {JUMBO: +3, XEROSIC: -4, LISIA: -2, CAPE: +1, NEUTRAL_ZONE: -1,
               607: +2, 1121: +1},
}


def ace_spec_count(deck, byid):
    return sum(1 for c in deck if getattr(byid.get(c), "aceSpec", False))


def main():
    byid = card_map()
    base = base_deck()
    assert len(base) == 60, len(base)
    print(f"base LO-mill: {len(base)} cards "
          f"(Jumbo x{base.count(JUMBO)}, Cape x{base.count(CAPE)}, "
          f"Xerosic x{base.count(XEROSIC)}, Lisia x{base.count(LISIA)})\n")

    print(f"base ACE SPEC count = {ace_spec_count(base, byid)}\n")

    for name, deltas in VARIANTS.items():
        d = variant(base, deltas)
        # the two rules ApiBattleStart enforces (else it returns errorType 4 / 2)
        assert len(d) == 60, f"{name}: {len(d)} cards, not 60"
        n_ace = ace_spec_count(d, byid)
        assert n_ace <= 1, f"{name}: {n_ace} ACE SPEC cards (max 1)"
        # max 4 copies per card NAME, except Basic Energy (engine: errorType 2)
        names = Counter(getattr(byid.get(c), "name", str(c)) for c in d)
        for nm, k in names.items():
            assert k <= 4 or "Basic" in nm, f"{name}: {nm} x{k} (max 4)"

        path = os.path.join(HERE, f"lo_v_{name}.json")
        json.dump(d, open(path, "w"))
        chg = ", ".join(
            f"{getattr(byid.get(c), 'name', c)} {base.count(c)}->{d.count(c)}"
            for c in deltas)
        print(f"{name:8} 60 OK, ace={n_ace}  |  {chg}")
    print(f"\nwrote lo_v_*.json to {HERE}")


if __name__ == "__main__":
    main()
