"""Replicate a player's EXACT 60-card decklist from their ladder replays.

Given any submission_id (ours, or a top player's that we reached by traversing
episodes), download that submission's replays, find the owning player's deck in
each game (the len-60 action), and return their MAIN deck = the most frequent
exact 60-card list across games. Outputs a JSON list of 60 card IDs (ready to
drop into a deck.csv / build script) plus a human-readable card breakdown and an
archetype label.

Usage:
  uv run python extract_deck.py <submission_id> [out.json]
e.g. copy charmq (LB #4):
  uv run python extract_deck.py 53858964 ../exp012_nonex/charmq_deck.json

Finding a target submission_id: it appears as an opponent's `submission_id` in
any episode you have (our submissions, or another player's episodes). See
top_meta.py / analyze.py for the traversal, or:
  uv run python -c "from kaggle.api.kaggle_api_extended import KaggleApi; \
    a=KaggleApi(); a.authenticate(); \
    [print(x.submission_id, x.team_name) for e in a.competition_list_episodes(MY_SUB) for x in e.agents]"
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))

COMPETITION = "pokemon-tcg-ai-battle"


def card_map():
    from harness import load_engine
    api, _ = load_engine()
    return {c.cardId: c for c in api.all_card_data()}


def decks_from_replay(rep):
    """{agent_index: deck60} from the first len-60 actions in the replay."""
    decks = {}
    for st in rep.get("steps", []):
        for idx, agent in enumerate(st):
            act = agent.get("action")
            if isinstance(act, list) and len(act) == 60 and idx not in decks:
                decks[idx] = act
        if len(decks) >= 2:
            break
    return decks


def extract(sub_id, raw_dir=None, sleep=0.25):
    """Return (deck60, n_games_with_that_deck, n_total, rows) for the owner of sub_id."""
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi(); api.authenticate()
    if raw_dir is None:
        raw_dir = os.path.join(ROOT, "references", "raw", "replays", f"deck_{sub_id}")
    os.makedirs(raw_dir, exist_ok=True)

    eps = api.competition_list_episodes(sub_id)
    deck_counter = Counter()
    total = 0
    for e in eps:
        path = os.path.join(raw_dir, f"episode-{e.id}-replay.json")
        if not os.path.exists(path):
            try:
                api.competition_episode_replay(e.id, path=raw_dir); time.sleep(sleep)
            except Exception as ex:
                print(f"  skip {e.id}: {ex}"); continue
        tgt = next((a for a in e.agents if a.submission_id == sub_id), None)
        if tgt is None:
            continue
        try:
            rep = json.load(open(path))
            dk = decks_from_replay(rep).get(tgt.index)
        except Exception:
            dk = None
        if dk and len(dk) == 60:
            deck_counter[tuple(sorted(dk))] += 1
            total += 1
    if not deck_counter:
        return None, 0, 0
    main, n = deck_counter.most_common(1)[0]
    return list(main), n, total


def archetype_of(deck, byid):
    """Lightweight archetype label (mirrors analyze.archetype)."""
    cnt = Counter(deck)
    ex_count = sum(n for cid, n in cnt.items() if cid in byid and (byid[cid].ex or byid[cid].megaEx))
    crustle = cnt.get(345, 0) + cnt.get(344, 0)
    names = {byid[cid].name.lower() for cid in cnt if cid in byid}
    has = lambda kw: any(kw in n for n in names)
    if crustle >= 2:
        return "crustle_control"
    if cnt.get(330, 0) >= 1 and ex_count == 0:
        return "sylveon_control"
    if has("dragapult") or has("dreepy"):
        return "dragapult"
    if has("lucario") or has("riolu"):
        return "lucario_ex" if ex_count else "lucario"
    if ex_count == 0:
        return "non_ex_attackers"
    return f"mixed_ex{ex_count}" if ex_count < 6 else "ex_beatdown"


def main():
    if len(sys.argv) < 2:
        print("usage: extract_deck.py <submission_id> [out.json]"); sys.exit(1)
    sub_id = int(sys.argv[1])
    out = sys.argv[2] if len(sys.argv) > 2 else None
    byid = card_map()
    deck, n, total = extract(sub_id)
    if deck is None:
        print(f"no 60-card deck found for submission {sub_id}"); sys.exit(2)

    cnt = Counter(deck)
    arch = archetype_of(deck, byid)
    ex_count = sum(v for cid, v in cnt.items() if cid in byid and (byid[cid].ex or byid[cid].megaEx))
    print(f"submission {sub_id}: main deck used in {n}/{total} games | archetype={arch} | ex-cards={ex_count}")
    print(f"=== 60-card list ===")
    # Pokemon first, then trainers/energy, by count
    from harness import load_engine
    api, _ = load_engine()
    PT = api.CardType.POKEMON
    def sortkey(cid):
        c = byid.get(cid)
        kind = 0 if (c and c.cardType == PT) else 1
        return (kind, -cnt[cid], cid)
    for cid in sorted(cnt, key=sortkey):
        c = byid.get(cid)
        tag = ""
        if c and c.cardType == PT:
            tag = "EX" if (c.ex or c.megaEx) else "  "
        print(f"  x{cnt[cid]} [{tag}] {cid:4d} {c.name if c else '?'}")
    assert sum(cnt.values()) == 60

    if out:
        op = out if os.path.isabs(out) else os.path.join(HERE, out)
        os.makedirs(os.path.dirname(op), exist_ok=True)
        json.dump(deck, open(op, "w"))
        print(f"\nsaved {op}  (drop into a deck.csv / build script)")


if __name__ == "__main__":
    main()
