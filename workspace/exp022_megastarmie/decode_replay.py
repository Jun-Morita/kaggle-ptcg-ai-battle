"""Decode an expert player's decision sequence from a ladder replay (raw dict, no engine).

Prints, for the target agent's MAIN turns, the human-readable actions they took:
energy ATTACH -> which Pokemon (and its energy count), EVOLVE -> to what, ATTACK -> which
attack on which target, plus board/prize state. Used to extract tomatomato's Mega Starmie
piloting "knack" (when to concentrate energy, when to Nebula Beam, how they beat the wall).
Usage: uv run python decode_replay.py <episode.json> [agent_index]
"""
from __future__ import annotations
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OPT = {0: "NUMBER", 1: "YES", 2: "NO", 3: "CARD", 4: "TOOL", 5: "ENERGY_CARD", 6: "ENERGY",
       7: "PLAY", 8: "ATTACH", 9: "EVOLVE", 10: "ABILITY", 11: "DISCARD", 12: "RETREAT",
       13: "ATTACK", 14: "END", 15: "SKILL", 16: "COND"}
AREA = {1: "DECK", 2: "HAND", 3: "DISC", 4: "ACTIVE", 5: "BENCH", 6: "PRIZE", 7: "STADIUM",
        8: "ENERGY", 9: "TOOL", 10: "PRE_EVO", 11: "PLAYER", 12: "LOOK"}


def card_names():
    m = {}
    with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
        for row in csv.DictReader(f):
            try:
                m[int(row["Card ID"])] = row["Card Name"]
            except (ValueError, KeyError):
                pass
    return m


def attack_names():
    """attackId -> name, via the engine."""
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
    from harness import load_engine
    load_engine()
    from cg import api
    return {a.attackId: a.name for a in api.all_attack()}


def pokemon_str(p, names):
    if not isinstance(p, dict):
        return "?"
    cid = p.get("id")
    e = len(p.get("energies", []) or [])
    hp = p.get("hp", "?")
    dmg = p.get("damage", 0)
    return f"{names.get(cid, cid)}[{e}e,{hp-dmg}/{hp}hp]"


def board(obs, names):
    cur = obs.get("current") or {}
    yi = cur.get("yourIndex", 0)
    players = cur.get("players") or [{}, {}]
    me = players[yi] if yi < len(players) else {}
    opp = players[1 - yi] if len(players) > 1 else {}
    act = me.get("active") or []
    bench = me.get("bench") or []
    a = pokemon_str(act[0], names) if act else "-"
    b = ", ".join(pokemon_str(x, names) for x in bench if x)
    oact = (opp.get("active") or [])
    o = pokemon_str(oact[0], names) if oact else "-"
    return a, b, o, len(me.get("prize") or []), len(opp.get("prize") or []), cur.get("turn", "?")


def decode(path, target_idx, names, atk):
    d = json.load(open(path))
    steps = d["steps"]
    print(f"\n===== {os.path.basename(path)} | agent {target_idx} | rewards={d.get('rewards')} =====")
    last_turn = None
    for si, st in enumerate(steps):
        ag = st[target_idx]
        obs = ag.get("observation")
        act = ag.get("action")
        if not isinstance(obs, dict):
            continue
        sel = obs.get("select")
        if not sel or not act:
            continue
        opts = sel.get("option", [])
        if len(opts) == 60:
            continue
        chosen = [opts[i] for i in act if isinstance(i, int) and i < len(opts)]
        if not chosen:
            continue
        kinds = [OPT.get(o.get("type"), o.get("type")) for o in chosen]
        if not any(k in ("ATTACH", "EVOLVE", "ATTACK", "RETREAT") for k in kinds):
            continue  # focus on the piloting verbs (skip pure draws/plays)
        a, b, oact, myp, oppp, turn = board(obs, names)
        desc = []
        for o in chosen:
            t = OPT.get(o.get("type"))
            if t == "ATTACH":
                desc.append(f"ATTACH->{AREA.get(o.get('inPlayArea'))}#{o.get('inPlayIndex')}")
            elif t == "EVOLVE":
                desc.append(f"EVOLVE@{AREA.get(o.get('inPlayArea'))}#{o.get('inPlayIndex')}")
            elif t == "ATTACK":
                aid = o.get("attackId")
                desc.append(f"*** ATTACK [{atk.get(aid, aid)}] ***")
            elif t == "RETREAT":
                desc.append("RETREAT")
            else:
                desc.append(t)
        if turn != last_turn:
            print(f" --- turn {turn} | prize me{myp}/opp{oppp} | OPP active={oact}")
            last_turn = turn
        print(f"      me: act={a} bench=[{b}]")
        print(f"        -> {', '.join(desc)}")


def main():
    path = sys.argv[1]
    names = card_names()
    atk = attack_names()
    if not os.path.isabs(path):
        path = os.path.join(HERE, path)
    if len(sys.argv) > 2:
        idx = int(sys.argv[2])
    else:
        d = json.load(open(path))
        idx = 0
        for st in d["steps"]:
            for i in (0, 1):
                a = st[i].get("action")
                if isinstance(a, list) and len(a) == 60 and (1031 in a or 861 in a):
                    idx = i
        print(f"(auto-detected Mega-Starmie agent = {idx})")
    decode(path, idx, names, atk)


if __name__ == "__main__":
    main()
