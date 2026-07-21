"""exp070h — is the "+1 energy per turn" assumption in opponent_can_attack_soon wrong?

    def opponent_can_attack_soon(opponent):
        return attached_energy_count(active) + 1 >= attack_energy_minimum(active)

The "+1" hard-codes "the opponent attaches exactly one energy next turn". Energy
acceleration (Archaludon's ability, Crispin, etc.) attaches more, so against accel
decks this UNDER-estimates how fast a threat arrives.

Ground truth is directly observable: look at the opponent's active energy count on
consecutive opponent turns and measure the ACTUAL gain. No proxy needed.

Measures:
  1. distribution of real per-turn energy gain on the opponent's active
  2. how often the predicate's prediction ("ready next turn") disagreed with what
     actually happened (attached >= min cost on their next turn)
  3. the same split by whether we won or lost

Note this is a different question from the earlier typed-vs-count check (0.1%
disagreement); that was about energy TYPE, this is about energy RATE.
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


def main():
    api, _ = load_engine()
    mod = PP.load_koff()
    to_obs = api.to_observation_class

    files = []
    for d in KOFF_DIRS:
        files += sorted(glob.glob(os.path.join(ROOT, "references/raw/replays", d,
                                               "episode-*-replay.json")))

    gain_hist = collections.Counter()
    pred = {"n": 0, "disagree": 0, "pred_true": 0, "actual_true": 0,
            "missed_fast": 0}   # predicate said NOT soon, but they WERE ready
    by_out = {"W": collections.Counter(), "L": collections.Counter()}

    for fp in files:
        try:
            d = json.load(open(fp))
        except Exception:
            continue
        names = d.get("info", {}).get("TeamNames") or []
        seats = [i for i, n in enumerate(names) if OUR_NAME in str(n)]
        rewards = d.get("rewards") or []
        for seat in seats:
            if seat >= len(rewards) or rewards[seat] is None or len(rewards) < 2:
                continue
            k = "W" if rewards[seat] > rewards[1 - seat] else "L"
            # opponent active energy, sampled once per OUR decision turn
            series = []   # (turn, serial, attached, min_cost, pred)
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
                if cur is None or cur.yourIndex != seat or cur.turn in seen:
                    continue
                seen.add(cur.turn)
                opp = cur.players[1 - seat]
                a = mod.active_pokemon(opp)
                if a is None:
                    continue
                series.append((cur.turn, getattr(a, "serial", None),
                               mod.attached_energy_count(a),
                               mod.attack_energy_minimum(a),
                               mod.opponent_can_attack_soon(opp)))
            # consecutive samples on the SAME active pokemon
            for (t0, s0, e0, m0, p0), (t1, s1, e1, m1, p1) in zip(series, series[1:]):
                if s0 is None or s0 != s1:
                    continue          # active changed: not a clean delta
                gain = e1 - e0
                if gain >= 0:
                    gain_hist[min(gain, 5)] += 1
                    by_out[k][min(gain, 5)] += 1
                pred["n"] += 1
                actual_ready = e1 >= m1
                pred["pred_true"] += int(p0)
                pred["actual_true"] += int(actual_ready)
                pred["disagree"] += int(p0 != actual_ready)
                if actual_ready and not p0:
                    pred["missed_fast"] += 1

    tot = sum(gain_hist.values()) or 1
    print("=== ACTUAL opponent energy gain per turn (same active) ===")
    for g in sorted(gain_hist):
        lbl = f"{g}" if g < 5 else "5+"
        print(f"  +{lbl}: {gain_hist[g]:6d}  ({100*gain_hist[g]/tot:5.1f}%)")
    accel = sum(v for g, v in gain_hist.items() if g >= 2)
    print(f"  --> gain >= 2 (acceleration, the '+1' assumption is WRONG here): "
          f"{accel} ({100*accel/tot:.1f}%)")

    n = pred["n"] or 1
    print(f"\n=== predicate vs what actually happened (n={pred['n']} transitions) ===")
    print(f"  predicate said 'can attack soon' : {100*pred['pred_true']/n:5.1f}%")
    print(f"  actually WAS attack-ready next   : {100*pred['actual_true']/n:5.1f}%")
    print(f"  DISAGREE                         : {100*pred['disagree']/n:5.1f}%")
    print(f"  missed a faster-than-+1 arrival  : {100*pred['missed_fast']/n:5.1f}%"
          f"   <- what acceleration awareness would fix")

    print("\n=== gain distribution split by our outcome ===")
    for k in ("W", "L"):
        s = sum(by_out[k].values()) or 1
        acc = sum(v for g, v in by_out[k].items() if g >= 2)
        print(f"  {k}: accel(>=2) {100*acc/s:.1f}%  (n={s})")

    json.dump({"gain": dict(gain_hist), "pred": pred,
               "by_outcome": {k: dict(v) for k, v in by_out.items()}},
              open(os.path.join(HERE, "accel_rates.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
