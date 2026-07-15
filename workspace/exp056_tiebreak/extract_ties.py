"""exp056 -- extract TIE-BREAK decisions from silver LO players' replays.

For every ACTIVE select decision of a teacher (same 60/60 LO deck as ours):
recompute OUR koff pilot's per-option scores (instrumented select_card_score,
exactly the probe_voids method); if >=2 options tie at the top AND the
teacher's single pick lies INSIDE the tie set, emit a training record in the
exp043 schema (feats / cands / cand_xf / picks) so train_pri.py runs unchanged.

We deliberately learn ONLY P(pick | tie set, state): outside ties the base
scores stay authoritative (regression risk structurally bounded).

Pairing rule (exp043/exp041 lesson): the action stored at steps[t] responds to
the observation at steps[t-1].

Usage: uv run python extract_ties.py <CTX or ALL> [out.pkl]
"""
from __future__ import annotations
import importlib.util
import json
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WS = os.path.join(ROOT, "workspace")
for p in ("exp001_harness", "exp013_router", "exp043_learnpri", "exp053_bandpool"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
api, _ = load_engine()
from extract_selects import _LINE_NAMES, make_feats, hand_ids, field_ids, discard_ids  # noqa: E402
import policy_diff as PD  # noqa: E402

name_of = PD.ctx_namer()
LO_DIR = os.path.join(WS, "exp053_bandpool", "lo_opp")

TEACHERS = [
    ("MR.h", "top_mrh_0715"),
    ("Takuma_Tsuji", "top_tsuji_0715"),
    # older small caches with MR.h / Rafael G games (exp054-C index)
]

TARGET_CTX = {"TO_HAND", "TO_ACTIVE", "SWITCH", "TO_BENCH", "SETUP_ACTIVE_POKEMON", "DISCARD"}


def load_pilot():
    spec = importlib.util.spec_from_file_location("lo_tie", os.path.join(LO_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LO_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.should_ko_mode = lambda *a, **k: False  # v023 config
    rec = []
    orig = mod.select_card_score

    def score(card, player_index, context, me, opponent, state, wall_mode, ko_mode):
        s = orig(card, player_index, context, me, opponent, state, wall_mode, ko_mode)
        rec.append(s)
        return s
    mod.select_card_score = score
    return mod, rec


def main():
    want = sys.argv[1] if len(sys.argv) > 1 else "ALL"
    out_path = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "data", f"ties_{want.lower()}.pkl")
    name2id = {}
    for c in api.all_card_data():
        name2id.setdefault(c.name, c.cardId)
    line_ids = {name2id[n] for n in _LINE_NAMES if n in name2id}
    nm_of = {c.cardId: c.name for c in api.all_card_data()}
    lo_deck = sorted(json.load(open(os.path.join(WS, "exp054_upperband", "lo_deck.json"))))

    mod, rec = load_pilot()
    records, stats, picks_c = [], Counter(), Counter()

    for team, tag in TEACHERS:
        raw = os.path.join(ROOT, "references", "raw", "replays", tag)
        if not os.path.isdir(raw):
            continue
        files = sorted(f for f in os.listdir(raw) if f.endswith("replay.json"))
        for fn in files:
            try:
                rep = json.load(open(os.path.join(raw, fn)))
            except Exception:
                stats["bad_json"] += 1
                continue
            names = rep.get("info", {}).get("TeamNames") or []
            if team not in names:
                continue
            ti = names.index(team)
            steps = rep.get("steps", [])
            # verify teacher runs OUR deck this game
            deck_ok = False
            for st in steps[:4]:
                a = st[ti].get("action")
                if isinstance(a, list) and len(a) == 60:
                    deck_ok = sorted(a) == lo_deck
                    break
            if not deck_ok:
                stats["other_deck_game"] += 1
                continue
            stats["games"] += 1
            for t in range(1, len(steps)):
                prev_ag, ag = steps[t - 1][ti], steps[t][ti]
                obs = prev_ag.get("observation")
                act = ag.get("action")
                if not isinstance(obs, dict) or obs.get("select") is None:
                    continue
                if not isinstance(act, list) or len(act) != 1:
                    continue
                sel = obs["select"]
                opts = sel.get("option", [])
                if len(opts) < 2:
                    continue
                ctx = name_of(sel.get("context"))
                if ctx not in TARGET_CTX or (want != "ALL" and ctx != want):
                    continue
                rec.clear()
                try:
                    mod.agent(obs)
                except Exception:
                    stats["pilot_err"] += 1
                    continue
                if len(rec) != len(opts):
                    stats["score_mismatch"] += 1
                    continue
                top = max(rec)
                tie = [i for i, s in enumerate(rec) if s == top]
                if len(tie) < 2:
                    stats["no_tie"] += 1
                    continue
                pick = act[0]
                if pick not in tie:
                    stats["pick_outside_tie"] += 1
                    continue
                # candidate card ids for the tie set (options are area refs)
                def cid_of(i):
                    o = opts[i]
                    lst = PD._area_list(obs, o.get("area"), o.get("playerIndex", 0) or 0)
                    j = o.get("index")
                    if lst is not None and isinstance(j, int) and 0 <= j < len(lst):
                        c = lst[j]
                        if isinstance(c, dict):
                            return c.get("id", -1)
                    return -1
                cands = [cid_of(i) for i in tie]
                cur = obs["current"]
                me = cur["players"][cur.get("yourIndex", 0)]
                hand, fld, dsc = hand_ids(me), field_ids(me), discard_ids(me)
                hc, fc, dc = Counter(hand), Counter(fld), Counter(dsc)
                cand_xf = [[min(hc[c], 3) / 3.0, min(fc[c], 3) / 3.0, min(dc[c], 3) / 3.0]
                           for c in cands]
                records.append({
                    "ctx": ctx,
                    "feats": make_feats(obs, line_ids),
                    "cands": cands,
                    "cand_xf": cand_xf,
                    "picks": [tie.index(pick)],
                    "min": 1, "max": 1,
                    "epid": rep.get("info", {}).get("EpisodeId"),
                })
                stats[f"tie_{ctx}"] += 1
                picks_c[nm_of.get(cid_of(pick), str(cid_of(pick)))] += 1

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    pickle.dump(records, open(out_path, "wb"))
    print(f"wrote {len(records)} tie-break records -> {out_path}")
    for k, v in sorted(stats.items()):
        print(f"  {k}: {v}")
    print("top teacher picks:", picks_c.most_common(10))


if __name__ == "__main__":
    main()
