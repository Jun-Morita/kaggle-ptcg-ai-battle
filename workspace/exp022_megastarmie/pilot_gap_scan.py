"""Generalized pilot-gap scanner — find the NEXT gust-style binary leak.

The gust fix (Boss's Orders 0->1.6/game) came from one hand-picked metric. This generalizes
that: decode a top pilot's MAIN (context-0) decisions across all their cached ladder replays,
compute the PER-GAME RATE of every distinguishable action (play <card>, evolve <card>,
attach, retreat, attack <move>), split by WIN/LOSS, and contrast wins-vs-losses. Large W>L
gaps = encodable winning habits; actions present in W but ~0 for us = candidate single-fix
patches (the gust template). Card ids resolved via data/raw/EN_Card_Data.csv.

Usage: uv run python pilot_gap_scan.py <pilot_dirname> [name_substring]
  e.g. uv run python pilot_gap_scan.py top_mogja_j_0624 Mogja
       uv run python pilot_gap_scan.py top_keidroid_0624 keidroid
"""
from __future__ import annotations
import csv
import glob
import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))

# action type codes (from engine option.type)
T_PLAY, T_ATTACH, T_EVOLVE, T_RETREAT, T_ATTACK = 7, 8, 9, 12, 13


def load_names():
    m = {}
    with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
        for row in csv.DictReader(f):
            try:
                m[int(row["Card ID"])] = row["Card Name"]
            except (ValueError, KeyError):
                pass
    return m


def load_move_names():
    m = {}
    with open(os.path.join(ROOT, "data", "raw", "EN_Card_Data.csv")) as f:
        for row in csv.DictReader(f):
            mv = (row.get("Move Name") or "").strip()
            nm = row.get("Card Name") or ""
            if mv:
                m.setdefault(nm + ":" + mv, None)
    return m  # not id-keyed; attacks resolved by attackId below via fallback


def pilot_idx(d, sub):
    tn = (d.get("info") or {}).get("TeamNames") or []
    for i, n in enumerate(tn):
        if sub.lower() in str(n).lower():
            return i
    return None


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    pdir = sys.argv[1]
    sub = sys.argv[2] if len(sys.argv) > 2 else pdir.replace("top_", "").split("_")[0]
    names = load_names()
    cn = lambda cid: names.get(cid, f"#{cid}")

    files = sorted(glob.glob(os.path.join(ROOT, "references", "raw", "replays", pdir, "*.json")))
    rate = {"W": Counter(), "L": Counter()}   # summed counts of each action key
    pres = {"W": Counter(), "L": Counter()}   # games where action used >=1 (presence)
    turns = {"W": 0, "L": 0}                  # total decision-steps (for per-decision norm)
    n = {"W": 0, "L": 0}

    for path in files:
        try:
            d = json.load(open(path))
        except Exception:
            continue
        idx = pilot_idx(d, sub)
        if idx is None:
            continue
        res = d.get("rewards", [0, 0])
        if res[idx] not in (0, 1, -1):
            continue
        tag = "W" if res[idx] == 1 else "L"
        n[tag] += 1
        game_keys = set()
        for st in d.get("steps", []):
            if idx >= len(st):
                continue
            ag = st[idx]
            obs, act = ag.get("observation"), ag.get("action")
            if not isinstance(obs, dict) or not act:
                continue
            sel = obs.get("select")
            if not sel or sel.get("context") != 0:
                continue
            opts = sel.get("option", [])
            if not opts or len(opts) == 60:
                continue
            cur = obs.get("current") or {}
            me = (cur.get("players") or [None, None])[idx]
            if me is None:
                continue
            turns[tag] += 1
            hand = me.get("hand") or []
            for ci in act:
                if not (isinstance(ci, int) and ci < len(opts)):
                    continue
                o = opts[ci]
                t = o.get("type")
                key = None
                if t == T_PLAY:
                    hi = o.get("index")
                    cid = hand[hi].get("id") if (hi is not None and hi < len(hand)) else None
                    key = f"play {cn(cid)}"
                elif t == T_EVOLVE:
                    hi = o.get("index")
                    cid = hand[hi].get("id") if (hi is not None and hi < len(hand)) else None
                    key = f"evolve {cn(cid)}"
                elif t == T_ATTACH:
                    key = "attach energy"
                elif t == T_RETREAT:
                    key = "retreat"
                elif t == T_ATTACK:
                    key = f"attack #{o.get('attackId')}"
                if key:
                    rate[tag][key] += 1
                    game_keys.add(key)
        for k in game_keys:
            pres[tag][k] += 1

    print(f"=== {sub}: {n['W']}W / {n['L']}L games decoded from {pdir} ===\n")
    if n["W"] == 0:
        print("no games matched — check the name substring.")
        return
    keys = set(rate["W"]) | set(rate["L"])
    rows = []
    for k in keys:
        # per-DECISION rate (length-normalized) + presence (% games used >=1)
        pw = rate["W"][k] / turns["W"] if turns["W"] else 0
        pl = rate["L"][k] / turns["L"] if turns["L"] else 0
        prw = 100 * pres["W"][k] / n["W"] if n["W"] else 0
        rows.append((pw - pl, pw, pl, prw, k))
    rows.sort(reverse=True)
    print(f"per-decision rate (length-normalized); pres%=games-with-1+-use (W only)\n")
    print(f"{'action':32s} {'W/dec':>7s} {'L/dec':>7s} {'W-L':>7s} {'pres%':>6s}")
    print("-" * 64)
    for diff, pw, pl, prw, k in rows:
        print(f"{k:32s} {pw:7.3f} {pl:7.3f} {diff:+7.3f} {prw:6.0f}")

    # ---- take-when-legal: distinguishes a DECISION leak from a draw/length gap. ----
    # For each watched card, count how often it was a legal play-option vs how often taken.
    # A low take-rate gap with a big EXPOSURE gap = draw/throughput issue (not patchable by
    # a single rule). A normal exposure but low take-rate = a real gated decision leak (the
    # gust template: Boss's Orders). Pass extra card ids as args 3+ to watch them.
    watch = [int(x) for x in sys.argv[3:]] or [1097, 1152, 1182]  # Night Stretcher, Poke Pad, Boss
    avail = {c: [0, 0] for c in watch}
    for path in files:
        try:
            d = json.load(open(path))
        except Exception:
            continue
        idx = pilot_idx(d, sub)
        if idx is None:
            continue
        for st in d.get("steps", []):
            if idx >= len(st):
                continue
            ag = st[idx]
            obs, act = ag.get("observation"), ag.get("action")
            if not isinstance(obs, dict) or not act:
                continue
            sel = obs.get("select")
            if not sel or sel.get("context") != 0:
                continue
            opts = sel.get("option", [])
            if not opts or len(opts) == 60:
                continue
            cur = obs.get("current") or {}
            me = (cur.get("players") or [None, None])[idx]
            if me is None:
                continue
            hand = me.get("hand") or []
            taken = {i for i in act if isinstance(i, int) and i < len(opts)}
            for oi, o in enumerate(opts):
                if o.get("type") != T_PLAY:
                    continue
                hi = o.get("index")
                cid = hand[hi].get("id") if (hi is not None and hi < len(hand)) else None
                if cid in avail:
                    avail[cid][0] += 1
                    if oi in taken:
                        avail[cid][1] += 1
    print("\ntake-when-legal (exposure = #times a legal play-option; big exposure gap vs us")
    print("= draw/throughput issue; low take-rate at normal exposure = gated decision leak):")
    for cid, (ex, tk) in avail.items():
        r = 100 * tk / ex if ex else 0
        print(f"  {cn(cid):20s}: exposure {ex:5d}, taken {tk:5d}  ({r:.0f}% when legal)")


if __name__ == "__main__":
    main()
