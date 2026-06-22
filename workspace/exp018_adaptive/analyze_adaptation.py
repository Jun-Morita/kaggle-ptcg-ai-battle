"""Does a TOP player adapt their play to the opponent's archetype?

For a top non-ex player (default charmq, cached replays), split their ACTUAL games
by OPPONENT archetype and measure, per matchup:
  - their W-L (do they have a weak matchup like our non-ex mirror?)
  - bench development (avg benched Pokemon at their decisions = prize-liability discipline)
  - attack tempo (fraction of their turns that end in an ATTACK)
  - decision-match vs OUR policy (where we diverge most = matchup-specific know-how)
If their behavior shifts by opponent archetype, that's the opponent-adaptive mechanism;
the matchups where we match them least are where we'd gain by adapting.

Usage: uv run python analyze_adaptation.py [sub_id] [deck.json] [cache_tag]
  default: charmq 53858964, charmq_deck.json, diff_53858964
"""
from __future__ import annotations
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp011_meta_watch"),
          os.path.join(ROOT, "workspace", "exp013_router")):
    sys.path.insert(0, p)

from harness import load_engine  # noqa
from analyze import archetype  # noqa
import router_policy as R  # noqa

api, _ = load_engine()
to_obs = api.to_observation_class
SC = {int(getattr(api.SelectContext, n)): n for n in dir(api.SelectContext)
      if not n.startswith("_") and isinstance(getattr(api.SelectContext, n), int)}
OPTT = {int(getattr(api.OptionType, n)): n for n in dir(api.OptionType)
        if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
byid = {c.cardId: c for c in api.all_card_data()}


def decks_from_replay(rep):
    d = {}
    for st in rep.get("steps", []):
        for i, ag in enumerate(st):
            a = ag.get("action")
            if isinstance(a, list) and len(a) == 60 and i not in d:
                d[i] = a
        if len(d) >= 2:
            break
    return d


def main():
    sub_id = int(sys.argv[1]) if len(sys.argv) > 1 else 53858964
    deck_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")
    tag = sys.argv[3] if len(sys.argv) > 3 else f"diff_{sub_id}"
    raw = os.path.join(ROOT, "references", "raw", "replays", tag)
    deck = json.load(open(deck_path))
    agent = R.make_agent(deck)  # our policy piloting their deck

    # per opponent-archetype accumulators
    wl = defaultdict(lambda: [0, 0])          # arch -> [wins, games]
    bench = defaultdict(lambda: [0, 0])       # arch -> [sum_bench, n_decisions]
    attack_turns = defaultdict(lambda: [0, 0])  # arch -> [turns_with_attack, turns]
    match = defaultdict(lambda: [0, 0])       # arch -> [match, total] vs our policy
    files = [f for f in os.listdir(raw) if f.endswith("replay.json")] if os.path.isdir(raw) else []
    print(f"sub {sub_id}: {len(files)} cached replays in {tag}")

    for fn in files:
        try:
            rep = json.load(open(os.path.join(raw, fn)))
        except Exception:
            continue
        rewards = rep.get("rewards")
        steps = rep.get("steps", [])
        if not steps:
            continue
        dm = decks_from_replay(rep)
        # find our target index = the player whose deck matches sub's (len-60); use agent index from any agent meta if present
        # fallback: the index whose deck classifies as the same as our deck's archetype
        my_arch = archetype(deck, byid)
        ti = None
        for i, d in dm.items():
            if archetype(d, byid) == my_arch:
                ti = i
                break
        if ti is None:
            continue
        oi = 1 - ti
        opp_arch = archetype(dm.get(oi, []), byid) if dm.get(oi) else "unknown"
        if rewards and ti < len(rewards) and rewards[ti] in (-1, 1):
            wl[opp_arch][0] += int(rewards[ti] == 1)
            wl[opp_arch][1] += 1
        cur_turn = None
        turn_attacked = False
        for st in steps:
            if ti >= len(st):
                continue
            ag = st[ti]
            if ag.get("status") != "ACTIVE":
                continue
            obs = ag.get("observation")
            act = ag.get("action")
            if not isinstance(obs, dict) or obs.get("select") is None:
                continue
            sel = obs["select"]
            opts = sel.get("option", [])
            cur = obs.get("current", {})
            # tempo: track per-turn whether an ATTACK option was chosen
            t = cur.get("turn")
            if t != cur_turn:
                if cur_turn is not None:
                    attack_turns[opp_arch][0] += int(turn_attacked)
                    attack_turns[opp_arch][1] += 1
                cur_turn = t
                turn_attacked = False
            pl = cur.get("players", [{}, {}])
            me = pl[ti] if ti < len(pl) else {}
            bench[opp_arch][0] += len(me.get("bench", []))
            bench[opp_arch][1] += 1
            chosen = [opts[i] for i in act if isinstance(act, list) and 0 <= i < len(opts)]
            if any(OPTT.get(o.get("type")) == "ATTACK" for o in chosen):
                turn_attacked = True
            # decision-match vs our policy (real choices only)
            if len(opts) >= 2 and isinstance(act, list) and sel.get("minCount", 1) <= len(act) <= sel.get("maxCount", 1):
                try:
                    ours = agent(obs)
                    match[opp_arch][0] += int(sorted(ours) == sorted(act))
                    match[opp_arch][1] += 1
                except Exception:
                    pass

    print(f"\n=== {sub_id} ({my_arch}) behavior BY OPPONENT archetype ===")
    print(f"{'opp archetype':20s} {'W-L (wr)':14s} {'avg_bench':9s} {'attack/turn':11s} {'match_vs_us':10s}")
    for arch in sorted(wl, key=lambda a: -wl[a][1]):
        w, g = wl[arch]
        b = bench[arch][0] / max(bench[arch][1], 1)
        at = attack_turns[arch][0] / max(attack_turns[arch][1], 1)
        m, tot = match[arch]
        print(f"  {arch:18s} {w}-{g-w} ({w/max(g,1):.2f})   {b:6.2f}     {at:6.2f}       {m}/{tot}={m/max(tot,1):.2f}")


if __name__ == "__main__":
    main()
