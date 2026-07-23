"""exp074 / H2 step 1 -- do we take prizes IN THE POOL, or only fail to in reality?

The autopsy of 27 real games found we finish with 5.90-6.00 of our 6 prizes
unclaimed: we run a single clock (mill / 山札切れ) and never take the prize route.
Losses end with 12.60 cards of their deck still unmilled -- games we lose while
holding a completely unused second win condition.

Before designing a prize plan (H2), check the cheap thing first: does this even
reproduce in the pool? Two outcomes, both useful:

  pool also ~6.00 unclaimed  -> the behaviour reproduces locally, so H2 can be
      designed and measured on the instrument we have. Proceed to the oracle.
  pool takes prizes normally -> the pool disagrees with reality about our own
      behaviour, which is a bigger finding than H2 and must be fixed first.

Also records the raw material for the "can't vs won't" question: how much damage
we ever deal, and whether the opponent's active is ever brought low.

Run against the lucario_v2 pool, where CRN is verified to hold (crn_control.py).

Usage: uv run python probe_clock.py [n_per_matchup]
"""
from __future__ import annotations
import os, sys, json, statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
assert EB.USE_CRN, "CRN harness not active"
import cg as _cg
assert "exp052_crn" in _cg.__file__, f"plain engine: {_cg.__file__}"
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine, _empty_deck_obs, _validate_selection
from eval_band import load_built

BUILD = os.path.join(WS, "exp071_bundlefix", "build")


def first(x):
    if isinstance(x, list):
        return x[0] if x else None
    return x


def play(agent0, agent1, seed, our_seat):
    """One instrumented match. agent0 always sits at seat 0; our_seat says which
    of the two is US, so both sides of the swap are recorded from our view."""
    api, game = load_engine()
    to_obs = api.to_observation_class
    agents = [agent0, agent1]
    decks = [[int(x) for x in a(_empty_deck_obs())] for a in agents]
    os.environ["CG_CRN_SEED"] = str(seed)
    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return None

    rec = {"turns": 0, "my_prize": 6, "op_prize": 6, "op_deck": None,
           "min_op_hp": None, "won": None}
    try:
        for _ in range(5000):
            o = to_obs(obs)
            if o.current is not None and o.current.result != -1:
                break
            if o.select is None:
                break
            cur = o.current
            me, opp = cur.players[our_seat], cur.players[1 - our_seat]
            if me.prize is not None:
                rec["my_prize"] = len(me.prize)
            if opp.prize is not None:
                rec["op_prize"] = len(opp.prize)
            od = getattr(opp, "deckCount", None)
            if od is not None:
                rec["op_deck"] = od
            oa = first(getattr(opp, "active", None))
            hp = getattr(oa, "hp", None) if oa else None
            if hp is not None:
                rec["min_op_hp"] = hp if rec["min_op_hp"] is None else min(rec["min_op_hp"], hp)
            rec["turns"] = cur.turn
            pi = cur.yourIndex
            sel = _validate_selection(agents[pi](obs), o.select)
            obs = game.battle_select(sel)
    except Exception as e:
        game.battle_finish()
        return None
    o = to_obs(obs)
    res = o.current.result if o.current is not None else -1
    rec["won"] = (res == our_seat)
    game.battle_finish()
    return rec


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 40
    opp = EB.opponents()
    print(f"v030 vs pool, instrumented. n={n}/matchup (half on each side).")
    print(f"real ladder reference: our prizes left 5.90-6.00, "
          f"their deck left 12.60 on losses\n")
    print(f"{'matchup':14}{'wr':>7}{'ourPrizeLeft':>14}{'theirPrizeLeft':>15}"
          f"{'theirDeckLeft':>14}{'minOppHP':>10}{'tookAny':>9}")
    allrec = {}
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed0 = EB.SEED + abs(hash(oname)) % 99991
        rows = []
        for i in range(n):
            ours = load_built(BUILD, f"v030_probe_{oname}_{i}")
            them = fac(deck)
            if i % 2 == 0:
                r = play(ours, them, seed0 + i, 0)
            else:
                r = play(them, ours, seed0 + i, 1)
            if r:
                rows.append(r)
        if not rows:
            print(f"{oname:14}  (no valid games)")
            continue
        f = lambda k: [r[k] for r in rows if r[k] is not None]
        took = sum(1 for r in rows if r["my_prize"] < 6)
        allrec[oname] = {
            "n": len(rows),
            "wr": sum(r["won"] for r in rows) / len(rows),
            "my_prize_left": st.mean(f("my_prize")),
            "op_prize_left": st.mean(f("op_prize")),
            "op_deck_left": st.mean(f("op_deck")) if f("op_deck") else None,
            "min_op_hp": st.mean(f("min_op_hp")) if f("min_op_hp") else None,
            "took_any_prize": took / len(rows),
        }
        a = allrec[oname]
        print(f"{oname:14}{a['wr']:7.3f}{a['my_prize_left']:14.2f}"
              f"{a['op_prize_left']:15.2f}"
              f"{(a['op_deck_left'] if a['op_deck_left'] is not None else -1):14.2f}"
              f"{(a['min_op_hp'] if a['min_op_hp'] is not None else -1):10.1f}"
              f"{a['took_any_prize']:9.1%}", flush=True)

    if allrec:
        mp = st.mean([v["my_prize_left"] for v in allrec.values()])
        tk = st.mean([v["took_any_prize"] for v in allrec.values()])
        print(f"\npool average: our prizes left {mp:.2f}, "
              f"games where we took >=1 prize {tk:.1%}")
        print("reality: our prizes left 5.90-6.00 -> "
              + ("REPRODUCES, H2 can be designed on the pool"
                 if mp > 5.5 else
                 "DOES NOT reproduce; the pool disagrees about our own behaviour"))
    json.dump(allrec, open(os.path.join(HERE, f"clock_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
