"""Which ATTACKER (our active) is used, by turn bucket, W/L split."""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp011_meta_watch"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp001_harness"))
from harness import load_engine
load_engine()
from analyze import card_map, archetype
from analyze_drag import CORPORA, decks_from_replay, team_indices, NM

byid = card_map()
for corpus in ("yushin", "ours"):
    team, dirs = CORPORA[corpus]
    atk = {"W": Counter(), "L": Counter()}
    seen = set()
    for tag in dirs:
        raw = os.path.join("..", "..", "references", "raw", "replays", tag)
        if not os.path.isdir(raw): continue
        for fn in sorted(os.listdir(raw)):
            if not fn.endswith("replay.json"): continue
            try: rep = json.load(open(os.path.join(raw, fn)))
            except Exception: continue
            epid = rep.get("info", {}).get("EpisodeId")
            if epid in seen: continue
            seen.add(epid)
            idxs = team_indices(rep, team)
            if not idxs: continue
            decks = decks_from_replay(rep)
            rewards = rep.get("rewards") or [None, None]
            steps = rep.get("steps", [])
            for ti in idxs:
                my_deck, opp_deck = decks.get(ti), decks.get(1 - ti)
                if not my_deck or not opp_deck: continue
                r = rewards[ti] if ti < len(rewards) else None
                if r not in (1, -1): continue
                if archetype(opp_deck, byid) != "dragapult": continue
                wl = "W" if r == 1 else "L"
                for si, st in enumerate(steps):
                    if ti >= len(st): continue
                    ag = st[ti]
                    if ag.get("status") != "ACTIVE": continue
                    obs = ag.get("observation")
                    if si + 1 >= len(steps) or ti >= len(steps[si + 1]): continue
                    act = steps[si + 1][ti].get("action")
                    if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list): continue
                    if len(act) == 60: continue
                    sel = obs["select"]
                    if sel.get("context") != 0 or sel.get("type") != 0: continue
                    cur = obs.get("current", {})
                    turn = cur.get("turn", 0)
                    yi = cur.get("yourIndex", 0)
                    me = cur.get("players", [{}, {}])[yi]
                    myact = (me.get("active") or [{}])
                    myact = myact[0] if myact else {}
                    opts = sel.get("option", [])
                    for i in act:
                        if isinstance(i, int) and 0 <= i < len(opts) and opts[i].get("type") == 7:  # ATTACK
                            bucket = "t<=6" if turn <= 6 else "t>6"
                            atk[wl][f"{bucket}:{NM.get(myact.get('id'),'?')}[a{opts[i].get('index')}]"] += 1
    print(f"\n[{corpus}] attacker usage (W | L):")
    keys = sorted(set(atk["W"]) | set(atk["L"]), key=lambda k: -(atk["W"][k]+atk["L"][k]))
    for k in keys[:14]:
        print(f"   {k:40s} {atk['W'][k]:3d} | {atk['L'][k]:3d}")
