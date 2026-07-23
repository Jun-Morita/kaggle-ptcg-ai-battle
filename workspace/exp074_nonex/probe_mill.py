"""exp074 / H1 -- how fast is our only clock, and what gates it?

Chain of findings that leads here:
  1. We finish real games with 5.90-6.00 prizes unclaimed: one clock only (mill).
  2. Losses end with 12.60 cards of their deck still in it.
  3. H2 oracle: a damaging attack is NEVER even legal for us. Over 4 games the
     only attack ever offered was Land Collapse (0 dmg). Superb Scissors (120 /
     3 energy), Giant Tusk (160 / 4) and Land Crush (90 / 3) never appeared.
  4. Reason: our active holds 0 energy on most turns and NEVER reaches 3.
        alakazam_dun  0e x26, 1e x10, 2e x1, 3e+ x0
        pure_wall     0e x42, 1e x19, 2e x12, 3e+ x0
     8 energy cards in 60 (Rock Fighting x4 + Mist x4).

So the prize clock is unreachable without a deck change, and the mill clock is
itself energy-gated. That makes the mill rate the thing to measure:

    Land Collapse: "Discard the top card of your opponent's deck. If you played an
    an Ancient Supporter card from your hand during this turn, discard 3 more."

1 card/turn vs 4 -- a 4x swing on the only clock we have. 12.60 unmilled cards is
about 3-4 boosted turns. If the boost rate is low, H1 has real headroom.

CardData exposes no "Ancient" flag, so which supporters count is measured, not
guessed (the exp067 rule: never assume card/API semantics). Method: watch the
opponent's deckCount across our attack, and record which supporter cardIds we
played that turn. A drop of 4 identifies a boosted turn and therefore the Ancient
supporters in our list.

Usage: uv run python probe_mill.py [n_per_matchup]
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


def f(x):
    return (x[0] if x else None) if isinstance(x, list) else x


def run(oname, n, byid, seed0, opp):
    deck, fac = opp[oname]
    drops = collections.Counter()          # cards milled in one attack -> count
    played_on_drop = collections.defaultdict(collections.Counter)
    per_game = []
    for g in range(n):
        ours = load_built(BUILD, f"mill_{oname}_{g}")
        them = fac(deck)
        api, game = load_engine()
        to_obs = api.to_observation_class
        ags = [ours, them]
        decks = [[int(x) for x in a(_empty_deck_obs())] for a in ags]
        os.environ["CG_CRN_SEED"] = str(seed0 + g)
        obs, sd = game.battle_start(decks[0], decks[1])
        if game.Battle.battle_ptr in (None, 0):
            continue
        prev_deck, prev_turn = None, None
        this_turn_played = collections.Counter()
        milled, turns = 0, set()
        try:
            for _ in range(5000):
                o = to_obs(obs)
                if o.current is not None and o.current.result != -1:
                    break
                if o.select is None:
                    break
                cur = o.current
                od = getattr(cur.players[1], "deckCount", None)
                if cur.turn != prev_turn:
                    this_turn_played = collections.Counter()
                    prev_turn = cur.turn
                if cur.yourIndex == 0:
                    turns.add(cur.turn)
                    # a drop in THEIR deck during OUR turn is our mill
                    if prev_deck is not None and od is not None and od < prev_deck:
                        d = prev_deck - od
                        drops[d] += 1
                        milled += d
                        for cid, k in this_turn_played.items():
                            played_on_drop[d][cid] += k
                    if od is not None:
                        prev_deck = od
                    # remember what we played this turn (MAIN, PLAY options)
                    s = o.select
                    if s.context == 0:
                        pass
                sel = ags[cur.yourIndex](obs)
                if cur.yourIndex == 0:
                    for i in (sel if isinstance(sel, list) else [sel]):
                        try:
                            op = (o.select.option or [])[int(i)]
                        except Exception:
                            continue
                        if op.cardId is not None and int(op.type) == 7:   # PLAY
                            this_turn_played[op.cardId] += 1
                obs = game.battle_select(_validate_selection(sel, o.select))
        except Exception:
            pass
        game.battle_finish()
        per_game.append({"milled": milled, "turns": len(turns)})
    return drops, played_on_drop, per_game


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 20
    load_engine()
    from cg.api import all_card_data
    byid = {c.cardId: c.name for c in all_card_data()}
    opp = EB.opponents()

    all_drops = collections.Counter()
    all_played = collections.defaultdict(collections.Counter)
    print(f"mill probe, n={n}/matchup, CRN\n")
    print(f"{'matchup':14}{'milled/gm':>11}{'our turns':>11}{'mill/turn':>11}")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        d, p, pg = run(oname, n, byid, EB.SEED + abs(hash(oname)) % 99991, opp)
        all_drops.update(d)
        for k, c in p.items():
            all_played[k].update(c)
        if pg:
            m = stx.mean(x["milled"] for x in pg)
            t = stx.mean(x["turns"] for x in pg)
            print(f"{oname:14}{m:11.2f}{t:11.2f}{m/max(1,t):11.2f}", flush=True)

    print(f"\n=== how many cards each mill event removed ===")
    tot = sum(all_drops.values())
    for k in sorted(all_drops):
        print(f"  {k} card(s): {all_drops[k]:5d}  ({all_drops[k]/max(1,tot):.1%})")
    print(f"\n=== cards we played on turns that milled 4+ (the Ancient boost) ===")
    big = collections.Counter()
    for k, c in all_played.items():
        if k >= 4:
            big.update(c)
    for cid, c in big.most_common(12):
        print(f"  {byid.get(cid, cid):28s} {c}")
    print(f"\n=== cards we played on turns that milled exactly 1 ===")
    for cid, c in all_played.get(1, collections.Counter()).most_common(12):
        print(f"  {byid.get(cid, cid):28s} {c}")
    json.dump({"drops": dict(all_drops)},
              open(os.path.join(HERE, f"mill_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
