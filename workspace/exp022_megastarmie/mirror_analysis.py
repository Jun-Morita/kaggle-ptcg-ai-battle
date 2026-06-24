"""Extract Mogja(#3)'s MIRROR piloting rules — same deck as ours, but 0.68 vs our 0.40.

Mogja runs our EXACT non-ex deck. Decode Mogja's side (identified by team name) across
all mirror games, aggregate the piloting choices, and contrast WINS vs LOSSES to surface
concrete, encodable rules for our weakest matchup (the non-ex mirror, 26% of field).
Usage: uv run python mirror_analysis.py
"""
from __future__ import annotations
import glob
import json
import os
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
REPL = os.path.join(ROOT, "references", "raw", "replays", "top_mogja_j_0624")

TREV, PHAN, DUDU, DUN, SNOR, CRAM = 879, 878, 66, 65, 304, 311
BOSS, CHOICE_BAND = 1182, 1171
ATK = {1267: "Trev:Revenge(1e,30)", 1268: "Trev:Corner(3e,90)", 1266: "Phantump(10)",
       76: "Dudun:LandCrush(90)", 422: "Snorlax:DynPress(140)", 433: "Cramorant(120)",
       74: "Dun:Gnaw", 75: "Dun:Dig"}
T_PLAY, T_ATTACH, T_EVOLVE, T_ATTACK, T_RETREAT = 7, 8, 9, 13, 12


def mogja_idx(d):
    tn = (d.get("info") or {}).get("TeamNames") or []
    for i, n in enumerate(tn):
        if "Mogja" in str(n):
            return i
    return None


def pkmn(player, area, idx):
    if area == 4:
        a = player.get("active") or []
        return a[0] if a else None
    if area == 5:
        b = player.get("bench") or []
        return b[idx] if idx < len(b) else None
    return None


def analyze():
    files = sorted(glob.glob(os.path.join(REPL, "*.json")))
    agg = {"W": Counter(), "L": Counter()}
    attacks = {"W": Counter(), "L": Counter()}
    bench_sizes = {"W": [], "L": []}
    boss_prize = {"W": [], "L": []}        # own prizes-left when Boss's Orders played
    first_attack_turn = {"W": [], "L": []}
    energy_on_attacker = {"W": [], "L": []}  # energies on the active when it attacked
    n = {"W": 0, "L": 0}

    for path in files:
        d = json.load(open(path))
        idx = mogja_idx(d)
        if idx is None:
            continue
        res = d.get("rewards", [0, 0])
        won = res[idx] == 1
        tag = "W" if won else "L"
        # is this a mirror? opponent deck has Trevenant/Phantump
        steps = d["steps"]
        opp_deck = None
        for st in steps:
            a = st[1 - idx].get("action")
            if isinstance(a, list) and len(a) == 60:
                opp_deck = a
        if not opp_deck or not (TREV in opp_deck or PHAN in opp_deck):
            continue  # only mirror games
        n[tag] += 1
        seen_attack = False
        for st in steps:
            ag = st[idx]
            obs = ag.get("observation")
            act = ag.get("action")
            if not isinstance(obs, dict) or not act:
                continue
            sel = obs.get("select")
            if not sel or sel.get("context") != 0:
                continue
            opts = sel.get("option", [])
            if len(opts) == 60:
                continue
            cur = obs["current"]
            me = cur["players"][idx]
            turn = cur.get("turn", 0)
            bench_sizes[tag].append(len(me.get("bench") or []))
            for ci in act:
                if not (isinstance(ci, int) and ci < len(opts)):
                    continue
                o = opts[ci]
                t = o.get("type")
                if t == T_ATTACK:
                    aid = o.get("attackId")
                    attacks[tag][ATK.get(aid, aid)] += 1
                    act0 = (me.get("active") or [None])[0]
                    if act0:
                        energy_on_attacker[tag].append(len(act0.get("energies", [])))
                    if not seen_attack:
                        first_attack_turn[tag].append(turn)
                        seen_attack = True
                elif t == T_PLAY:
                    hand = me.get("hand") or []
                    hi = o.get("index")
                    cid = hand[hi].get("id") if (hi is not None and hi < len(hand)) else None
                    if cid == BOSS:
                        boss_prize[tag].append(len(me.get("prize") or []))
                    agg[tag][f"play_{cid}"] += 1
                elif t == T_RETREAT:
                    agg[tag]["retreat"] += 1

    def avg(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    print(f"Mogja MIRROR games decoded: {n['W']}W / {n['L']}L\n")
    for tag in ("W", "L"):
        print(f"=== {tag} ({n[tag]} games) ===")
        print(f"  avg bench size: {avg(bench_sizes[tag]):.2f}")
        print(f"  first-attack turn: {avg(first_attack_turn[tag]):.1f}")
        print(f"  energies on attacker when attacking: {avg(energy_on_attacker[tag]):.2f}")
        print(f"  Boss's Orders plays: {len(boss_prize[tag])} (avg own-prizes-left when used: {avg(boss_prize[tag]):.1f})")
        tot = sum(attacks[tag].values()) or 1
        print(f"  attack mix: " + ", ".join(f"{k}={v}({100*v//tot}%)" for k, v in attacks[tag].most_common()))
        print(f"  retreats: {agg[tag]['retreat']}")
        print()


if __name__ == "__main__":
    analyze()
