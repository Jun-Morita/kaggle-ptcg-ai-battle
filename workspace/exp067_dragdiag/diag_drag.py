"""exp067 step 1-2: WHY does koff lose to dragapult (wr 0.363)?

Loss-weight decomposition: dragapult is 18.0% of all koff losses despite only
5.7% band share -- the only major matchup we lose outright, and the one never
autopsied (exp054-G/H/I covered Alakazam variants and walls; dragapult is rare
in-band so we seldom face it live).

DIAGNOSIS ONLY -- no patch, no gate. Per the exp060 lever-measurement-first
rule we characterise the mechanism before spending anything on optimisation.

Assumption under test (so far only CLASSIFIED as structural, never verified):
  "dragapult losses are structural -- Dusknoir/Munkidori ABILITY damage bypasses
   Safeguard / Neutralization Zone, which block only ATTACKS."
Discriminator: if true, our HP should drain on turns where the opponent makes no
attack, and losses should show a steady chip curve. If false -- if our HP falls
on their ATTACK turns -- then Safeguard/NZ are simply not up when they should be,
which is a decision leak.

Turn-level aggregation only (exp022 rule: raw per-select counts overcount).
"""
from __future__ import annotations
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB  # sets up sys.path + loads engine
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine, _empty_deck_obs, _validate_selection

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")


def make_koff():
    from eval_band import load_built
    return load_built(KOFF_DIR, "koff")


def snapshot(o, seat):
    """Per-turn state for OUR seat.

    Field names verified against cg.api: PlayerState has `prize` (a list, whose
    length is the prizes REMAINING) and `active` (list[Pokemon|None]); Pokemon
    identity is `.id` and `.serial` (serial is unique per card per match, so it
    is the reliable way to detect that the active was replaced after a KO).
    """
    cur = o.current
    me = cur.players[seat]
    opp = cur.players[1 - seat]

    def act(p):
        a = getattr(p, "active", None)
        if isinstance(a, list):
            a = a[0] if a else None
        if a is None:
            return None, None, None
        return getattr(a, "hp", None), getattr(a, "id", None), getattr(a, "serial", None)

    my_hp, my_id, my_ser = act(me)
    op_hp, op_id, op_ser = act(opp)
    return {
        "turn": cur.turn,
        "my_prize": len(me.prize) if getattr(me, "prize", None) is not None else None,
        "op_prize": len(opp.prize) if getattr(opp, "prize", None) is not None else None,
        "my_hp": my_hp, "my_active": my_id, "my_serial": my_ser,
        "my_bench": len(getattr(me, "bench", []) or []),
        "op_hp": op_hp, "op_active": op_id, "op_serial": op_ser,
        "my_deck": getattr(me, "deckCount", None),
        "op_deck": getattr(opp, "deckCount", None),
    }


def run_instrumented(agent0, agent1, our_seat, crn_seed, max_steps=5000):
    api, game = load_engine()
    to_obs = api.to_observation_class
    agents = [agent0, agent1]
    decks = [[int(x) for x in a(_empty_deck_obs())] for a in agents]

    os.environ["CG_CRN_SEED"] = str(crn_seed)
    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return None

    trace, seen_turns = [], set()
    winner = -1
    try:
        for _ in range(max_steps):
            o = to_obs(obs)
            if o.current is not None and o.current.result != -1:
                break
            if o.select is None:
                break
            # one snapshot per (turn, acting seat) -- turn-level, not per-select
            cur = o.current
            key = (cur.turn, cur.yourIndex)
            if key not in seen_turns:
                seen_turns.add(key)
                s = snapshot(o, our_seat)
                s["actor"] = "us" if cur.yourIndex == our_seat else "them"
                trace.append(s)
            pi = o.current.yourIndex
            sel = _validate_selection(agents[pi](obs), o.select)
            obs = game.battle_select(sel)
    except Exception:
        pass

    o = to_obs(obs)
    if o.current is not None:
        winner = o.current.result
    game.battle_finish()
    return {"winner": winner, "trace": trace, "won": winner == our_seat}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    opp = EB.opponents()
    deck, fac = opp["dragapult"]

    games = []
    for g in range(n):
        us_first = (g % 2 == 0)
        ours, theirs = make_koff(), fac(deck)
        a0, a1 = (ours, theirs) if us_first else (theirs, ours)
        our_seat = 0 if us_first else 1
        r = run_instrumented(a0, a1, our_seat, crn_seed=20260920 + g)
        if r is None:
            print(f"game {g}: battle_start failed", flush=True)
            continue
        games.append(r)
        print(f"game {g}: {'WIN ' if r['won'] else 'LOSS'} turns={len(r['trace'])}", flush=True)

    json.dump(games, open(os.path.join(HERE, "trace.json"), "w"))
    wins = [g for g in games if g["won"]]
    losses = [g for g in games if not g["won"]]
    print(f"\n=== {len(wins)}W-{len(losses)}L (wr {len(wins)/max(1,len(games)):.3f}) ===")
    print(f"trace saved -> {os.path.join(HERE, 'trace.json')}")


if __name__ == "__main__":
    main()
