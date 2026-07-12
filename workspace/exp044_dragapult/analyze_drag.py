"""exp044 -- dragapult-floor attack, step 1: behavioral diff on REAL replays.

Why dragapult: our worst matchup (v014 = 0.17 at n=200) and the biggest
remaining headroom. Yushin Ito's OLD sub (53955703, SAME Hop's-Trevenant
archetype) went 15W-16L (0.48) vs dragapult on the ladder -- ~3x our rate with
the same deck line, so a better way to pilot this matchup demonstrably exists.

Why a NEW extractor: policy_diff2.py / analyze_adaptation.py / exp043's
extract_selects.py all use SAME-STEP action pairing, which is WRONG (verified
2026-07-10: steps[t].action responds to the obs at steps[t-1]; same-step gives
4% out-of-range actions + shifted labels). This script uses the verified
next-step pairing throughout (obs at steps[si] pairs steps[si+1][ti].action).

Output: W/L-split behavioral tables for (a) Yushin-vs-dragapult and (b) our
own ladder games vs dragapult -- game length, prize race trajectory, bench
size discipline, action-type mix, TO_HAND fetches, energy-attach targets,
per-turn first-attack timing. The diff (his wins vs our losses) is the
candidate-mechanism shortlist for an env-gated patch.

Usage: uv run python analyze_drag.py [opp_archetype]   # default dragapult
"""
from __future__ import annotations
import json
import os
import sys
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))

from harness import load_engine  # noqa: E402
load_engine()
from cg import api  # noqa: E402
from analyze import card_map, archetype  # noqa: E402

OPTT = {getattr(api.OptionType, n): n for n in dir(api.OptionType)
        if not n.startswith("_") and isinstance(getattr(api.OptionType, n), int)}
CTXT = {getattr(api.SelectContext, n): n for n in dir(api.SelectContext)
        if not n.startswith("_") and isinstance(getattr(api.SelectContext, n), int)}
NM = {c.cardId: c.name for c in api.all_card_data()}

CORPORA = {
    "yushin": ("Yushin Ito", ["top_yushin_0708"]),
    "ours": ("Junichiro Morita", ["0704_54269701", "0705_54315009", "0707_54315009",
                                   "ladder_v012", "ladder_v013", "ladder_v014",
                                   "ladder_v014clone"]),
}


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


def team_indices(rep, team):
    names = rep.get("info", {}).get("TeamNames") or [a.get("Name") for a in rep.get("info", {}).get("Agents", [])]
    return [i for i, n in enumerate(names or []) if n == team]


def _area_list(obs, area, pi):
    cur = obs.get("current", {})
    pls = cur.get("players", [{}, {}])
    pl = pls[pi] if pi < len(pls) else {}
    return {1: obs.get("select", {}).get("deck", []), 2: pl.get("hand", []),
            3: pl.get("discard", []), 4: pl.get("active", []), 5: pl.get("bench", []),
            6: pl.get("prize", []), 7: cur.get("stadium", []), 12: cur.get("looking", [])}.get(area)


def decode_opt(obs, opt):
    t = OPTT.get(opt.get("type"), str(opt.get("type")))
    lst = _area_list(obs, opt.get("area"), opt.get("playerIndex", 0) or 0)
    idx = opt.get("index")
    if lst is not None and isinstance(idx, int) and 0 <= idx < len(lst):
        c = lst[idx]
        if isinstance(c, dict):
            return t, NM.get(c.get("id"), str(c.get("id")))
    return t, None


class GameStats:
    def __init__(self, won):
        self.won = won
        self.max_turn = 0
        self.bench_by_turn = {}        # turn -> bench count (first obs that turn)
        self.myprize_by_turn = {}      # turn -> my prize cards REMAINING
        self.opprize_by_turn = {}
        self.first_attack_turn = None
        self.act_types = Counter()     # OptionType of chosen options
        self.fetches = Counter()       # TO_HAND chosen card names
        self.attach_targets = Counter()  # energy-attach target card names
        self.plays = Counter()         # "TYPE:Name" of all chosen options


def scan(team, dirs, opp_arch, byid):
    games = []
    seen = set()
    for tag in dirs:
        raw = os.path.join(ROOT, "references", "raw", "replays", tag)
        if not os.path.isdir(raw):
            continue
        for fn in sorted(os.listdir(raw)):
            if not fn.endswith("replay.json"):
                continue
            try:
                rep = json.load(open(os.path.join(raw, fn)))
            except Exception:
                continue
            epid = rep.get("info", {}).get("EpisodeId")
            if epid in seen:
                continue
            seen.add(epid)
            idxs = team_indices(rep, team)
            if not idxs:
                continue
            decks = decks_from_replay(rep)
            rewards = rep.get("rewards") or [None, None]
            steps = rep.get("steps", [])
            for ti in idxs:
                my_deck, opp_deck = decks.get(ti), decks.get(1 - ti)
                if not my_deck or not opp_deck:
                    continue
                r = rewards[ti] if ti < len(rewards) else None
                if r not in (1, -1):
                    continue
                if archetype(opp_deck, byid) != opp_arch:
                    continue
                g = GameStats(won=(r == 1))
                for si, st in enumerate(steps):
                    if ti >= len(st):
                        continue
                    ag = st[ti]
                    if ag.get("status") != "ACTIVE":
                        continue
                    obs = ag.get("observation")
                    if si + 1 >= len(steps) or ti >= len(steps[si + 1]):
                        continue
                    act = steps[si + 1][ti].get("action")
                    if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                        continue
                    if len(act) == 60:
                        continue
                    cur = obs.get("current", {})
                    turn = cur.get("turn", 0)
                    g.max_turn = max(g.max_turn, turn)
                    yi = cur.get("yourIndex", 0)
                    pls = cur.get("players", [{}, {}])
                    me, opp = pls[yi], pls[1 - yi]
                    if turn not in g.bench_by_turn:
                        g.bench_by_turn[turn] = len(me.get("bench") or [])
                        g.myprize_by_turn[turn] = len(me.get("prize") or [])
                        g.opprize_by_turn[turn] = len(opp.get("prize") or [])
                    sel = obs["select"]
                    opts = sel.get("option", [])
                    ctx = CTXT.get(sel.get("context"), str(sel.get("context")))
                    for i in act:
                        if not (isinstance(i, int) and 0 <= i < len(opts)):
                            continue
                        t, name = decode_opt(obs, opts[i])
                        g.act_types[t] += 1
                        if name:
                            g.plays[f"{t}:{name}"] += 1
                        if t == "ATTACK" and g.first_attack_turn is None:
                            g.first_attack_turn = turn
                        if ctx == "TO_HAND" and name:
                            g.fetches[name] += 1
                        if t == "ENERGY" and name:
                            g.attach_targets[name] += 1
                games.append(g)
    return games


def bucket_avg(games, attr, buckets=((1, 4), (5, 10), (11, 99))):
    out = []
    for lo, hi in buckets:
        vals = [v for g in games for t, v in getattr(g, attr).items() if lo <= t <= hi]
        out.append(sum(vals) / len(vals) if vals else float("nan"))
    return out


def report(label, games):
    for wl, gs in (("W", [g for g in games if g.won]), ("L", [g for g in games if not g.won])):
        if not gs:
            continue
        n = len(gs)
        turns = sum(g.max_turn for g in gs) / n
        fa = [g.first_attack_turn for g in gs if g.first_attack_turn]
        fat = sum(fa) / len(fa) if fa else float("nan")
        b = bucket_avg(gs, "bench_by_turn")
        # prizes REMAINING at turn 10 (lower opp = we're ahead)
        my10 = [g.myprize_by_turn.get(t) for g in gs for t in (10, 9, 11) if g.myprize_by_turn.get(t) is not None][:n]
        op10 = [g.opprize_by_turn.get(t) for g in gs for t in (10, 9, 11) if g.opprize_by_turn.get(t) is not None][:n]
        my10v = sum(my10) / len(my10) if my10 else float("nan")
        op10v = sum(op10) / len(op10) if op10 else float("nan")
        att = sum(g.act_types.get("ATTACK", 0) for g in gs) / n
        ret = sum(g.act_types.get("RETREAT", 0) for g in gs) / n
        print(f"{label}-{wl}: n={n} turns={turns:.1f} 1st_atk_t={fat:.1f} "
              f"bench[t1-4/5-10/11+]={b[0]:.2f}/{b[1]:.2f}/{b[2]:.2f} "
              f"prize@t10 my={my10v:.2f} opp={op10v:.2f} atk/g={att:.1f} ret/g={ret:.1f}")
    # aggregated counters (per game, W vs L side by side)
    for cname in ("fetches", "attach_targets"):
        print(f"  -- {cname} (per game, W | L):")
        w_gs = [g for g in games if g.won] or [GameStats(True)]
        l_gs = [g for g in games if not g.won] or [GameStats(False)]
        cw, cl = Counter(), Counter()
        for g in w_gs:
            cw.update(getattr(g, cname))
        for g in l_gs:
            cl.update(getattr(g, cname))
        keys = sorted(set(cw) | set(cl), key=lambda k: -(cw[k] + cl[k]))
        for k in keys[:12]:
            print(f"     {k:32s} {cw[k]/len(w_gs):5.2f} | {cl[k]/len(l_gs):5.2f}")


def main():
    opp_arch = sys.argv[1] if len(sys.argv) > 1 else "dragapult"
    byid = card_map()
    print(f"=== opponent archetype: {opp_arch} (next-step pairing, verified) ===")
    for corpus in ("yushin", "ours"):
        team, dirs = CORPORA[corpus]
        games = scan(team, dirs, opp_arch, byid)
        w = sum(g.won for g in games)
        print(f"\n[{corpus}/{team}] {len(games)} games, {w}W-{len(games)-w}L")
        report(corpus, games)


if __name__ == "__main__":
    main()
