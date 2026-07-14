"""exp054-C -- decision-match of silver-band LO players (same 60/60 deck) vs OUR pilot.

If they run the unmodified public notebook pilot, match ~= 1.0 -> their LB
(965/938/923) estimates OUR stock fixed point directly. If lower, the decoded
divergences are patch intel (same-deck better-pilot lever).

Usage: uv run python diff_silver_lo.py [player_substring]
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WS = os.path.join(ROOT, "workspace")
for p in (os.path.join(WS, "exp001_harness"), os.path.join(WS, "exp013_router"),
          os.path.join(WS, "exp053_bandpool")):
    sys.path.insert(0, p)

from harness import load_engine
api, _ = load_engine()
import policy_diff as PD
OPTT = {int(getattr(api.OptionType, n)): n for n in dir(api.OptionType)
        if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
NM_OF = {c.cardId: c.name for c in api.all_card_data()}
name_of = PD.ctx_namer()

LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")


def load_lo_module():
    spec = importlib.util.spec_from_file_location("lo_diff", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else ""
    games = json.load(open(os.path.join(HERE, "silver_lo_players.json")))
    games = [g for g in games if want.lower() in g["player"].lower() and g["overlap"] == 60]
    print(f"{len(games)} games (players: {Counter(g['player'] for g in games)})")
    mod = load_lo_module()
    base = os.path.join(ROOT, "references", "raw", "replays")

    by_ctx = defaultdict(lambda: [0, 0])
    by_ctx_sem = defaultdict(lambda: [0, 0])
    examples = defaultdict(list)
    total = [0, 0]
    for g in games:
        rep = json.load(open(os.path.join(base, g["dir"], g["file"])))
        ti = g["seat"]
        for st in rep.get("steps", []):
            if ti >= len(st):
                continue
            ag = st[ti]
            if ag.get("status") != "ACTIVE":
                continue
            obs, act = ag.get("observation"), ag.get("action")
            if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                continue
            sel = obs["select"]
            opts = sel.get("option", [])
            if len(opts) < 2:
                continue
            if not (sel.get("minCount", 1) <= len(act) <= sel.get("maxCount", 1)):
                continue
            try:
                ours = mod.agent(obs)
            except Exception:
                continue
            if not isinstance(ours, list):
                continue
            ctx = name_of(sel.get("context"))
            match = sorted(ours) == sorted(act)
            sem = (sorted(PD.decode_choice(obs, sel, ours, OPTT, NM_OF))
                   == sorted(PD.decode_choice(obs, sel, act, OPTT, NM_OF)))
            by_ctx[ctx][0] += int(match); by_ctx[ctx][1] += 1
            by_ctx_sem[ctx][0] += int(sem); by_ctx_sem[ctx][1] += 1
            total[0] += int(match); total[1] += 1
            if not sem and len(examples[ctx]) < 4:
                examples[ctx].append((PD.decode_choice(obs, sel, act, OPTT, NM_OF),
                                      PD.decode_choice(obs, sel, ours, OPTT, NM_OF)))

    print(f"\n=== overall decision match vs OUR stock LO pilot: "
          f"{total[0]}/{total[1]} = {total[0]/max(total[1],1):.3f} ===")
    print(f"{'context':24s} match  total   rate  sem-rate")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True):
        sm, stt = by_ctx_sem[ctx]
        print(f"  {ctx:22s} {m:5d} {t:6d}   {m/max(t,1):.2f}   {sm/max(stt,1):.2f}")
    print("\n=== divergences (their choice vs ours, decoded, sem-mismatch only) ===")
    for ctx in examples:
        print(f"[{ctx}]")
        for their, ours_d in examples[ctx]:
            print(f"  them: {their}\n  us  : {ours_d}")


if __name__ == "__main__":
    main()
