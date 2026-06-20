"""exp011 weekly meta-watch: download our latest submission's ladder replays,
extract each opponent's deck + result, and summarize the current meta.

Usage:
  uv run python analyze.py <submission_id> [tag]
e.g.
  uv run python analyze.py 53846234 0620

Replays are saved (gitignored) to references/raw/replays/<tag>/.
A machine-readable summary is written to results/meta_<tag>.json and a
human summary is printed.
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


def card_map():
    from harness import load_engine
    api, _ = load_engine()
    return {c.cardId: c for c in api.all_card_data()}


def archetype(deck, byid):
    """Heuristic archetype label from a 60-card decklist."""
    cnt = Counter(deck)
    names = {cid: byid[cid].name for cid in cnt if cid in byid}
    has = lambda kw: any(kw.lower() in n.lower() for n in names.values())
    ncard = lambda cid: cnt.get(cid, 0)
    ex_count = sum(n for cid, n in cnt.items() if cid in byid and (byid[cid].ex or byid[cid].megaEx))
    # signature cards
    crustle = ncard(345) + ncard(344)  # Crustle/Dwebble
    sylveon = ncard(330)
    if crustle >= 2:
        return "crustle_control"
    if sylveon >= 1 and ex_count == 0:
        return "sylveon_control"
    if has("Dragapult") or has("Dreepy") or has("Drakloak"):
        return "dragapult"
    if has("Lucario") or has("Riolu"):
        return "lucario_ex" if ex_count else "lucario"
    if ex_count == 0:
        return "non_ex_attackers"
    if ex_count >= 6:
        return "ex_beatdown"
    return f"mixed_ex{ex_count}"


def opp_deck_from_replay(rep, our_sub_id):
    """Return (opp_index, opp_deck, our_reward, opp_team). Deck = the len-60 action."""
    steps = rep.get("steps", [])
    if not steps:
        return None
    info = rep.get("info", {})
    # identify our agent index via reward at the last step
    last = steps[-1]
    rewards = [s.get("reward") for s in last]
    # decks: first step where each agent's action is a list of 60
    decks = {}
    for st in steps:
        for idx, agent in enumerate(st):
            act = agent.get("action")
            if isinstance(act, list) and len(act) == 60 and idx not in decks:
                decks[idx] = act
        if len(decks) >= 2:
            break
    return decks, rewards, info


def analyze_submission(sub_id, tag, api=None, byid=None, verbose=True):
    """Download a submission's ladder replays, return {n_games, by_arch, rows}.
    Reused by meta_watch.py. Writes results/meta_<tag>.json."""
    raw_dir = os.path.join(ROOT, "references", "raw", "replays", tag)
    os.makedirs(raw_dir, exist_ok=True)
    if api is None:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi(); api.authenticate()
    if byid is None:
        byid = card_map()

    eps = api.competition_list_episodes(sub_id)
    if verbose:
        print(f"submission {sub_id}: {len(eps)} episodes")

    rows = []  # (epid, opp_team, opp_arch, result, ex_count)
    for e in eps:
        path = os.path.join(raw_dir, f"episode-{e.id}-replay.json")
        if not os.path.exists(path):
            try:
                api.competition_episode_replay(e.id, path=raw_dir)
            except Exception as ex:
                print(f"  skip {e.id}: {ex}")
                continue
            time.sleep(0.3)
        # map agents -> team & reward
        our_idx = next((a.index for a in e.agents if a.submission_id == sub_id), None)
        opp = next((a for a in e.agents if a.submission_id != sub_id), None)
        our = next((a for a in e.agents if a.submission_id == sub_id), None)
        if our is None or opp is None:
            continue
        our_reward = our.reward
        result = "W" if our_reward == 1 else ("L" if our_reward == -1 else "D")
        try:
            with open(path) as f:
                rep = json.load(f)
            decks, rewards, info = opp_deck_from_replay(rep, sub_id)
            opp_deck = decks.get(opp.index, [])
            arch = archetype(opp_deck, byid) if opp_deck else "unknown"
            exc = sum(1 for cid in opp_deck if cid in byid and (byid[cid].ex or byid[cid].megaEx))
        except Exception as ex:
            arch, exc, opp_deck = f"parse_err:{ex}", -1, []
        rows.append({"epid": e.id, "opp": opp.team_name, "arch": arch,
                     "result": result, "ex_in_deck": exc,
                     "opp_deck_top": [byid[c].name for c in dict.fromkeys(opp_deck) if c in byid][:12]})

    # aggregate
    by_arch = defaultdict(lambda: [0, 0, 0])  # W,L,D
    by_opp = defaultdict(lambda: [0, 0, 0])
    for r in rows:
        i = {"W": 0, "L": 1, "D": 2}[r["result"]]
        by_arch[r["arch"]][i] += 1
        by_opp[r["opp"]][i] += 1

    if verbose:
        print(f"\n=== {len(rows)} games by opponent archetype (our W-L-D) ===")
        for a, (w, l, d) in sorted(by_arch.items(), key=lambda x: -sum(x[1])):
            n = w + l + d
            print(f"  {a:20s} {w}-{l}-{d}  (wr={w/max(n,1):.2f}, n={n})")
        print(f"\n=== by opponent team ===")
        for o, (w, l, d) in sorted(by_opp.items(), key=lambda x: -sum(x[1])):
            print(f"  {o[:28]:28s} {w}-{l}-{d}")

    out = {"submission_id": sub_id, "tag": tag, "n_games": len(rows),
           "by_arch": {a: list(v) for a, v in by_arch.items()},
           "rows": rows}
    op = os.path.join(HERE, "results", f"meta_{tag}.json")
    os.makedirs(os.path.dirname(op), exist_ok=True)
    json.dump(out, open(op, "w"), indent=2, ensure_ascii=False)
    if verbose:
        print(f"\nwrote {op}")
    return out


def main():
    if len(sys.argv) < 2:
        print("usage: analyze.py <submission_id> [tag]")
        sys.exit(1)
    sub_id = int(sys.argv[1])
    tag = sys.argv[2] if len(sys.argv) > 2 else time.strftime("%m%d")
    analyze_submission(sub_id, tag)


if __name__ == "__main__":
    main()
