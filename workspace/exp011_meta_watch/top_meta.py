"""Analyze the TOP of the ladder by traversing a high-rated player's replays.

Given a high-rated submission_id (e.g. a top-LB team we faced), download their
episodes and extract BOTH decks per game: the target's own deck (what a top team
runs) and each opponent's deck (the rest of the top field), plus the target's
win/loss by matchup. This reveals the top-meta archetype distribution.

Usage:
  uv run python top_meta.py <submission_id> [tag]
e.g. charmq (LB #4):
  uv run python top_meta.py 53858964 charmq
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
from analyze import card_map, archetype  # reuse  # noqa


def decks_from_replay(rep):
    """Return {agent_index: deck60} from the first len-60 actions."""
    decks = {}
    for st in rep.get("steps", []):
        for idx, agent in enumerate(st):
            act = agent.get("action")
            if isinstance(act, list) and len(act) == 60 and idx not in decks:
                decks[idx] = act
        if len(decks) >= 2:
            break
    return decks


def main():
    if len(sys.argv) < 2:
        print("usage: top_meta.py <submission_id> [tag]"); sys.exit(1)
    sub_id = int(sys.argv[1])
    tag = sys.argv[2] if len(sys.argv) > 2 else str(sub_id)
    raw_dir = os.path.join(ROOT, "references", "raw", "replays", f"top_{tag}")
    os.makedirs(raw_dir, exist_ok=True)

    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    byid = card_map()
    eps = api.competition_list_episodes(sub_id)
    print(f"target submission {sub_id} ({tag}): {len(eps)} episodes")

    own_arch = Counter()           # target's own archetype across games
    own_deck_names = Counter()     # target's card frequency (to read its decklist)
    opp_arch = defaultdict(lambda: [0, 0, 0])  # opp archetype -> target W,L,D
    rows = []
    for e in eps:
        path = os.path.join(raw_dir, f"episode-{e.id}-replay.json")
        if not os.path.exists(path):
            try:
                api.competition_episode_replay(e.id, path=raw_dir); time.sleep(0.25)
            except Exception as ex:
                print(f"  skip {e.id}: {ex}"); continue
        tgt = next((a for a in e.agents if a.submission_id == sub_id), None)
        opp = next((a for a in e.agents if a.submission_id != sub_id), None)
        if tgt is None or opp is None:
            continue
        res = "W" if tgt.reward == 1 else ("L" if tgt.reward == -1 else "D")
        try:
            rep = json.load(open(path))
            decks = decks_from_replay(rep)
            tgt_deck = decks.get(tgt.index, [])
            opp_deck = decks.get(opp.index, [])
            ta = archetype(tgt_deck, byid) if tgt_deck else "unknown"
            oa = archetype(opp_deck, byid) if opp_deck else "unknown"
            own_arch[ta] += 1
            for c in tgt_deck:
                if c in byid:
                    own_deck_names[byid[c].name] += 1
        except Exception as ex:
            oa = f"parse_err"; opp_deck = []
        i = {"W": 0, "L": 1, "D": 2}[res]
        opp_arch[oa][i] += 1
        rows.append({"epid": e.id, "opp": opp.team_name, "opp_arch": oa, "result": res,
                     "opp_deck_top": [byid[c].name for c in dict.fromkeys(opp_deck) if c in byid][:10]})

    print(f"\n=== {tag}'s OWN archetype across {sum(own_arch.values())} games ===")
    for a, n in own_arch.most_common():
        print(f"  {a:20s} {n}")
    print(f"\n=== {tag}'s decklist (most frequent cards) ===")
    for nm, cnt in own_deck_names.most_common(24):
        print(f"  x{cnt//max(sum(own_arch.values()),1):<2d} {nm}")
    print(f"\n=== {tag}'s record vs opponent archetype (W-L-D) ===")
    for a, (w, l, d) in sorted(opp_arch.items(), key=lambda x: -sum(x[1])):
        n = w + l + d
        print(f"  {a:20s} {w}-{l}-{d}  (wr={w/max(n,1):.2f}, n={n})")

    out = {"submission_id": sub_id, "tag": tag,
           "own_arch": dict(own_arch),
           "opp_arch": {a: v for a, v in opp_arch.items()}, "rows": rows}
    op = os.path.join(HERE, "results", f"top_{tag}.json")
    json.dump(out, open(op, "w"), indent=2, ensure_ascii=False)
    print(f"\nwrote {op}")


if __name__ == "__main__":
    main()
