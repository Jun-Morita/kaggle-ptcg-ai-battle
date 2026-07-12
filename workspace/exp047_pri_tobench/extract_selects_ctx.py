"""exp047 — generalized version of exp043's extract_selects2.py: extracts a
CHOSEN SelectContext's card-choice decisions (not hardcoded to TO_HAND), with
the FIXED next-step action pairing (see exp043 SESSION_NOTES / exp041 lesson:
the action stored at steps[t] responds to the obs at steps[t-1]).

Same record schema as exp043 so train_pri.py runs unchanged on the output:
  feats, cands, cand_xf, picks, min, max, epid

Usage: uv run python extract_selects_ctx.py <CONTEXT_NAME> [team] [cache_tag] [out.pkl]
       uv run python extract_selects_ctx.py TO_BENCH "Yushin Ito" top_yushin_0708 data/tobench.pkl
"""
from __future__ import annotations
import json
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp043_learnpri"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp013_router"))

from extract_selects import (_LINE_NAMES, card_id_of, field_ids, hand_ids,
                             discard_ids, make_feats)  # noqa: E402


def main():
    ctx_name = sys.argv[1] if len(sys.argv) > 1 else "TO_BENCH"
    team = sys.argv[2] if len(sys.argv) > 2 else "Yushin Ito"
    tag = sys.argv[3] if len(sys.argv) > 3 else "top_yushin_0708"
    out_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, "data", f"{ctx_name.lower()}.pkl")

    from harness import load_engine
    api, _ = load_engine()
    CTX = int(getattr(api.SelectContext, ctx_name))
    name2id = {}
    for c in api.all_card_data():
        name2id.setdefault(c.name, c.cardId)
    line_ids = {name2id[n] for n in _LINE_NAMES if n in name2id}
    nm_of = {c.cardId: c.name for c in api.all_card_data()}

    raw_dir = os.path.join(ROOT, "references", "raw", "replays", tag)
    files = sorted(f for f in os.listdir(raw_dir) if f.endswith("replay.json"))
    print(f"extracting {ctx_name} decisions of '{team}' from {len(files)} cached replays in {tag}")

    records, pick_counter, skipped = [], Counter(), Counter()
    seen = set()
    for fn in files:
        try:
            rep = json.load(open(os.path.join(raw_dir, fn)))
        except Exception:
            skipped["bad_json"] += 1
            continue
        epid = rep.get("info", {}).get("EpisodeId")
        if epid in seen:
            continue
        seen.add(epid)
        names = rep.get("info", {}).get("TeamNames") or []
        idxs = [i for i, n in enumerate(names) if n == team]
        if not idxs:
            skipped["no_agent"] += 1
            continue
        steps = rep.get("steps", [])
        for ti in idxs:
            for si, st in enumerate(steps):
                if ti >= len(st):
                    continue
                ag = st[ti]
                if ag.get("status") != "ACTIVE":
                    continue
                obs = ag.get("observation")
                if si + 1 >= len(steps) or ti >= len(steps[si + 1]):
                    skipped["no_next"] += 1
                    continue
                act = steps[si + 1][ti].get("action")
                if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                    continue
                if len(act) == 60:   # deck-submission pseudo-step
                    continue
                sel = obs["select"]
                if sel.get("context") != CTX:
                    continue
                opts = sel.get("option", [])
                if len(opts) < 2:
                    continue
                mn, mx = sel.get("minCount", 1), sel.get("maxCount", 1)
                if not (mn <= len(act) <= mx):
                    skipped["count_out_of_bounds"] += 1
                    continue
                cands = [card_id_of(obs, o) for o in opts]
                if any(c is None for c in cands):
                    skipped["undecoded_cand"] += 1
                    continue
                if any((not isinstance(i, int)) or i < 0 or i >= len(opts) for i in act):
                    skipped["bad_action_idx"] += 1
                    continue
                cur = obs["current"]
                yi = cur.get("yourIndex", 0)
                me = cur["players"][yi]
                hand = Counter(hand_ids(me))
                fld = Counter(field_ids(me))
                dsc = Counter(discard_ids(me))
                cand_xf = [[min(hand[c], 3) / 3.0, min(fld[c], 3) / 3.0, min(dsc[c], 3) / 3.0]
                           for c in cands]
                records.append({
                    "epid": epid,
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
    print(f"their pick distribution ({ctx_name}, top 20):")
    for nm, n in pick_counter.most_common(20):
        print(f"  {n:6d}  {nm}")
    npicks = Counter(len(r["picks"]) for r in records)
    print("picks-per-decision:", dict(sorted(npicks.items())))


if __name__ == "__main__":
    main()
