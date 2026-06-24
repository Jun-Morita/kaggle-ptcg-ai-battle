"""Measure OUR policy's mirror behavior on Mogja's win-correlated metrics.

Decode v006's own MAIN decisions (from obs+action) in a v006-vs-v006 mirror and compare
to Mogja's WINNING mirror profile: attack mix (Trevenant Revenge vs Phantump), Boss's
Orders timing, energy-on-attacker. Gaps = concrete mirror rules to patch.
Usage: uv run python our_mirror_stats.py [n]
"""
from __future__ import annotations
import importlib.util
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from harness import load_engine, run_match  # noqa
load_engine()

TREV, PHAN, BOSS = 879, 878, 1182
ATK = {1267: "Trev:Revenge", 1268: "Trev:Corner", 1266: "Phantump",
       76: "Dudun:LandCrush", 422: "Snorlax", 433: "Cramorant", 74: "Dun:Gnaw", 75: "Dun:Dig"}
T_PLAY, T_ATTACK = 7, 13

attacks = Counter()
boss_prize = []
energy_on_attacker = []
bench_sizes = []


def load_built(d):
    spec = importlib.util.spec_from_file_location("b_" + os.path.basename(d), os.path.join(d, "main.py"))
    m = importlib.util.module_from_spec(spec)
    p = os.getcwd()
    try:
        os.chdir(d); spec.loader.exec_module(m)
    finally:
        os.chdir(p)
    return m.agent


def logging_wrap(agent):
    def a(obs_dict):
        sel = obs_dict.get("select") if isinstance(obs_dict, dict) else None
        out = agent(obs_dict)
        try:
            if sel and sel.get("context") == 0:
                opts = sel.get("option", [])
                if opts and len(opts) != 60:
                    cur = obs_dict["current"]
                    me = cur["players"][cur["yourIndex"]]
                    bench_sizes.append(len(me.get("bench") or []))
                    for ci in out:
                        if not (isinstance(ci, int) and ci < len(opts)):
                            continue
                        o = opts[ci]
                        if o.get("type") == T_ATTACK:
                            attacks[ATK.get(o.get("attackId"), o.get("attackId"))] += 1
                            act0 = (me.get("active") or [None])[0]
                            if act0:
                                energy_on_attacker.append(len(act0.get("energies", [])))
                        elif o.get("type") == T_PLAY:
                            hand = me.get("hand") or []
                            hi = o.get("index")
                            if hi is not None and hi < len(hand) and hand[hi].get("id") == BOSS:
                                boss_prize.append(len(me.get("prize") or []))
        except Exception:
            pass
        return out
    return a


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    v006 = load_built(os.path.join(ROOT, "workspace", "exp012_nonex", "build_v006"))
    me = logging_wrap(v006)
    opp = load_built(os.path.join(ROOT, "workspace", "exp012_nonex", "build_v006"))
    for _ in range(n):
        run_match(me, opp)
    avg = lambda xs: sum(xs) / len(xs) if xs else float("nan")
    tot = sum(attacks.values()) or 1
    print(f"OUR v006 mirror profile over {n} games:")
    print(f"  avg bench size: {avg(bench_sizes):.2f}   (Mogja-W 3.82)")
    print(f"  energies on attacker: {avg(energy_on_attacker):.2f}   (Mogja-W 1.73)")
    print(f"  Boss's Orders plays: {len(boss_prize)} (avg own-prizes-left: {avg(boss_prize):.1f})   (Mogja-W 31 plays @ 3.1)")
    print(f"  attack mix: " + ", ".join(f"{k}={v}({100*v//tot}%)" for k, v in attacks.most_common()))
    print(f"  (Mogja-W: Trev:Revenge 56%, Phantump 36%)")


if __name__ == "__main__":
    main()
