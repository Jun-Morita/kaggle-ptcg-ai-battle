"""Fine archetype classifier (ported from the public en-replay-archetype-analysis classify_deck,
ID-based) to decompose our coarse meta-watch buckets (mixed_ex3/4) into NAMED archetypes.

Reads a cached replay dir, classifies each opponent's 60-card deck, reports our W-L per
fine archetype. Usage: uv run python fine_classify.py [replay_dir] [our_name_substring]
  default: 0626_54044198 (v011) / Morita
"""
from __future__ import annotations
import glob, json, os, sys
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# signature card IDs (resolved from EN_Card_Data.csv)
BELLIBOLT, GARCHOMP, WALREIN, ZOROARK, GRIMMSNARL = 269, 381, 943, 293, 648
ALAKAZAM, DUDUNSPARCE, COMFEY, CHANDELURE = 245, 66, 164, 98
CRUSTLE, DWEBBLE, TYPHLOSION = 345, 344, 354
PIKACHU, AZUMARILL, AZUMARILL_EX, SLOWKING = 210, 315, 962, 163
MLUCARIO, RIOLU, SOLROCK, LUNATONE = 678, 677, 676, 675   # Riolu in Lucario deck = 677
DRAGAPULT, DRAKLOAK, DREEPY = 121, 120, 119
ARCHALUDON, DURALUDON = 190, 169
MSTARMIE, MFROSLASS, MLOPUNNY = 1031, 861, 849
MGARDEVOIR, MCHARX, MCHARY = 747, 790, 928
OKIDOGI, OKIDOGI_EX, BARBARACLE = 116, 138, 1052
HOPTREV, HOPSNORLAX = 879, 878   # Hop's Trevenant line (our deck)
DIPPLIN, THWACKEY, FESTIVAL = 93, 90, 1245


def classify(idset):
    h = lambda c: c in idset
    # specific named ex decks first
    if h(BELLIBOLT): return "Iono's Bellibolt ex"
    if h(GARCHOMP): return "Cynthia's Garchomp ex"
    if h(WALREIN): return "Walrein"
    if h(ZOROARK): return "N's Zoroark ex"
    if h(GRIMMSNARL): return "Marnie's Grimmsnarl ex"
    if h(ALAKAZAM) and h(DUDUNSPARCE): return "Alakazam + Dudunsparce"
    if h(ALAKAZAM): return "Alakazam"
    if h(COMFEY) and h(CHANDELURE): return "Comfey + Chandelure"
    if h(CRUSTLE) and h(TYPHLOSION): return "Crustle + Ethan's Typhlosion"
    if (h(DIPPLIN) or False) and h(THWACKEY) and h(FESTIVAL): return "Festival Deck"
    if h(TYPHLOSION) and h(DUDUNSPARCE): return "Ethan's Typhlosion + Dudunsparce"
    if h(TYPHLOSION) and h(DREEPY): return "Ethan's Typhlosion + Dreepy"
    if h(TYPHLOSION): return "Ethan's Typhlosion"
    if h(PIKACHU) and (h(AZUMARILL) or h(AZUMARILL_EX)): return "Pikachu ex + Azumarill"
    if h(SLOWKING): return "Slowking"
    if h(HOPTREV): return "Hop (non-ex Trevenant)"          # our archetype / mirror
    # mega / tag-based
    tags = []
    if h(MLUCARIO) or h(RIOLU): tags.append("Mega Lucario ex")
    if h(SOLROCK) and h(LUNATONE): tags.append("Solrock/Lunatone")
    if h(DRAGAPULT) or h(DRAKLOAK) or h(DREEPY): tags.append("Dragapult ex")
    if h(CRUSTLE) or h(DWEBBLE): tags.append("Crustle")
    if h(OKIDOGI) or h(OKIDOGI_EX): tags.append("Okidogi")
    if h(BARBARACLE): tags.append("Barbaracle")
    if h(MGARDEVOIR): tags.append("Mega Gardevoir ex")
    if h(MCHARX) or h(MCHARY): tags.append("Mega Charizard ex")
    if h(ARCHALUDON) or h(DURALUDON): tags.append("Archaludon ex")
    if h(MSTARMIE) and h(MFROSLASS): tags.append("Mega Starmie ex + Mega Froslass ex")
    elif h(MSTARMIE) and h(MLOPUNNY): tags.append("Mega Starmie ex + Mega Lopunny ex")
    elif h(MSTARMIE): tags.append("Mega Starmie ex")
    elif h(MFROSLASS): tags.append("Mega Froslass ex")
    if not tags: return "Other / Unknown"
    if "Mega Lucario ex" in tags and "Solrock/Lunatone" in tags: return "Mega Lucario ex + Solrock/Lunatone"
    if "Dragapult ex" in tags: return "Dragapult ex"
    if "Archaludon ex" in tags: return "Archaludon ex"
    if "Crustle" in tags: return "Crustle"
    return tags[0]


def deck_of(d, idx):
    for st in d.get("steps", []):
        if idx < len(st):
            a = st[idx].get("action")
            if isinstance(a, list) and len(a) == 60:
                return [int(x) for x in a]
    return None


def main():
    pdir = sys.argv[1] if len(sys.argv) > 1 else "0626_54044198"
    sub = sys.argv[2] if len(sys.argv) > 2 else "Morita"
    files = sorted(glob.glob(os.path.join(ROOT, "references", "raw", "replays", pdir, "*.json")))
    wl = defaultdict(lambda: [0, 0, 0])  # archetype -> [W,L,D]
    for f in files:
        try: d = json.load(open(f))
        except Exception: continue
        tn = (d.get("info") or {}).get("TeamNames") or []
        idx = next((i for i, n in enumerate(tn) if sub.lower() in str(n).lower()), None)
        if idx is None: continue
        opp_deck = deck_of(d, 1 - idx)
        if not opp_deck: continue
        arch = classify(set(opp_deck))
        res = d.get("rewards", [0, 0])
        r = res[idx] if idx < len(res) else 0
        slot = 0 if r == 1 else (1 if r == -1 or (idx < len(res) and res[idx] < res[1 - idx]) else 2)
        wl[arch][slot] += 1
    rows = sorted(wl.items(), key=lambda kv: -(kv[1][0] + kv[1][1] + kv[1][2]))
    print(f"# fine archetype W-L vs {sub} ({pdir})")
    print(f"{'archetype':38s} {'W':>3} {'L':>3} {'D':>3}  {'wr':>5}  n")
    for a, (w, l, dr) in rows:
        n = w + l + dr
        print(f"{a:38s} {w:3d} {l:3d} {dr:3d}  {w/n if n else 0:5.2f}  {n}")


if __name__ == "__main__":
    main()
