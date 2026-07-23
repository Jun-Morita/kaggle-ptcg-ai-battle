"""exp074 / H1 step 2 -- is the mill boost lost to SUPPORTER PRIORITY? (free fix?)

Measured so far (probe_mill2 + the Ancient identification run):
    Land Collapse milled 1 card on 172 events, 4 cards on 37 -> boost rate 17.7%
    the ONLY Ancient supporter in our 60 is Explorer's Guidance x4
    on turns we attacked WITHOUT the boost we had played:
        Colress's Tenacity x11, Boss's Orders x11, Lisia's Appeal x5

You may play only ONE supporter per turn. So every turn we attacked while holding
Explorer's Guidance but spent the supporter slot on something else is a 1-mill turn
that could have been a 4-mill turn -- worth 3 cards, at zero deck cost, fixable as
a policy priority rather than a deck change.

This counts exactly that. Per turn in which we attack, classify:
    boosted            -- Explorer's Guidance played, mill 4
    EG in hand, wasted -- EG was in hand, a DIFFERENT supporter was played
    EG in hand, unused -- EG was in hand, no supporter played at all
    no EG              -- EG not in hand; only a deck change can help these

Reading: the first two categories are the free headroom. If they are near zero the
boost is draw-limited and H1 needs more Ancient supporters in the list (which
requires finding them -- the engine exposes no trait flag, so that is a much more
expensive empirical search). If they are large, patch the priority and re-measure.

Usage: uv run python probe_eg.py [n_per_matchup]
"""
from __future__ import annotations
import os, sys, json, collections

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
EG = 1185                      # Explorer's Guidance (measured: our only Ancient)
SUPPORTER = 3                  # CardData.cardType for supporters
L_PLAY, L_ATTACK, L_MOVE, L_MOVE_R = 10, 15, 6, 7
A_DECK, A_DISCARD = 1, 3


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
    api, game = load_engine()
    to_obs = api.to_observation_class
    from cg.api import all_card_data
    cards = {c.cardId: c for c in all_card_data()}
    sup = {cid for cid, c in cards.items() if int(c.cardType) == SUPPORTER}
    opp = EB.opponents()

    tally = collections.Counter()
    wasted_for = collections.Counter()
    print(f"Explorer's Guidance probe, n={n}/matchup, CRN\n")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed0 = EB.SEED + abs(hash(oname)) % 99991
        for g in range(n):
            ours = load_built(BUILD, f"eg_{oname}_{g}")
            them = fac(deck)
            ags = [ours, them]
            decks = [[int(x) for x in a(_empty_deck_obs())] for a in ags]
            os.environ["CG_CRN_SEED"] = str(seed0 + g)
            obs, sd = game.battle_start(decks[0], decks[1])
            if game.Battle.battle_ptr in (None, 0):
                continue
            turn = -1
            played, eg_in_hand = collections.Counter(), False
            try:
                for _ in range(5000):
                    o = to_obs(obs)
                    cur = o.current
                    t = cur.turn if cur is not None else turn
                    if t != turn:
                        turn, played, eg_in_hand = t, collections.Counter(), False
                    if cur is not None and cur.yourIndex == 0:
                        hand = getattr(cur.players[0], "hand", None) or []
                        if any(getattr(c, "id", getattr(c, "cardId", None)) == EG
                               for c in hand):
                            eg_in_hand = True
                    atk, nmill = False, 0
                    for lg in (o.logs or []):
                        ty = int(lg.type)
                        if ty == L_PLAY and lg.playerIndex == 0:
                            played[lg.cardId] += 1
                        elif ty == L_ATTACK and lg.playerIndex == 0:
                            atk = True
                        elif ty in (L_MOVE, L_MOVE_R) and lg.playerIndex == 1:
                            if (lg.fromArea is not None and int(lg.fromArea) == A_DECK
                                    and lg.toArea is not None
                                    and int(lg.toArea) == A_DISCARD):
                                nmill += 1
                    if atk and nmill:
                        sup_played = [c for c in played if c in sup]
                        if EG in played:
                            tally["boosted"] += 1
                        elif eg_in_hand and sup_played:
                            tally["EG in hand, wasted on another supporter"] += 1
                            for c in sup_played:
                                wasted_for[c] += 1
                        elif eg_in_hand:
                            tally["EG in hand, no supporter played"] += 1
                        else:
                            tally["no EG in hand"] += 1
                    if cur is not None and cur.result != -1:
                        break
                    if o.select is None:
                        break
                    obs = game.battle_select(
                        _validate_selection(ags[cur.yourIndex](obs), o.select))
            except Exception:
                pass
            game.battle_finish()
        print(f"  {oname} done", flush=True)

    tot = sum(tally.values())
    print(f"\n=== attack turns that milled, classified (n={tot}) ===")
    for k in ("boosted", "EG in hand, wasted on another supporter",
              "EG in hand, no supporter played", "no EG in hand"):
        print(f"  {k:42s} {tally[k]:5d}  {tally[k]/max(1,tot):6.1%}")
    free = (tally["EG in hand, wasted on another supporter"]
            + tally["EG in hand, no supporter played"])
    print(f"\nfree headroom (EG was in hand but unplayed): {free}/{tot} "
          f"= {free/max(1,tot):.1%} of milling attacks")
    print(f"each such turn is worth +3 milled cards; "
          f"potential +{free*3/max(1,tot):.2f} cards per milling attack")
    if wasted_for:
        print(f"\nsupporters we played INSTEAD of Explorer's Guidance:")
        for cid, c in wasted_for.most_common(8):
            print(f"  {cards[cid].name if cid in cards else cid:28s} {c}")
    json.dump(dict(tally), open(os.path.join(HERE, f"eg_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
