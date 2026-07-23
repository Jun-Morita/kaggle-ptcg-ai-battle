"""exp079 -- what do real Alakazam pilots do that pub1034 does NOT?

The mirror is the whole decision (exp077): switching to Alakazam gains +0.091
across every other archetype and loses -0.061 to its own mirror alone. Closing
the mirror from 0.333 to 0.500 is worth +0.061 -- more than twice the +0.030 the
deck switch itself buys.

Two ways of "fixing" it are already closed:
  - policy weight tuning: NO-GO at n=300 (exp058; the author's memetic weights
    are a single-knob local optimum)
  - deck choice: NO-GO at n=400 (exp075 mirror sweep; the three real silver-band
    lists all land inside noise of stock, control 0.495)

But every fix that DID work this year was a third thing: the pilot was blind to a
real mechanism (Boss's Orders gust -> v010, revenge window -> v011, a broken race
calculation removed -> v023, a false-positive predicate -> v030). That class has
never been searched in the Alakazam mirror.

Ideal data exists: the 36 mirror games v025 played (12W-24L). Replays carry the
OPPONENT's full observations AND actions, so we can replay their decisions
through pub1034's own policy -- same position, same legal options -- and see
where the two disagree.

Read it with the exp022 rule:
  big exposure gap + matching take-when-legal  -> throughput/draw gap, NOT patchable
  normal exposure but we take it far less      -> a real gated decision leak (the
                                                  gust template) -- worth one fix

Usage: uv run python gap_scan.py [max_games]
"""
from __future__ import annotations
import os, sys, json, collections, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
if "--crn" not in sys.argv:
    sys.argv.append("--crn")
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine

PUB = os.path.join(WS, "exp057_pubalakazam", "agent")
_n = [0]

OPT = {0: "NUMBER", 1: "YES", 2: "NO", 3: "CARD", 4: "TOOL_CARD", 5: "ENERGY_CARD",
       6: "ENERGY", 7: "PLAY", 8: "ATTACH", 9: "EVOLVE", 10: "ABILITY",
       11: "DISCARD", 12: "RETREAT", 13: "ATTACK", 14: "END", 15: "SKILL",
       16: "SPECIAL_CONDITION"}


def make_pub(deck):
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"gap_{_n[0]}", os.path.join(PUB, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(PUB)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.read_deck_csv = lambda: list(deck)
    return mod.agent


def main():
    api, _ = load_engine()
    to_obs = api.to_observation_class
    from cg.api import all_card_data
    nm = {c.cardId: c.name for c in all_card_data()}

    games = json.load(open(os.path.join(HERE, "mirror_games.json")))
    cap = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else len(games)

    # MAIN-context option-type exposure / take rates, split by whether they won
    legal = collections.Counter()          # opt type -> times legal (their turn)
    took_them = collections.Counter()      # opt type -> times THEY chose it
    took_us = collections.Counter()        # opt type -> times PUB1034 would choose it
    ctx_match = collections.defaultdict(lambda: [0, 0])   # context -> [match, total]
    abil_legal = collections.Counter()
    card_them = collections.Counter()      # cards they PLAYed/used
    card_us = collections.Counter()
    n_dec = 0

    for g in games[:cap]:
        rep = json.load(open(g["fp"]))
        seat = 1 - g["seat"]                     # THE OPPONENT
        deck = None
        for st in rep.get("steps", []):
            if seat < len(st):
                a = (st[seat] or {}).get("action")
                if isinstance(a, list) and len(a) == 60:
                    deck = [int(x) for x in a]
                    break
        if deck is None:
            continue
        agent = make_pub(deck)
        for st in rep.get("steps", []):
            if seat >= len(st):
                continue
            e = st[seat] or {}
            if e.get("status") != "ACTIVE":
                continue
            ob = e.get("observation") or {}
            act = e.get("action")
            if not ob.get("current") or ob.get("select") is None:
                continue
            if not isinstance(act, list) or (isinstance(act, list) and len(act) == 60):
                continue
            try:
                o = to_obs(ob)
                mine = agent(ob)
            except Exception:
                continue
            if not isinstance(mine, list):
                continue
            n_dec += 1
            s = o.select
            ctx = int(s.context)
            same = sorted(act) == sorted(mine)
            ctx_match[ctx][0] += same
            ctx_match[ctx][1] += 1
            opts = s.option or []
            if ctx == 0:                          # MAIN
                types = {int(op.type) for op in opts}
                for t in types:
                    legal[t] += 1
                for idx, who in ((act, took_them), (mine, took_us)):
                    for i in idx:
                        if 0 <= i < len(opts):
                            who[int(opts[i].type)] += 1
                for idx, who in ((act, card_them), (mine, card_us)):
                    for i in idx:
                        if 0 <= i < len(opts) and int(opts[i].type) in (7, 10):
                            cid = opts[i].cardId
                            if cid is None and opts[i].inPlayArea is not None:
                                cid = opts[i].serial
                            key = (OPT.get(int(opts[i].type)), cid)
                            who[key] += 1
                # ability exposure by card
                for op in opts:
                    if int(op.type) == 10:
                        abil_legal[op.cardId] += 1

    print(f"decisions replayed through pub1034: {n_dec} "
          f"(from {min(cap,len(games))} real mirror games)\n")
    print("=== MAIN: take-when-legal (the exp022 lens) ===")
    print(f"{'option':12}{'legal':>8}{'THEM take':>11}{'US take':>9}{'them%':>8}{'us%':>8}{'gap':>8}")
    for t in sorted(legal, key=lambda x: -legal[x]):
        L = legal[t]
        a, b = took_them[t], took_us[t]
        print(f"{OPT.get(t,t):12}{L:8d}{a:11d}{b:9d}{a/L:8.1%}{b/L:8.1%}{(a-b)/L:+8.1%}")

    print(f"\n=== decision agreement by SelectContext (top 10 by volume) ===")
    for ctx, (m, tot) in sorted(ctx_match.items(), key=lambda x: -x[1][1])[:10]:
        print(f"  ctx {ctx:2d}  match {m}/{tot} = {m/max(1,tot):.3f}")

    print(f"\n=== ABILITY use by card (legal / them / us) ===")
    for cid in sorted(abil_legal, key=lambda x: -abil_legal[x])[:10]:
        L = abil_legal[cid]; a = card_them.get(("ABILITY", cid), 0); b = card_us.get(("ABILITY", cid), 0)
        print(f"  {str(nm.get(cid,cid)):26s} legal {L:4d}  them {a:4d} ({a/L:5.1%})  us {b:4d} ({b/L:5.1%})  gap {(a-b)/L:+6.1%}")
    print(f"\n=== PLAY/ABILITY cards THEY use more (top 12) ===")
    diff = {c: card_them[c] - card_us.get(c, 0) for c in set(card_them) | set(card_us)}
    for c in sorted(diff, key=lambda x: -diff[x])[:12]:
        t, cid = c
        print(f"  {t:8s} {str(nm.get(cid,cid)):26s} them {card_them[c]:4d}  us {card_us.get(c,0):4d}  {diff[c]:+4d}")
    json.dump({"legal": dict(legal), "them": dict(took_them), "us": dict(took_us)},
              open(os.path.join(HERE, "gap.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
