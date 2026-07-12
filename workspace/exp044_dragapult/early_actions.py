"""exp044 step 2: what happens in turns 1-8, decision-level, W/L split.
Focus: in OUR losses, what do we choose INSTEAD of attacking? And what does
Yushin attack INTO (opp active hp/id) when he attacks early?"""
import json, os, sys
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp011_meta_watch"))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "exp001_harness"))
from harness import load_engine
load_engine()
from cg import api
from analyze import card_map, archetype
from analyze_drag import CORPORA, decks_from_replay, team_indices, OPTT, CTXT, NM, decode_opt

MAXT = 8

def scan(team, dirs, opp_arch, byid):
    out = {"W": Counter(), "L": Counter()}
    tgt = {"W": Counter(), "L": Counter()}
    nturnsel = {"W": 0, "L": 0}
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
                    cur = obs.get("current", {})
                    turn = cur.get("turn", 0)
                    if turn > MAXT: continue
                    sel = obs["select"]
                    opts = sel.get("option", [])
                    # TURN-type select (context 0 / type 0) = main turn decision
                    is_turn_sel = sel.get("context") == 0 and sel.get("type") == 0
                    if is_turn_sel: nturnsel[wl] += 1
                    yi = cur.get("yourIndex", 0)
                    opp = cur.get("players", [{}, {}])[1 - yi]
                    oppact = (opp.get("active") or [{}])
                    oppact = oppact[0] if oppact else {}
                    for i in act:
                        if not (isinstance(i, int) and 0 <= i < len(opts)): continue
                        t, name = decode_opt(obs, opts[i])
                        if is_turn_sel:
                            out[wl][t] += 1
                            if t == "ATTACK":
                                tgt[wl][f"into:{NM.get(oppact.get('id'), oppact.get('id'))}(hp{oppact.get('hp')})"] += 1
    return out, tgt, nturnsel

def main():
    byid = card_map()
    for corpus in ("yushin", "ours"):
        team, dirs = CORPORA[corpus]
        out, tgt, nsel = scan(team, dirs, "dragapult", byid)
        print(f"\n[{corpus}] turn<={MAXT} TURN-select mix (per turn-select, W | L):")
        keys = sorted(set(out["W"]) | set(out["L"]), key=lambda k: -(out["W"][k] + out["L"][k]))
        for k in keys:
            w = out["W"][k] / max(nsel["W"], 1)
            l = out["L"][k] / max(nsel["L"], 1)
            print(f"   {k:24s} {w:5.2f} | {l:5.2f}")
        print(f"   (n turn-selects: W={nsel['W']} L={nsel['L']})")
        print(f"  attack targets (count, W | L):")
        for k in sorted(set(tgt["W"]) | set(tgt["L"]), key=lambda k: -(tgt["W"][k] + tgt["L"][k]))[:8]:
            print(f"   {k:44s} {tgt['W'][k]:3d} | {tgt['L'][k]:3d}")

main()
