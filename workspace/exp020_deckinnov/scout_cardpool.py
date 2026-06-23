"""exp020: scout the card pool for deck-innovation candidates.

Find strong SINGLE-PRIZE (non-ex/non-megaEx) attackers — high damage per energy,
survivable HP — and flag which are already used by known meta decks vs unused
(= candidates for an ORIGINAL deck we could pilot). Deck Score (20%) + originality
reward our own construction over a copied list. Respects deck<->pilot coupling:
prefer attackers close to what our lucario_v2-based policy can drive (1-2 energy
"attack now" lines, named support-card families with built-in engines).

Usage: uv run python scout_cardpool.py [min_dmg]
"""
from __future__ import annotations
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine  # noqa
api, _ = load_engine()

ETYPE = {0: "C", 1: "?", 2: "?"}  # energies use type ids; print raw count is enough


def known_meta_cards():
    ids = set()
    paths = [
        os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json"),
        os.path.join(ROOT, "workspace", "exp012_nonex", "debauchery_deck.json"),
        os.path.join(ROOT, "workspace", "exp007_anti_crustle", "crustle_deck.json"),
    ]
    for p in paths:
        try:
            ids |= set(json.load(open(p)))
        except Exception:
            pass
    # baselines decks
    try:
        d = json.load(open(os.path.join(ROOT, "workspace", "exp002_baselines", "policies", "decks.json")))
        for v in d.values():
            ids |= set(v)
    except Exception:
        pass
    # alakazam
    try:
        ak = os.path.join(ROOT, "references", "raw", "public_notebooks", "alakazam", "deck.csv")
        ids |= {int(x) for x in open(ak).read().split() if x.strip()}
    except Exception:
        pass
    return ids


def main():
    min_dmg = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    cards = list(api.all_card_data())
    atk = {a.attackId: a for a in api.all_attack()}
    meta = known_meta_cards()
    nm = {c.cardId: c.name for c in cards}

    rows = []
    for c in cards:
        if getattr(c, "cardType", None) != api.CardType.POKEMON:
            continue
        if c.ex or c.megaEx:
            continue
        best = None  # (eff, dmg, cost, attack_name)
        for aid in (c.attacks or []):
            a = atk.get(aid)
            if a is None or not a.damage:
                continue
            cost = len(a.energies or [])
            eff = a.damage / max(cost, 1)
            if best is None or (a.damage, eff) > (best[1], best[0]):
                best = (eff, a.damage, cost, a.name)
        if best is None or best[1] < min_dmg:
            continue
        eff, dmg, cost, aname = best
        stage = "B" if c.basic else "S1" if c.stage1 else "S2" if c.stage2 else "?"
        rows.append((eff, dmg, cost, c.cardId, c.name, c.hp, stage, c.cardId in meta, aname))

    rows.sort(key=lambda r: (-r[0], -r[1]))   # by damage-per-energy, then damage
    print(f"non-ex attackers with best-attack dmg >= {min_dmg}  (eff = dmg/energy)")
    print(f"{'eff':>5} {'dmg':>4} {'cost':>4} {'hp':>4} {'st':>3} {'meta':>4}  name / attack")
    shown = 0
    for eff, dmg, cost, cid, name, hp, stage, in_meta, aname in rows:
        if shown >= 45:
            break
        flag = "USED" if in_meta else " NEW"
        print(f"{eff:5.0f} {dmg:4d} {cost:4d} {hp:4d} {stage:>3} {flag:>4}  {name[:30]:30s} | {aname[:26]}")
        shown += 1

    # support-card families (named prefixes) hint at built-in engines we could pilot
    fam = defaultdict(int)
    for c in cards:
        n = c.name
        if "'s " in n or "’s " in n:
            fam[n.split("'s ")[0].split("’s ")[0]] += 1
    print("\nnamed families (built-in synergy engines), size>=4:")
    for f, k in sorted(fam.items(), key=lambda x: -x[1]):
        if k >= 4:
            print(f"  {f}: {k} cards")


if __name__ == "__main__":
    main()
