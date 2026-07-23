"""exp074 / H2 -- ORACLE bound on the second clock (taking prizes / サイドを取る).

Established so far:
  - Real games: we end with 5.90-6.00 of our 6 prizes unclaimed. We never take the
    prize route; we win or lose purely on mill (山札切れ). Losses end with 12.60
    cards of their deck unmilled.
  - probe_clock.py: the pool reproduces this exactly (5.91 avg, >=1 prize in only
    9.4% of games), so H2 can be designed and measured locally.
  - Our deck CAN attack:
        Crustle（イワパレス）  Superb Scissors  120 dmg / 3 energy
        Great Tusk（イダイナキバ）Giant Tusk      160 dmg / 4 energy
        Terrakion（テラキオン）  Land Crush      100 dmg / 3 energy
        Great Tusk            Land Collapse      0 dmg / 2 energy  <- the mill attack
    so this is plausibly "won't" rather than "can't". But energy is genuinely
    scarce: 8 energy cards in 60 (Rock Fighting x4 + Mist x4), and 120 damage
    needs 3 of them on one Pokemon.

Per the exp060 rule (measure a lever's dynamic range BEFORE optimising), bound it
with an oracle before writing any policy. Intervention is at the harness, not in
the agent, so no build is modified:

  base    : untouched v030.
  maxdmg  : whenever the engine asks WHICH attack to use (SelectContext.ATTACK),
            override the agent and pick the highest-damage one. Tests only "stop
            picking the 0-damage attack".
  ko      : additionally, at MAIN, if an attack option is available whose damage
            is at least the opponent active's CURRENT hp, take it. This is the
            opportunistic-KO oracle -- the literal second clock, with perfect
            knowledge of when a KO is on.

Reading:
  ko ~= base   -> the second clock is worth nothing; H2 dies here, cheaply, and
                  H1 (speed up the mill instead) becomes the main line.
  ko >> base   -> the headroom is real and sizes the budget for a prize plan.
  ko < base    -> attacking actively costs us; the single clock is correct and
                  that is worth knowing too (it would justify the current design).

The oracle is an UPPER bound: it has perfect KO knowledge and pays nothing for
the energy it spends. A real policy cannot beat it.

Run against the lucario_v2 pool, where CRN is verified to hold (crn_control.py).

Usage: uv run python oracle_prize.py [n_per_matchup]
"""
from __future__ import annotations
import os, sys, json, statistics as stx

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
OPT_ATTACK = 13          # OptionType.ATTACK
CTX_MAIN = 0             # SelectContext.MAIN
CTX_ATTACK = 35          # SelectContext.ATTACK

_DMG = {}


def dmg_of(attack_id):
    return _DMG.get(attack_id, 0)


def first(x):
    return (x[0] if x else None) if isinstance(x, list) else x


def play(agent0, agent1, seed, our_seat, arm):
    api, game = load_engine()
    to_obs = api.to_observation_class
    agents = [agent0, agent1]
    decks = [[int(x) for x in a(_empty_deck_obs())] for a in agents]
    os.environ["CG_CRN_SEED"] = str(seed)
    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return None

    rec = {"my_prize": 6, "op_prize": 6, "turns": 0, "forced": 0, "won": None}
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
            rec["turns"] = cur.turn

            pi = cur.yourIndex
            sel = None
            if arm != "base" and pi == our_seat:
                s = o.select
                opts = s.option or []
                atk_opts = [(i, op) for i, op in enumerate(opts)
                            if op.attackId is not None
                            and (s.context == CTX_ATTACK or op.type == OPT_ATTACK)]
                if atk_opts:
                    if s.context == CTX_ATTACK:
                        # pick the hardest-hitting attack on offer
                        i, _ = max(atk_opts, key=lambda x: dmg_of(x[1].attackId))
                        sel = [i]
                        rec["forced"] += 1
                    elif arm == "ko" and s.context == CTX_MAIN:
                        oa = first(getattr(opp, "active", None))
                        hp = getattr(oa, "hp", None) if oa else None
                        if hp is not None:
                            lethal = [(i, op) for i, op in atk_opts
                                      if dmg_of(op.attackId) >= hp]
                            if lethal:
                                i, _ = max(lethal, key=lambda x: dmg_of(x[1].attackId))
                                sel = [i]
                                rec["forced"] += 1
            if sel is None:
                sel = agents[pi](obs)
            sel = _validate_selection(sel, o.select)
            obs = game.battle_select(sel)
    except Exception:
        game.battle_finish()
        return None
    o = to_obs(obs)
    res = o.current.result if o.current is not None else -1
    rec["won"] = (res == our_seat)
    game.battle_finish()
    return rec


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 100
    load_engine()
    from cg.api import all_attack
    _DMG.update({a.attackId: (a.damage or 0) for a in all_attack()})

    opp = EB.opponents()
    arms = ("base", "maxdmg", "ko")
    res = {a: {} for a in arms}
    print(f"H2 oracle, n={n}/matchup, CRN, lucario_v2 pool.")
    print(f"{'matchup':14}" + "".join(f"{a:>10}" for a in arms)
          + f"{'ko-base':>10}{'prizeLeft(ko)':>15}{'forced/gm':>11}")
    for oname in sorted(EB.SILVER_BAND, key=lambda k: -EB.SILVER_BAND[k]):
        deck, fac = opp[oname]
        seed0 = EB.SEED + abs(hash(oname)) % 99991
        row, extra = {}, {}
        for arm in arms:
            rows = []
            for i in range(n):
                ours = load_built(BUILD, f"v030_{arm}_{oname}_{i}")
                them = fac(deck)
                r = (play(ours, them, seed0 + i, 0, arm) if i % 2 == 0
                     else play(them, ours, seed0 + i, 1, arm))
                if r:
                    rows.append(r)
            row[arm] = sum(r["won"] for r in rows) / max(1, len(rows))
            extra[arm] = (stx.mean([r["my_prize"] for r in rows]) if rows else None,
                          stx.mean([r["forced"] for r in rows]) if rows else None)
        for a in arms:
            res[a][oname] = row[a]
        print(f"{oname:14}" + "".join(f"{row[a]:10.3f}" for a in arms)
              + f"{row['ko']-row['base']:+10.3f}"
              + f"{extra['ko'][0]:15.2f}{extra['ko'][1]:11.1f}", flush=True)

    tot = sum(EB.SILVER_BAND.values())
    print()
    band = {}
    for a in arms:
        band[a] = sum(w * res[a][o] for o, w in EB.SILVER_BAND.items()) / tot
        print(f"band {a:8s} {band[a]:.4f}")
    print(f"\nCEILING (ko - base): {band['ko']-band['base']:+.4f}")
    print("Upper bound only: the oracle knows every lethal for free.")
    json.dump({"per_matchup": res, "band": band},
              open(os.path.join(HERE, f"oracle_prize_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
