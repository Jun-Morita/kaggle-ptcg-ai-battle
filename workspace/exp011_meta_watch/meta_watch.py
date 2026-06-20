"""Weekly meta-watch in one command (the operational loop).

Auto-detects our latest COMPLETE submission, analyzes its ladder replays
(archetype-level W-L + meta share), compares to the PREVIOUS snapshot to flag
rotations, and prints the current LB top. Backs the /meta-watch skill.

Usage:
  uv run python meta_watch.py [submission_id]
(omit submission_id to auto-pick our latest scored submission)
"""
from __future__ import annotations
import glob
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, HERE)

COMPETITION = "pokemon-tcg-ai-battle"


def latest_submission(api):
    subs = api.competition_submissions(COMPETITION)
    for s in subs:  # newest first
        if str(s.public_score or "").strip() not in ("", "None"):
            return s
    return subs[0] if subs else None


def shares(by_arch):
    total = sum(sum(v) for v in by_arch.values()) or 1
    return {a: sum(v) / total for a, v in by_arch.items()}


def prev_snapshot(cur_tag):
    """Most recent results/meta_*.json that isn't the current tag."""
    files = sorted(glob.glob(os.path.join(HERE, "results", "meta_*.json")), key=os.path.getmtime, reverse=True)
    for f in files:
        if f.endswith(f"meta_{cur_tag}.json"):
            continue
        try:
            return json.load(open(f)), os.path.basename(f)
        except Exception:
            continue
    return None, None


def main():
    from kaggle.api.kaggle_api_extended import KaggleApi
    from analyze import analyze_submission, card_map
    api = KaggleApi(); api.authenticate()

    if len(sys.argv) > 1:
        sub_id = int(sys.argv[1])
    else:
        s = latest_submission(api)
        sub_id = int(s.ref)
        print(f"latest scored submission: {sub_id} (LB {s.public_score}) — {str(s.description)[:60]}")

    tag = time.strftime("%m%d") + f"_{sub_id}"
    byid = card_map()
    cur = analyze_submission(sub_id, tag, api=api, byid=byid, verbose=True)

    # --- rotation detection vs previous snapshot (sample-size aware) ---
    MIN_GAMES = 15
    prev, prev_name = prev_snapshot(tag)
    cur_n = cur["n_games"]
    if cur_n < MIN_GAMES:
        print(f"\n(only {cur_n} games on this submission — too few for reliable rotation "
              f"detection; need >= {MIN_GAMES}. Re-run after it plays more, or pass a more "
              f"converged submission_id.)")
    elif prev:
        prev_n = prev.get("n_games", 0)
        cs, ps = shares(cur["by_arch"]), shares(prev.get("by_arch", {}))
        keys = sorted(set(cs) | set(ps), key=lambda k: -cs.get(k, 0))
        print(f"\n=== meta shift vs {prev_name} (n={prev_n}) — share Δ ===")
        rotated = False
        for k in keys:
            d = cs.get(k, 0) - ps.get(k, 0)
            flag = "  <== shift" if abs(d) >= 0.15 else ""
            if abs(d) >= 0.15:
                rotated = True
            print(f"  {k:20s} {ps.get(k,0):.0%} -> {cs.get(k,0):.0%}  ({d:+.0%}){flag}")
        if prev_n < MIN_GAMES:
            print(f"(previous snapshot has only {prev_n} games — treat shifts as tentative.)")
        print("ROTATION DETECTED — consider a counter submission." if rotated
              else "No major rotation (>=15% share change). Hold / monitor.")
    else:
        print("\n(no previous snapshot to diff against)")

    # --- LB top ---
    print("\n=== LB top 8 ===")
    try:
        lb = api.competition_leaderboard_view(COMPETITION)[:8]
        for r in lb:
            print(f"  {str(getattr(r,'team_name','?'))[:26]:26s} {getattr(r,'score','?')}")
    except Exception as ex:
        print(f"  (leaderboard fetch failed: {ex}; use `kaggle competitions leaderboard {COMPETITION} --show`)")


if __name__ == "__main__":
    main()
