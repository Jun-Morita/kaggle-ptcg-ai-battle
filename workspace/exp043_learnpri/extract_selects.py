"""exp043 — extract Yushin Ito's TO_HAND select decisions as (state, candidates, picks).

Walks the cached replays in references/raw/replays/top_yushin_0708/, takes every
ACTIVE decision of the target where select.context == TO_HAND and there is a real
choice, and records:
  feats   : small state feature vector (target's POV)
  cands   : candidate card ids (decoded from option area/index)
  cand_xf : per-candidate extra features (copies in hand / on field / in discard)
  picks   : indices into cands that they actually took (may be empty = declined)
  min/max : select bounds (STOP legality)
  epid    : game id (game-level holdout split)

Usage: uv run python extract_selects.py <sub_id> <cache_tag> [max_eps] [out.pkl]
       uv run python extract_selects.py 53955703 top_yushin_0708 1000 data/tohand.pkl
"""
from __future__ import annotations
import json
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp013_router"))

import policy_diff as PD  # _area_list decoding helper

# card ids resolved at runtime by name (stable across engine builds)
_LINE_NAMES = ("Hop's Trevenant", "Hop's Phantump")


def card_id_of(obs, opt):
    lst = PD._area_list(obs, opt.get("area"), opt.get("playerIndex", 0) or 0)
    idx = opt.get("index")
    if lst is not None and isinstance(idx, int) and 0 <= idx < len(lst):
        c = lst[idx]
        if isinstance(c, dict):
            return c.get("id")
    return None


def field_ids(pl):
    out = []
    for zone in (pl.get("active") or []), (pl.get("bench") or []):
        for c in zone:
            if isinstance(c, dict):
                out.append(c.get("id"))
                for sub in c.get("cards", []) or []:  # evolution stack underneath
                    if isinstance(sub, dict):
                        out.append(sub.get("id"))
    return out


def hand_ids(pl):
    return [c.get("id") for c in pl.get("hand") or [] if isinstance(c, dict)]


def discard_ids(pl):
    return [c.get("id") for c in pl.get("discard") or [] if isinstance(c, dict)]


def make_feats(obs, line_ids):
    cur = obs["current"]
    yi = cur.get("yourIndex", 0)
    me = cur["players"][yi]
    op = cur["players"][1 - yi]
    my_field = field_ids(me)
    my_prize = len(me.get("prize") or [])
    op_prize = len(op.get("prize") or [])
    active = (me.get("active") or [None])[0]
    act_energy = len((active or {}).get("energies") or []) if isinstance(active, dict) else 0
    act_is_trev = 1.0 if isinstance(active, dict) and active.get("id") in line_ids else 0.0
    return [
        min(cur.get("turn", 0), 30) / 30.0,
        (me.get("handCount") or len(me.get("hand") or [])) / 10.0,
        me.get("deckCount", 0) / 60.0,
        my_prize / 6.0,
        op_prize / 6.0,
        (my_prize - op_prize) / 6.0,
        len(me.get("bench") or []) / 5.0,
        len(op.get("bench") or []) / 5.0,
        sum(1 for i in my_field if i in line_ids) / 4.0,
        1.0 if cur.get("energyAttached") else 0.0,
        1.0 if cur.get("supporterPlayed") else 0.0,
        act_is_trev,
        min(act_energy, 3) / 3.0,
        1.0,  # bias
    ]


def main():
    sub_id = int(sys.argv[1]) if len(sys.argv) > 1 else 53955703
    tag = sys.argv[2] if len(sys.argv) > 2 else "top_yushin_0708"
    max_eps = int(sys.argv[3]) if len(sys.argv) > 3 else 1000
    out_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "data", "tohand.pkl")

    from harness import load_engine
    api, _ = load_engine()
    TO_HAND = int(api.SelectContext.TO_HAND)
    name2id = {}
    for c in api.all_card_data():
        name2id.setdefault(c.name, c.cardId)
    line_ids = {name2id[n] for n in _LINE_NAMES if n in name2id}
    nm_of = {c.cardId: c.name for c in api.all_card_data()}

    from kaggle.api.kaggle_api_extended import KaggleApi
    kapi = KaggleApi(); kapi.authenticate()
    raw_dir = os.path.join(ROOT, "references", "raw", "replays", tag)
    eps = kapi.competition_list_episodes(sub_id)[:max_eps]
    print(f"extracting TO_HAND decisions of {sub_id} from {len(eps)} episodes in {tag}")

    records, pick_counter, skipped = [], Counter(), Counter()
    for e in eps:
        path = os.path.join(raw_dir, f"episode-{e.id}-replay.json")
        if not os.path.exists(path):
            skipped["no_replay"] += 1; continue
        tgt = next((a for a in e.agents if a.submission_id == sub_id), None)
        if tgt is None:
            skipped["no_agent"] += 1; continue
        ti = tgt.index
        try:
            rep = json.load(open(path))
        except Exception:
            skipped["bad_json"] += 1; continue
        for st in rep.get("steps", []):
            if ti >= len(st):
                continue
            ag = st[ti]
            if ag.get("status") != "ACTIVE":
                continue
            obs = ag.get("observation"); act = ag.get("action")
            if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                continue
            sel = obs["select"]
            if sel.get("context") != TO_HAND:
                continue
            opts = sel.get("option", [])
            if len(opts) < 2:
                continue
            mn, mx = sel.get("minCount", 1), sel.get("maxCount", 1)
            if not (mn <= len(act) <= mx):
                continue
            cands = [card_id_of(obs, o) for o in opts]
            if any(c is None for c in cands):
                skipped["undecoded_cand"] += 1; continue
            if any(i < 0 or i >= len(opts) for i in act):
                skipped["bad_action_idx"] += 1; continue
            cur = obs["current"]; yi = cur.get("yourIndex", 0)
            me = cur["players"][yi]
            hand = Counter(hand_ids(me)); fld = Counter(field_ids(me)); dsc = Counter(discard_ids(me))
            cand_xf = [[min(hand[c], 3) / 3.0, min(fld[c], 3) / 3.0, min(dsc[c], 3) / 3.0]
                       for c in cands]
            records.append({
                "epid": e.id,
                "feats": make_feats(obs, line_ids),
                "cands": cands,
                "cand_xf": cand_xf,
                "picks": sorted(act),
                "min": mn, "max": mx,
            })
            for i in act:
                pick_counter[nm_of.get(cands[i], cands[i])] += 1
            if not act:
                pick_counter["<STOP/none>"] += 1

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "wb") as f:
        pickle.dump(records, f)
    games = len({r["epid"] for r in records})
    print(f"wrote {len(records)} decisions from {games} games -> {out_path}")
    print("skips:", dict(skipped))
    print("their pick distribution (top 20):")
    for nm, n in pick_counter.most_common(20):
        print(f"  {n:6d}  {nm}")
    npicks = Counter(len(r["picks"]) for r in records)
    print("picks-per-decision:", dict(sorted(npicks.items())))


if __name__ == "__main__":
    main()
