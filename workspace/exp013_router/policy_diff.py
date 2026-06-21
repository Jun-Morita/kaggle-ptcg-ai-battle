"""Decision-diff: run OUR policy on a top player's actual game states and compare.

For a target submission_id (a top player), download their replays, and at every
decision point where THEY had a choice, feed their observation (their POV obs_dict)
to our policy (loaded with THEIR deck) and compare our chosen option(s) to what
they actually did. Aggregates a match rate overall and by SelectContext, and lists
the contexts where we diverge most (= concrete mimic-patch targets). Interpret
divergences with the 6 lenses in references/knowledge/ptcg_strategy.md.

Usage:
  uv run python policy_diff.py <submission_id> [deck.json] [max_episodes]
e.g. charmq (our-style non-ex deck):
  uv run python policy_diff.py 53858964 ../exp012_nonex/charmq_deck.json 25
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, HERE)

COMPETITION = "pokemon-tcg-ai-battle"


def ctx_namer():
    from harness import load_engine
    api, _ = load_engine()
    SC = api.SelectContext
    m = {int(getattr(SC, n)): n for n in dir(SC) if not n.startswith("_") and isinstance(getattr(SC, n), int)}
    return lambda i: m.get(i, f"ctx{i}")


def opt_types(select, api_optt):
    """Multiset of option type names in this select (for categorizing)."""
    names = []
    for o in select.get("option", []):
        t = o.get("type")
        names.append(api_optt.get(t, str(t)))
    return names


def _area_list(obs, area, pi):
    cur = obs.get("current", {})
    pl = cur.get("players", [{}, {}])[pi] if pi < len(cur.get("players", [])) else {}
    return {1: obs.get("select", {}).get("deck", []), 2: pl.get("hand", []),
            3: pl.get("discard", []), 4: pl.get("active", []), 5: pl.get("bench", []),
            6: pl.get("prize", []), 7: cur.get("stadium", []), 12: cur.get("looking", [])}.get(area)


def decode(obs, opt, optt, nm_of):
    """Human label for an option: 'TYPE:CardName'."""
    t = optt.get(opt.get("type"), str(opt.get("type")))
    lst = _area_list(obs, opt.get("area"), opt.get("playerIndex", 0) or 0)
    idx = opt.get("index")
    if lst is not None and isinstance(idx, int) and 0 <= idx < len(lst):
        c = lst[idx]
        if isinstance(c, dict):
            return f"{t}:{nm_of.get(c.get('id'), c.get('id'))}"
    return t


def decode_choice(obs, sel, idxs, optt, nm_of):
    opts = sel.get("option", [])
    return [decode(obs, opts[i], optt, nm_of) for i in idxs if 0 <= i < len(opts)]


def main():
    if len(sys.argv) < 2:
        print("usage: policy_diff.py <submission_id> [deck.json] [max_episodes]"); sys.exit(1)
    sub_id = int(sys.argv[1])
    deck_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "exp012_nonex", "charmq_deck.json")
    max_eps = int(sys.argv[3]) if len(sys.argv) > 3 else 25

    from harness import load_engine
    api, _ = load_engine()
    OPTT = {int(getattr(api.OptionType, n)): n for n in dir(api.OptionType)
            if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
    NM_OF = {c.cardId: c.name for c in api.all_card_data()}
    name_of = ctx_namer()
    from collections import Counter
    th_pick, our_pick = Counter(), Counter()   # TO_HAND search-target priority (their vs ours)

    import router_policy as R
    deck = json.load(open(deck_path))
    agent = R.make_agent(deck)  # our policy piloting THEIR deck

    from kaggle.api.kaggle_api_extended import KaggleApi
    kapi = KaggleApi(); kapi.authenticate()
    raw_dir = os.path.join(ROOT, "references", "raw", "replays", f"diff_{sub_id}")
    os.makedirs(raw_dir, exist_ok=True)
    eps = kapi.competition_list_episodes(sub_id)[:max_eps]
    print(f"target {sub_id}: diffing our policy on {len(eps)} of their games")

    by_ctx = defaultdict(lambda: [0, 0])  # ctx -> [match, total]
    examples = defaultdict(list)          # ctx -> [(their, ours, opttypes)]
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
            if ag.get("status") != "ACTIVE":   # only the acting player's real decisions
                continue
            obs = ag.get("observation")
            act = ag.get("action")
            if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                continue
            sel = obs["select"]
            opts = sel.get("option", [])
            if len(opts) < 2:    # no real choice
                continue
            if not (sel.get("minCount", 1) <= len(act) <= sel.get("maxCount", 1)):
                continue         # skip malformed/no-op rows
            try:
                ours = agent(obs)
            except Exception:
                continue
            ctx = name_of(sel.get("context"))
            match = sorted(ours) == sorted(act)
            by_ctx[ctx][0] += int(match); by_ctx[ctx][1] += 1
            total[0] += int(match); total[1] += 1
            if ctx == "TO_HAND":
                th_pick.update(decode_choice(obs, sel, act, OPTT, NM_OF))
                our_pick.update(decode_choice(obs, sel, ours, OPTT, NM_OF))
            if not match and len(examples[ctx]) < 5:
                examples[ctx].append((decode_choice(obs, sel, act, OPTT, NM_OF),
                                      decode_choice(obs, sel, ours, OPTT, NM_OF)))

    print(f"\n=== overall decision match: {total[0]}/{total[1]} = {total[0]/max(total[1],1):.3f} ===")
    print(f"{'context':24s} match  total   rate")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True):
        print(f"  {ctx:22s} {m:5d} {t:6d}   {m/max(t,1):.2f}   (mismatch {t-m})")
    print("\n=== top divergence examples (their choice vs ours, decoded) ===")
    for ctx, (m, t) in sorted(by_ctx.items(), key=lambda x: (x[1][1] - x[1][0]), reverse=True)[:6]:
        if examples[ctx]:
            print(f"[{ctx}] (mismatch {t-m}/{t})")
            for their, ours in examples[ctx]:
                print(f"   their={their}  ours={ours}")
    print("\n=== TO_HAND search-target priority: THEY fetch vs WE fetch ===")
    print("  THEIR top picks:", th_pick.most_common(12))
    print("  OUR   top picks:", our_pick.most_common(12))

    out = {"submission_id": sub_id, "deck": os.path.basename(deck_path),
           "overall": total, "by_ctx": {k: v for k, v in by_ctx.items()}}
    json.dump(out, open(os.path.join(HERE, "results", f"diff_{sub_id}.json"), "w"), indent=2)


if __name__ == "__main__":
    main()
