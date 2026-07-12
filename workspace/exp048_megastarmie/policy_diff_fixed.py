"""exp048 -- decision-diff vs a top player's cached replays, with the VERIFIED
next-step action pairing (steps[t].action responds to steps[t-1]'s obs -- see
exp043v2/exp041's 2026-07-10 finding). policy_diff.py/policy_diff2.py compare
`agent(obs)` at step si against `act` read from the SAME step si, which is
actually the response to obs at si-1 -- this script fixes that by pairing obs
at si with steps[si+1][ti]["action"], reading team index via cached-replay
info.TeamNames (no Kaggle API needed, works entirely offline on a cache
already downloaded by top_meta.py/extract_deck.py).

Usage: uv run python policy_diff_fixed.py <team_name> <deck.json> <cache_tag> [policy.py] [max_games]
  policy.py must expose make_agent(deck) (default: exp007_anti_crustle/anti_crustle.py,
  i.e. generic lucario_v2 piloting the given deck).
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp013_router"))

import policy_diff as PD  # decode_choice / ctx_namer / _area_list reuse


def main():
    team = sys.argv[1] if len(sys.argv) > 1 else "tomatomato"
    deck_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "exp011_meta_watch", "tomatomato_deck.json")
    tag = sys.argv[3] if len(sys.argv) > 3 else "top_tomatomato_0712"
    policy_path = os.path.abspath(sys.argv[4]) if len(sys.argv) > 4 else os.path.join(ROOT, "workspace", "exp007_anti_crustle", "anti_crustle.py")
    max_games = int(sys.argv[5]) if len(sys.argv) > 5 else 10**9

    from harness import load_engine
    api, _ = load_engine()
    OPTT = {int(getattr(api.OptionType, n)): n for n in dir(api.OptionType)
            if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
    NM_OF = {c.cardId: c.name for c in api.all_card_data()}
    name_of = PD.ctx_namer()

    spec = importlib.util.spec_from_file_location("target_policy", policy_path)
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    deck = json.load(open(deck_path))
    agent = pm.make_agent(deck)
    print(f"policy: {os.path.basename(policy_path)}  deck: {os.path.basename(deck_path)}  team: {team}")

    raw_dir = os.path.join(ROOT, "references", "raw", "replays", tag)
    files = sorted(f for f in os.listdir(raw_dir) if f.endswith("replay.json"))

    by_ctx = defaultdict(lambda: [0, 0])
    by_ctx_sem = defaultdict(lambda: [0, 0])
    examples = defaultdict(list)
    total = [0, 0]
    th_pick, our_pick = Counter(), Counter()
    games_done = 0
    seen = set()
    for fn in files:
        if games_done >= max_games:
            break
        try:
            rep = json.load(open(os.path.join(raw_dir, fn)))
        except Exception:
            continue
        epid = rep.get("info", {}).get("EpisodeId")
        if epid in seen:
            continue
        seen.add(epid)
        names = rep.get("info", {}).get("TeamNames") or []
        idxs = [i for i, n in enumerate(names) if n == team]
        if not idxs:
            continue
        steps = rep.get("steps", [])
        for ti in idxs:
            for si, st in enumerate(steps):
                if ti >= len(st):
                    continue
                ag = st[ti]
                if ag.get("status") != "ACTIVE":
                    continue
                obs = ag.get("observation")
                if si + 1 >= len(steps) or ti >= len(steps[si + 1]):
                    continue
                act = steps[si + 1][ti].get("action")
                if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                    continue
                if len(act) == 60:
                    continue
                sel = obs["select"]
                opts = sel.get("option", [])
                if len(opts) < 2:
                    continue
                mn, mx = sel.get("minCount", 1), sel.get("maxCount", 1)
                if not (mn <= len(act) <= mx):
                    continue
                try:
                    ours = agent(obs)
                except Exception:
                    continue
                ctx = name_of(sel.get("context"))
                match = sorted(ours) == sorted(act)
                sem = (sorted(PD.decode_choice(obs, sel, ours, OPTT, NM_OF))
                       == sorted(PD.decode_choice(obs, sel, act, OPTT, NM_OF)))
                by_ctx_sem[ctx][0] += int(sem); by_ctx_sem[ctx][1] += 1
                by_ctx[ctx][0] += int(match); by_ctx[ctx][1] += 1
                total[0] += int(match); total[1] += 1
                if ctx == "TO_HAND":
                    th_pick.update(PD.decode_choice(obs, sel, act, OPTT, NM_OF))
                    our_pick.update(PD.decode_choice(obs, sel, ours, OPTT, NM_OF))
                if not sem and len(examples[ctx]) < 6:
                    examples[ctx].append((PD.decode_choice(obs, sel, act, OPTT, NM_OF),
                                          PD.decode_choice(obs, sel, ours, OPTT, NM_OF)))
        games_done += 1

    print(f"\ngames scanned: {games_done}")
    print(f"=== overall decision match: {total[0]}/{total[1]} = {total[0]/max(total[1],1):.3f} ===")
    print(f"{'context':24s} match  total   rate   sem-rate")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True):
        sm, st = by_ctx_sem[ctx]
        print(f"  {ctx:22s} {m:5d} {t:6d}   {m/max(t,1):.2f}   {sm/max(st,1):.2f}   (mismatch {t-m})")
    print("\n=== top divergence examples (their choice vs ours, decoded) ===")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True)[:8]:
        if examples[ctx]:
            print(f"[{ctx}] (mismatch {t-m}/{t})")
            for their, ours in examples[ctx]:
                print(f"   their={their}  ours={ours}")
    print("\n=== TO_HAND search-target priority: THEY fetch vs WE fetch ===")
    print("  THEIR top picks:", th_pick.most_common(15))
    print("  OUR   top picks:", our_pick.most_common(15))


if __name__ == "__main__":
    main()
