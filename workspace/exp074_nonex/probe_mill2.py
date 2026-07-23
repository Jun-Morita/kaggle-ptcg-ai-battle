"""exp074 / H1 -- mill rate measured from the LOG stream (probe_mill.py was wrong).

probe_mill.py tried to infer our mill from drops in the opponent's deckCount. That
conflates our Land Collapse with their own draws and searches, and reported an
absurd 48-60 cards "milled" per game. Discarded.

Correct source: Observation.logs.
    LogType.ATTACK (15)                      -- an attack resolved, with attackId
    LogType.MOVE_CARD / _REVERSE (6 / 7)     -- a card moved, with fromArea/toArea
    LogType.PLAY (10)                        -- a card was played from hand

So: attribute cards leaving the OPPONENT's DECK(1) for their DISCARD(3) during our
turn to our attack, and record which supporters we played on that turn.

What this decides (H1):
    Land Collapse mills 1 normally, 4 if an Ancient Supporter was played that turn.
    Losses leave 12.60 cards unmilled ~= 3-4 boosted turns. If the boost rate is
    low, raising it is the cheapest available win. If it is already high, the mill
    is energy-gated instead (our active holds 0 energy on most turns and never
    reaches 3) and H1 becomes an energy-count deck question.

Which supporters are Ancient is measured, not assumed -- CardData exposes no such
flag and guessing card semantics is what produced the null-data bug in exp067.

Usage: uv run python probe_mill2.py [n_per_matchup]
"""
from __future__ import annotations
import os, sys, json, collections, statistics as stx

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
L_ATTACK, L_PLAY, L_MOVE, L_MOVE_R, L_TURN_START = 15, 10, 6, 7, 2
A_DECK, A_DISCARD = 1, 3


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
    api, game = load_engine()
    to_obs = api.to_observation_class
    from cg.api import all_card_data, all_attack
    byid = {c.cardId: c.name for c in all_card_data()}
    aname = {a.attackId: a.name for a in all_attack()}
    opp = EB.opponents()

    events = collections.Counter()            # (attack, n_milled) -> count
    boost_play = collections.defaultdict(collections.Counter)  # n_milled -> cards
    per_mu = {}
    null_logs = [0, 0]

    print(f"mill probe v2 (log-based), n={n}/matchup, CRN\n")
    print(f"{'matchup':14}{'ourMill/gm':>12}{'ourTurns':>10}{'mill/turn':>11}{'boost%':>9}")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed0 = EB.SEED + abs(hash(oname)) % 99991
        games = []
        for g in range(n):
            ours = load_built(BUILD, f"m2_{oname}_{g}")
            them = fac(deck)
            ags = [ours, them]
            decks = [[int(x) for x in a(_empty_deck_obs())] for a in ags]
            os.environ["CG_CRN_SEED"] = str(seed0 + g)
            obs, sd = game.battle_start(decks[0], decks[1])
            if game.Battle.battle_ptr in (None, 0):
                continue
            milled, boosted, attacks, turns = 0, 0, 0, set()
            played_this_turn = collections.Counter()
            try:
                for _ in range(5000):
                    o = to_obs(obs)
                    logs = o.logs or []
                    null_logs[1] += 1
                    if not logs:
                        null_logs[0] += 1
                    # attribute log events since the previous selection
                    pending_atk = None
                    n_mill = 0
                    for lg in logs:
                        t = int(lg.type)
                        if t == L_TURN_START:
                            played_this_turn = collections.Counter()
                        elif t == L_PLAY and lg.playerIndex == 0:
                            played_this_turn[lg.cardId] += 1
                        elif t == L_ATTACK and lg.playerIndex == 0:
                            pending_atk = getattr(lg, "attackId", None)
                            attacks += 1
                        elif t in (L_MOVE, L_MOVE_R) and lg.playerIndex == 1:
                            if (lg.fromArea is not None and int(lg.fromArea) == A_DECK
                                    and lg.toArea is not None and int(lg.toArea) == A_DISCARD):
                                n_mill += 1
                    if pending_atk is not None and n_mill:
                        milled += n_mill
                        events[(aname.get(pending_atk, pending_atk), n_mill)] += 1
                        boost_play[n_mill].update(played_this_turn)
                        if n_mill >= 4:
                            boosted += 1
                    if o.current is not None and o.current.result != -1:
                        break
                    if o.select is None:
                        break
                    cur = o.current
                    if cur.yourIndex == 0:
                        turns.add(cur.turn)
                    obs = game.battle_select(
                        _validate_selection(ags[cur.yourIndex](obs), o.select))
            except Exception:
                pass
            game.battle_finish()
            games.append({"milled": milled, "turns": len(turns),
                          "attacks": attacks, "boosted": boosted})
        if not games:
            continue
        m = stx.mean(x["milled"] for x in games)
        t = stx.mean(x["turns"] for x in games)
        ba = sum(x["boosted"] for x in games)
        at = sum(x["attacks"] for x in games)
        per_mu[oname] = {"mill": m, "turns": t, "boost_rate": ba / max(1, at)}
        print(f"{oname:14}{m:12.2f}{t:10.2f}{m/max(1,t):11.2f}"
              f"{ba/max(1,at):9.1%}", flush=True)

    print(f"\nlog null-rate: {null_logs[0]}/{null_logs[1]} selections had no logs")
    print(f"\n=== attack -> cards milled ===")
    for (a, k), c in sorted(events.items(), key=lambda x: -x[1])[:12]:
        print(f"  {str(a):20s} milled {k:2d}  x{c}")
    print(f"\n=== supporters played on BOOSTED turns (milled>=4) ===")
    big = collections.Counter()
    for k, c in boost_play.items():
        if k >= 4:
            big.update(c)
    for cid, c in big.most_common(10):
        print(f"  {byid.get(cid, cid):28s} {c}")
    print(f"\n=== cards played on UNBOOSTED turns (milled==1) ===")
    for cid, c in boost_play.get(1, collections.Counter()).most_common(10):
        print(f"  {byid.get(cid, cid):28s} {c}")
    json.dump({"per_matchup": per_mu,
               "events": {f"{a}|{k}": v for (a, k), v in events.items()}},
              open(os.path.join(HERE, f"mill2_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
