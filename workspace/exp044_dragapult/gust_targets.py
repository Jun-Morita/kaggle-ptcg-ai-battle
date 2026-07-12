"""exp044 step 3: when Boss's Orders is played vs dragapult, WHO gets pulled?
(the select right after playing Boss = choose opp bench pokemon)"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp011_meta_watch"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp001_harness"))
from harness import load_engine
load_engine()
from cg import api
from analyze import card_map, archetype
from analyze_drag import CORPORA, decks_from_replay, team_indices, CTXT, NM, _area_list

def scan(team, dirs, opp_arch, byid):
    pulls = {"W": Counter(), "L": Counter()}
    boss_plays = {"W": 0, "L": 0}
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
                if archetype(opp_deck, byid) != opp_arch: continue
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
                    eff = sel.get("effect") or {}
                    effname = NM.get(eff.get("id")) if isinstance(eff, dict) else None
                    # Boss's Orders effect select: choose from opp bench (area 5, playerIndex = opp)
                    if effname and "Boss" in str(effname):
                        boss_plays[wl] += 1
                        opts = sel.get("option", [])
                        for i in act:
                            if not (isinstance(i, int) and 0 <= i < len(opts)): continue
                            o = opts[i]
                            lst = _area_list(obs, o.get("area"), o.get("playerIndex", 0) or 0)
                            idx = o.get("index")
                            if lst is not None and isinstance(idx, int) and 0 <= idx < len(lst):
                                c = lst[idx]
                                if isinstance(c, dict):
                                    pulls[wl][f"{NM.get(c.get('id'), c.get('id'))}(hp{c.get('hp')})"] += 1
    return pulls, boss_plays

byid = card_map()
for corpus in ("yushin", "ours"):
    team, dirs = CORPORA[corpus]
    pulls, bp = scan(team, dirs, "dragapult", byid)
    print(f"\n[{corpus}] Boss-select decisions: W={bp['W']} L={bp['L']}")
    for wl in ("W", "L"):
        for k, v in pulls[wl].most_common(8):
            print(f"   {wl} pull {k:36s} {v}")
