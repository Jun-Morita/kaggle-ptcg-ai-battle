"""exp070f — ERROR RATE of each predicate against a correct reference.

Before writing any fix, measure how often each predicate is actually WRONG, on
real ladder states (303 koff games). This prioritises the fixes by how much they
could possibly matter, instead of guessing from code reading.

Reference implementations (what the predicate SHOULD say):

  attack_energy_minimum / can_pay_attack
      Shipped: compares COUNTS only (len(energies) >= len(cost)). Real costs are
      typed -- measured examples: Alakazam PSYCHIC x1, Archaludon ex METAL x3,
      Dragapult ex GRASS+PSYCHIC. Reference does a proper typed match with
      colorless flexibility (non-colorless demands must be met by that exact
      type; colorless absorbs any leftover).
      NOTE: our OWN main line is unaffected -- LAND_COLLAPSE costs {0,0} (two
      colorless), so the count check is exactly right there. The error can only
      bite when judging the OPPONENT's threats.

  opponent_ex_pressure
      Shipped: a benched ex with energy counts as pressure identically to an
      active ex. A benched attacker must first be promoted (a retreat/switch),
      so it is at least one turn slower. Reference separates the two so we can
      see how much of the firing is bench-only.

  ready_crustle
      Shipped: `any(p.id == CRUSTLE ...)` -- existence only, despite the name and
      despite its sibling has_ready_tusk checking can_pay_attack. Reference adds
      the attack-payable check, to size the inconsistency.

Output: disagreement rate per predicate over real decision turns.
"""
from __future__ import annotations
import os, sys, json, glob, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine
sys.path.insert(0, HERE)
import probe_predicates as PP

OUR_NAME = "Morita"
KOFF_DIRS = ["0718_54783479", "0718_54797761", "0719_54797761", "0720_54797761"]
COLORLESS = 0


def energy_values(pokemon):
    """Effective energy types attached, as ints."""
    out = []
    for e in getattr(pokemon, "energies", []) or []:
        out.append(int(e) if not hasattr(e, "value") else int(e.value))
    return out


def can_pay_typed(pokemon, attack) -> bool:
    """Correct payment check: typed demands first, colorless absorbs the rest."""
    if pokemon is None or attack is None:
        return False
    have = collections.Counter(energy_values(pokemon))
    cost = [int(c) if not hasattr(c, "value") else int(c.value) for c in attack.energies]
    need_colorless = 0
    for c in cost:
        if c == COLORLESS:
            need_colorless += 1
            continue
        if have.get(c, 0) > 0:
            have[c] -= 1
        else:
            return False           # a typed demand cannot be met
    return sum(have.values()) >= need_colorless


def min_cost_typed(mod, pokemon):
    """Cheapest attack this pokemon can ACTUALLY pay for right now (typed)."""
    if pokemon is None:
        return None
    data = mod.CARD_TABLE.get(pokemon.id)
    if data is None or not data.attacks:
        return None
    best = None
    for aid in data.attacks:
        at = mod.ATTACK_TABLE.get(aid)
        if at is None:
            continue
        n = len(at.energies)
        if best is None or n < best:
            best = n
    return best


def main():
    api, _ = load_engine()
    mod = PP.load_koff()
    to_obs = api.to_observation_class

    files = []
    for d in KOFF_DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                               "episode-*-replay.json")))

    stats = collections.defaultdict(lambda: {"n": 0, "disagree": 0,
                                             "ship_true": 0, "ref_true": 0})
    bench_only = {"fires": 0, "bench_only": 0}

    for fp in files:
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        names = d.get("info", {}).get("TeamNames") or []
        seats = [i for i, n in enumerate(names) if OUR_NAME in str(n)]
        for seat in seats:
            seen = set()
            for step in d.get("steps", []):
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
                if cur is None or cur.yourIndex != seat:
                    continue
                if cur.turn in seen:
                    continue
                seen.add(cur.turn)
                me = cur.players[seat]
                opp = cur.players[1 - seat]

                # --- 1. opponent_can_attack_soon: count-based vs typed ---
                oa = mod.active_pokemon(opp)
                if oa is not None:
                    ship = mod.opponent_can_attack_soon(opp)
                    data = mod.CARD_TABLE.get(oa.id)
                    ref = False
                    if data is not None and data.attacks:
                        # typed: could pay after ONE more energy of the best-case type
                        for aid in data.attacks:
                            at = mod.ATTACK_TABLE.get(aid)
                            if at is None:
                                continue
                            if can_pay_typed(oa, at):
                                ref = True
                                break
                            # allow one more attachment of any single type
                            have = collections.Counter(energy_values(oa))
                            cost = [int(c) for c in at.energies]
                            typed_need = collections.Counter(c for c in cost if c != COLORLESS)
                            short = sum(max(0, typed_need[t] - have.get(t, 0)) for t in typed_need)
                            total_short = max(0, len(cost) - sum(have.values()))
                            if short <= 1 and total_short <= 1:
                                ref = True
                                break
                    s = stats["opponent_can_attack_soon"]
                    s["n"] += 1
                    s["ship_true"] += int(ship)
                    s["ref_true"] += int(ref)
                    s["disagree"] += int(ship != ref)

                # --- 2. opponent_ex_pressure: how much is bench-only? ---
                if mod.opponent_ex_pressure(opp):
                    bench_only["fires"] += 1
                    act_ex = oa is not None and mod.is_ex_pokemon(oa) and \
                        mod.opponent_can_attack_soon(opp)
                    if not act_ex:
                        bench_only["bench_only"] += 1

                # --- 3. ready_crustle: existence vs actually attack-ready ---
                ship = mod.ready_crustle(me)
                ref = any(p.id == mod.CRUSTLE and
                          can_pay_typed(p, mod.ATTACK_TABLE.get(mod.SUPERB_SCISSORS))
                          for p in mod.field_pokemon(me))
                s = stats["ready_crustle"]
                s["n"] += 1
                s["ship_true"] += int(ship)
                s["ref_true"] += int(ref)
                s["disagree"] += int(ship != ref)

    print(f"{'predicate':32s}{'turns':>8}{'ship=T':>9}{'ref=T':>9}{'DISAGREE':>10}")
    for k, s in stats.items():
        if not s["n"]:
            continue
        print(f"{k:32s}{s['n']:8d}{100*s['ship_true']/s['n']:8.1f}%"
              f"{100*s['ref_true']/s['n']:8.1f}%{100*s['disagree']/s['n']:9.1f}%")
    if bench_only["fires"]:
        print(f"\nopponent_ex_pressure fired {bench_only['fires']} turns; "
              f"{100*bench_only['bench_only']/bench_only['fires']:.1f}% were BENCH-ONLY "
              f"(no active ex threat) -- these are the ones over-weighted vs promotion cost")
    json.dump({"stats": {k: dict(v) for k, v in stats.items()}, "bench": bench_only},
              open(os.path.join(HERE, "error_rates.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
