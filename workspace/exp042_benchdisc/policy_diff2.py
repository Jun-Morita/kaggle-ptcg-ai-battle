"""exp042 -- policy_diff with a SELECTABLE policy (exp013's policy_diff.py
hardcodes router/v008; comparing a top player against a 3-generations-old
baseline nearly cost us a wrong conclusion -- the discipline patch is already
in the v010+ chain via gust_policy importing discipline_policy).

Usage:
  REVENGE_BONUS=50 uv run python policy_diff2.py <sub_id> <deck.json> <max_eps> <policy.py>
Replays are reused from references/raw/replays/diff_<sub_id>/ (downloaded by a
prior policy_diff run); missing ones are fetched.
"""
from __future__ import annotations
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp013_router"))

import policy_diff as PD  # reuse decode helpers / ctx namer


def main():
    if len(sys.argv) < 5:
        print(__doc__); sys.exit(1)
    sub_id = int(sys.argv[1])
    deck_path = sys.argv[2]
    max_eps = int(sys.argv[3])
    policy_path = os.path.abspath(sys.argv[4])

    from harness import load_engine
    api, _ = load_engine()
    OPTT = {int(getattr(api.OptionType, n)): n for n in dir(api.OptionType)
            if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
    NM_OF = {c.cardId: c.name for c in api.all_card_data()}
    name_of = PD.ctx_namer()
    th_pick, our_pick = Counter(), Counter()

    spec = importlib.util.spec_from_file_location("target_policy", policy_path)
    pm = importlib.util.module_from_spec(spec); spec.loader.exec_module(pm)
    deck = json.load(open(deck_path))
    agent = pm.make_agent(deck)
    print(f"policy: {os.path.basename(policy_path)} (env REVENGE_BONUS={os.environ.get('REVENGE_BONUS')})")

    from kaggle.api.kaggle_api_extended import KaggleApi
    kapi = KaggleApi(); kapi.authenticate()
    raw_dir = os.path.join(ROOT, "references", "raw", "replays", f"diff_{sub_id}")
    os.makedirs(raw_dir, exist_ok=True)
    eps = kapi.competition_list_episodes(sub_id)[:max_eps]
    print(f"target {sub_id}: diffing on {len(eps)} of their games")

    by_ctx = defaultdict(lambda: [0, 0])
    by_ctx_sem = defaultdict(lambda: [0, 0])
    examples = defaultdict(list)
    total = [0, 0]
    for e in eps:
        path = os.path.join(raw_dir, f"episode-{e.id}-replay.json")
        if not os.path.exists(path):
            try:
                kapi.competition_episode_replay(e.id, path=raw_dir); time.sleep(0.25)
            except Exception as ex:
                print(f"  skip {e.id}: {ex}"); continue
        tgt = next((a for a in e.agents if a.submission_id == sub_id), None)
        if tgt is None:
            continue
        ti = tgt.index
        try:
            rep = json.load(open(path))
        except Exception:
            continue
        for st in rep.get("steps", []):
            if ti >= len(st):
                continue
            ag = st[ti]
            if ag.get("status") != "ACTIVE":
                continue
            obs = ag.get("observation")
            act = ag.get("action")
            if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                continue
            sel = obs["select"]
            opts = sel.get("option", [])
            if len(opts) < 2:
                continue
            if not (sel.get("minCount", 1) <= len(act) <= sel.get("maxCount", 1)):
                continue
            try:
                ours = agent(obs)
            except Exception:
                continue
            ctx = name_of(sel.get("context"))
            match = sorted(ours) == sorted(act)
            # semantic match: same decoded card-name multiset (two copies of the
            # same card at different option indices should count as agreement)
            sem = (sorted(PD.decode_choice(obs, sel, ours, OPTT, NM_OF))
                   == sorted(PD.decode_choice(obs, sel, act, OPTT, NM_OF)))
            by_ctx_sem[ctx][0] += int(sem); by_ctx_sem[ctx][1] += 1
            by_ctx[ctx][0] += int(match); by_ctx[ctx][1] += 1
            total[0] += int(match); total[1] += 1
            if ctx == "TO_HAND":
                th_pick.update(PD.decode_choice(obs, sel, act, OPTT, NM_OF))
                our_pick.update(PD.decode_choice(obs, sel, ours, OPTT, NM_OF))
            if not match and len(examples[ctx]) < 5:
                examples[ctx].append((PD.decode_choice(obs, sel, act, OPTT, NM_OF),
                                      PD.decode_choice(obs, sel, ours, OPTT, NM_OF)))

    print(f"\n=== overall decision match: {total[0]}/{total[1]} = {total[0]/max(total[1],1):.3f} ===")
    print(f"{'context':24s} match  total   rate   sem-rate")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True):
        sm, st = by_ctx_sem[ctx]
        print(f"  {ctx:22s} {m:5d} {t:6d}   {m/max(t,1):.2f}   {sm/max(st,1):.2f}   (mismatch {t-m})")
    print("\n=== top divergence examples (their choice vs ours, decoded) ===")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True)[:6]:
        if examples[ctx]:
            print(f"[{ctx}] (mismatch {t-m}/{t})")
            for their, ours in examples[ctx]:
                print(f"   their={their}  ours={ours}")
    print("\n=== TO_HAND search-target priority: THEY fetch vs WE fetch ===")
    print("  THEIR top picks:", th_pick.most_common(12))
    print("  OUR   top picks:", our_pick.most_common(12))


if __name__ == "__main__":
    main()
