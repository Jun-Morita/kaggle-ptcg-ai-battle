"""exp074 — autopsy of our WORST REAL matchup: non_ex_attackers (real wr 0.304).

Why here: exp073 compared pool predictions to 452 real koff games. Six of seven
archetypes differ from the pool only by matchmaking compression (winrates pull
toward 0.5 because you face similar-rated opponents). Exactly ONE inverted:

    non_ex_attackers   pool 0.847  ->  real 0.304

Compression cannot carry 0.847 below 0.5, so this is a real divergence: the pool
reports our biggest weakness as a strength. It is 16% of all real losses, second
only to the Alakazam family (25.5%).

Everything is read from real ladder replays -- real decks, real pilots, real
outcomes -- because the pool has been shown to lie about precisely this matchup.

Reads, per game: which non-ex deck they actually played, the prize/mill clocks,
turn counts, and our damage taken -- the same quantities that exposed the
single-clock mechanism against dragapult in exp067.
"""
from __future__ import annotations
import os, sys, json, glob, collections, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

OUR = "Morita"
KOFF_DIRS = ["0718_54783479", "0718_54797761", "0719_54797761", "0720_54797761"]


def first(x):
    if isinstance(x, list):
        return x[0] if x else None
    return x


def main():
    api, _ = load_engine()
    to_obs = api.to_observation_class
    import analyze as A
    from cg.api import all_card_data
    byid = {c.cardId: c for c in all_card_data()}

    files = []
    for d in KOFF_DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                               "episode-*-replay.json")))

    games, decks = [], collections.Counter()
    for fp in files:
        try:
            rep = json.load(open(fp))
        except Exception:
            continue
        names = (rep.get("info") or {}).get("TeamNames") or []
        seats = [i for i, n in enumerate(names) if OUR in str(n)]
        rewards = rep.get("rewards") or []
        if len(seats) != 1 or len(rewards) < 2:
            continue
        seat = seats[0]
        if rewards[seat] is None or rewards[1 - seat] is None:
            continue
        # opponent's declared deck = their first action (the 60-card list)
        opp_seat = 1 - seat
        opp_deck = None
        for step in rep.get("steps", []):
            if opp_seat < len(step):
                a = (step[opp_seat] or {}).get("action")
                if isinstance(a, list) and len(a) == 60:
                    opp_deck = [int(x) for x in a]
                    break
        if opp_deck is None:
            continue
        if A.archetype(opp_deck, byid) != "non_ex_attackers":
            continue

        won = rewards[seat] > rewards[1 - seat]
        key = tuple(sorted(collections.Counter(opp_deck).items()))
        decks[key] += 1

        trace, seen = [], set()
        for step in rep.get("steps", []):
            if seat >= len(step):
                continue
            ob = (step[seat] or {}).get("observation") or {}
            if not ob.get("current") or ob.get("select") is None:
                continue
            try:
                o = to_obs(ob)
            except Exception:
                continue
            cur = o.current
            if cur is None or cur.yourIndex != seat or cur.turn in seen:
                continue
            seen.add(cur.turn)
            me, opp = cur.players[seat], cur.players[1 - seat]
            ma, oa = first(getattr(me, "active", None)), first(getattr(opp, "active", None))
            trace.append({
                "turn": cur.turn,
                "my_prize": len(me.prize) if me.prize is not None else None,
                "op_prize": len(opp.prize) if opp.prize is not None else None,
                "my_deck": getattr(me, "deckCount", None),
                "op_deck": getattr(opp, "deckCount", None),
                "my_hp": getattr(ma, "hp", None) if ma else None,
                "my_ser": getattr(ma, "serial", None) if ma else None,
                "my_bench": len(getattr(me, "bench", []) or []),
                "op_active": getattr(oa, "id", None) if oa else None,
            })
        games.append({"won": won, "trace": trace, "deck": opp_deck})

    W = [g for g in games if g["won"]]
    L = [g for g in games if not g["won"]]
    print(f"non_ex_attackers games found: {len(games)}  ->  {len(W)}W-{len(L)}L "
          f"(wr {len(W)/max(1,len(games)):.3f})\n")

    print("=== which non-ex decks are these? (top 5 exact lists) ===")
    for key, c in decks.most_common(5):
        cnt = dict(key)
        top = sorted(cnt.items(), key=lambda x: -x[1])[:6]
        print(f"  x{c:3d} games: " + ", ".join(
            f"{byid[cid].name if cid in byid else cid}x{n}" for cid, n in top))

    def last(g, k):
        v = [t[k] for t in g["trace"] if t.get(k) is not None]
        return v[-1] if v else None

    print(f"\n=== clocks (the exp067 single-clock lens) ===")
    for nm, gs in (("WINS", W), ("LOSSES", L)):
        if not gs:
            continue
        f = lambda k: [x for x in (last(g, k) for g in gs) if x is not None]
        print(f"  {nm} (n={len(gs)}):")
        print(f"    their deck left  mean {st.mean(f('op_deck')):6.2f}   "
              f"our deck left mean {st.mean(f('my_deck')):6.2f}")
        print(f"    OUR prizes left  mean {st.mean(f('my_prize')):6.2f}   "
              f"THEIR prizes left mean {st.mean(f('op_prize')):6.2f}")
        print(f"    our turns        mean {st.mean([len(g['trace']) for g in gs]):6.2f}")

    print(f"\n=== do we ever take prizes? (single-clock test) ===")
    for nm, gs in (("WINS", W), ("LOSSES", L)):
        if not gs:
            continue
        vals = [last(g, "op_prize") for g in gs]
        vals = [v for v in vals if v is not None]
        took = sum(1 for v in vals if v < 6)
        print(f"  {nm}: games where we took >=1 prize: {took}/{len(vals)}")

    json.dump([{"won": g["won"], "trace": g["trace"]} for g in games],
              open(os.path.join(HERE, "trace.json"), "w"))
    print(f"\ntrace -> {os.path.join(HERE, 'trace.json')}")


if __name__ == "__main__":
    main()
