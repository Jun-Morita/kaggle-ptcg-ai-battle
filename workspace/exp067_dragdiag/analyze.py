"""exp067 analysis: what actually kills us vs dragapult?

Snapshots are taken at the START of each actor's turn, so a change between
snapshot a and snapshot b is the result of what happened during a's turn --
attribute deltas to a["actor"], NOT b["actor"] (an off-by-one in the first
version inverted every label).

KOs are detected via Pokemon.serial (unique per card per match): our active's
serial changing means the previous active left the slot.
"""
import json, os, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
games = json.load(open(os.path.join(HERE, "trace.json")))
W = [g for g in games if g["won"]]
L = [g for g in games if not g["won"]]
print(f"{len(W)}W-{len(L)}L  (wr {len(W)/max(1,len(games)):.3f})\n")


def last(g, key):
    v = [t[key] for t in g["trace"] if t.get(key) is not None]
    return v[-1] if v else None


def summarize(name, gs):
    print(f"--- {name} (n={len(gs)}) ---")
    for key, label in (("op_deck", "their deck left (our mill target)"),
                       ("my_deck", "our deck left"),
                       ("my_prize", "OUR prizes left (6 = we took none)"),
                       ("op_prize", "THEIR prizes left (0 = they won on prizes)")):
        v = [last(g, key) for g in gs]
        v = [x for x in v if x is not None]
        if v:
            print(f"  final {label:42s} mean {st.mean(v):6.2f} median {st.median(v):5.1f}")
    print(f"  game length (turn-slots){' ':19s} mean {st.mean([len(g['trace']) for g in gs]):6.2f}")
    print()


summarize("WINS", W)
summarize("LOSSES", L)

print("--- how the game ENDED (final prize/deck state) ---")
for name, gs in (("WINS", W), ("LOSSES", L)):
    c = collections.Counter()
    for g in gs:
        opd, opp_p, myp = last(g, "op_deck"), last(g, "op_prize"), last(g, "my_prize")
        if opd is not None and opd <= 1:
            c["their deck empty -> MILL WIN"] += 1
        elif opp_p is not None and opp_p <= 1:
            c["they were 0-1 prizes away -> PRIZE LOSS"] += 1
        else:
            c[f"other (op_deck~{opd}, their_prizes~{opp_p})"] += 1
    print(f"  {name}: {dict(c)}")
print()

print("--- our KO rate (active replaced) and prizes conceded ---")
for name, gs in (("WINS", W), ("LOSSES", L)):
    kos, conceded, lens = [], [], []
    for g in gs:
        tr = g["trace"]
        k = sum(1 for a, b in zip(tr, tr[1:])
                if a["my_serial"] is not None and b["my_serial"] is not None
                and a["my_serial"] != b["my_serial"])
        kos.append(k)
        p0 = next((t["op_prize"] for t in tr if t["op_prize"]), None)
        p1 = last(g, "op_prize")
        if p0 is not None and p1 is not None:
            conceded.append(p0 - p1)
        lens.append(len([t for t in tr if t["actor"] == "us"]))
    print(f"  {name}: our-active replacements {st.mean(kos):.2f}/game | "
          f"prizes conceded {st.mean(conceded):.2f} | our turns {st.mean(lens):.1f}")
print()

print("--- mill progress vs clock ---")
for name, gs in (("WINS", W), ("LOSSES", L)):
    rates, remain = [], []
    for g in gs:
        tr = [t for t in g["trace"] if t["op_deck"] is not None]
        our = sum(1 for t in tr if t["actor"] == "us")
        if our:
            rates.append((tr[0]["op_deck"] - tr[-1]["op_deck"]) / our)
        remain.append(last(g, "op_deck"))
    print(f"  {name}: mill {st.mean(rates):.2f} cards/our-turn | "
          f"their deck left at end {st.mean([r for r in remain if r is not None]):.1f}")
print()

print("--- our HP drain during THEIR turns (attack+ability), per game ---")
for name, gs in (("WINS", W), ("LOSSES", L)):
    drain = collections.Counter()
    for g in gs:
        tr = g["trace"]
        for a, b in zip(tr, tr[1:]):
            if a["my_serial"] != b["my_serial"]:
                continue  # active changed: HP reset, not damage
            if a["my_hp"] is None or b["my_hp"] is None:
                continue
            d = a["my_hp"] - b["my_hp"]
            if d > 0:
                drain[a["actor"]] += d   # attribute to the actor of the EARLIER turn
    tot = sum(drain.values()) or 1
    print(f"  {name}: during THEIR turns {drain['them']/max(1,len(gs)):.0f}/game "
          f"({100*drain['them']/tot:.0f}%) | during OUR turns {drain['us']/max(1,len(gs)):.0f}/game "
          f"({100*drain['us']/tot:.0f}%)")
