"""exp014 M0: build the offline RL dataset from top-ranker replays.

For each given submission_id (a strong/top player), download their episodes and
emit, for every decision point where THAT player is ACTIVE, one record carrying:
  - the player's POV observation (obs_dict, ~1KB)  <- self-contained for M1
  - their action, the SelectContext, n_options, is_choice (>=2 opts)
  - the FINAL outcome reward of that player (+1 win / -1 loss)  <- value label
  - the player's 60-card deck id (decks saved separately)

Also aggregates: per-deck occurrence, opponent card-frequency table (the learned
determinization prior), and an episode-level train/holdout split (no game spans
both splits -> no leakage). See PLAN.md M0 / go-no-go M1.

Usage:
  uv run python dataset_builder.py <sub_id>[,<sub_id>...] [--max-eps N] [--tag NAME]
  uv run python dataset_builder.py --seed <our_sub_id> [--top K] [--max-eps N]
      (harvest the K most-faced opponents from our own replays, then build on them)

Outputs (results/, gitignored replays cached to references/raw/replays/dataset/):
  results/records.jsonl   one decision per line (obs embedded)
  results/decks.json      deck_id -> 60-card list
  results/opp_cardfreq.json   opponent card-id -> count (determinization prior)
  results/manifest.json   stats, ctx-name map, episode split, value-label balance
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
RESULTS = os.path.join(HERE, "results")
RAW = os.path.join(ROOT, "references", "raw", "replays", "dataset")

COMPETITION = "pokemon-tcg-ai-battle"
HOLDOUT_FRAC = 0.2  # by episode


def ctx_name_map(api):
    SC = api.SelectContext
    return {int(getattr(SC, n)): n for n in dir(SC)
            if not n.startswith("_") and isinstance(getattr(SC, n), int)}


def deck_id(deck):
    return hashlib.sha1(",".join(map(str, deck)).encode()).hexdigest()[:12]


def decks_from_replay(rep):
    """{agent_index: deck60} from the first len-60 action each agent emits."""
    decks = {}
    for st in rep.get("steps", []):
        for idx, ag in enumerate(st):
            act = ag.get("action")
            if isinstance(act, list) and len(act) == 60 and idx not in decks:
                decks[idx] = act
        if len(decks) >= 2:
            break
    return decks


def is_holdout(ep_id):
    h = int(hashlib.sha1(str(ep_id).encode()).hexdigest(), 16)
    return (h % 100) < int(HOLDOUT_FRAC * 100)


def harvest_opponents(kapi, seed_sub, top_k, max_eps):
    """Most-faced opponent submission_ids from our own seed submission's replays."""
    eps = kapi.competition_list_episodes(seed_sub)[:max_eps]
    cnt = Counter()
    for e in eps:
        for a in e.agents:
            if a.submission_id and a.submission_id != seed_sub:
                cnt[a.submission_id] += 1
    return [s for s, _ in cnt.most_common(top_k)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("subs", nargs="?", default="", help="comma-separated submission_ids")
    ap.add_argument("--seed", type=int, default=0, help="harvest opponents from this sub")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--max-eps", type=int, default=40)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    os.makedirs(RESULTS, exist_ok=True)
    os.makedirs(RAW, exist_ok=True)

    from harness import load_engine
    api, _ = load_engine()
    CTX = ctx_name_map(api)

    from kaggle.api.kaggle_api_extended import KaggleApi
    kapi = KaggleApi(); kapi.authenticate()

    if args.seed:
        sub_ids = harvest_opponents(kapi, args.seed, args.top, args.max_eps)
        print(f"harvested {len(sub_ids)} opponents from seed {args.seed}: {sub_ids}")
    else:
        sub_ids = [int(s) for s in args.subs.replace(" ", ",").split(",") if s.strip()]
    if not sub_ids:
        print("no submission_ids given (use positional ids or --seed)"); sys.exit(1)

    decks = {}                      # deck_id -> deck60
    deck_occ = Counter()           # deck_id -> games
    opp_freq = Counter()           # opponent card-id -> count (determinization prior)
    ctx_counter = Counter()        # ctx name -> decisions
    label = Counter()              # 'win'/'loss' value-sample balance
    ep_seen = set()
    n_rec = n_choice = 0

    fout = open(os.path.join(RESULTS, "records.jsonl"), "w")
    for sub_id in sub_ids:
        try:
            eps = kapi.competition_list_episodes(sub_id)[:args.max_eps]
        except Exception as ex:
            print(f"  skip sub {sub_id}: {ex}"); continue
        print(f"sub {sub_id}: {len(eps)} episodes")
        for e in eps:
            path = os.path.join(RAW, f"episode-{e.id}-replay.json")
            if not os.path.exists(path):
                try:
                    kapi.competition_episode_replay(e.id, path=RAW); time.sleep(0.25)
                except Exception as ex:
                    print(f"    skip {e.id}: {ex}"); continue
            try:
                rep = json.load(open(path))
            except Exception:
                continue
            rewards = rep.get("rewards")
            if not rewards or any(r is None for r in rewards):
                continue
            tgt = next((a for a in e.agents if a.submission_id == sub_id), None)
            if tgt is None:
                continue
            ti = tgt.index
            ep_seen.add(e.id)
            ho = is_holdout(e.id)
            dmap = decks_from_replay(rep)
            tgt_deck = dmap.get(ti, [])
            if tgt_deck:
                did = deck_id(tgt_deck)
                decks.setdefault(did, tgt_deck)
                deck_occ[did] += 1
            else:
                did = None
            for oi, od in dmap.items():
                if oi != ti:
                    opp_freq.update(od)
            tgt_reward = rewards[ti] if ti < len(rewards) else None
            if tgt_reward not in (-1, 1):
                continue
            for si, st in enumerate(rep.get("steps", [])):
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
                if len(opts) == 60:   # this is the deck-selection step, not a play
                    continue
                ctx = sel.get("context")
                nopt = len(opts)
                is_choice = (nopt >= 2 and isinstance(act, list)
                             and sel.get("minCount", 1) <= len(act) <= sel.get("maxCount", 1))
                rec = {"ep": e.id, "sub": sub_id, "ai": ti, "step": si,
                       "ctx": ctx, "ctx_name": CTX.get(ctx, str(ctx)),
                       "nopt": nopt, "is_choice": bool(is_choice),
                       "action": act if isinstance(act, list) else [],
                       "reward": int(tgt_reward), "deck_id": did,
                       "holdout": ho, "obs": obs}
                fout.write(json.dumps(rec) + "\n")
                n_rec += 1
                n_choice += int(is_choice)
                ctx_counter[rec["ctx_name"]] += 1
                label["win" if tgt_reward == 1 else "loss"] += 1
    fout.close()

    json.dump(decks, open(os.path.join(RESULTS, "decks.json"), "w"))
    json.dump(dict(opp_freq.most_common()), open(os.path.join(RESULTS, "opp_cardfreq.json"), "w"))
    n_ho = sum(1 for x in ep_seen if is_holdout(x))
    manifest = {
        "subs": sub_ids, "max_eps": args.max_eps,
        "episodes": len(ep_seen), "episodes_holdout": n_ho,
        "records": n_rec, "choice_records": n_choice,
        "value_label_balance": dict(label),
        "decks": {k: deck_occ[k] for k in decks},
        "ctx_distribution": dict(ctx_counter.most_common()),
        "ctx_name_map": CTX,
        "holdout_frac": HOLDOUT_FRAC,
    }
    json.dump(manifest, open(os.path.join(RESULTS, "manifest.json"), "w"), indent=2)

    print(f"\n=== dataset built ===")
    print(f" episodes: {len(ep_seen)} (holdout {n_ho})")
    print(f" records:  {n_rec}  (choice {n_choice})")
    print(f" value balance: {dict(label)}")
    print(f" decks: {len(decks)}  | opp card types: {len(opp_freq)}")
    print(f" ctx: {dict(ctx_counter.most_common(8))}")
    print(f" -> results/records.jsonl, decks.json, opp_cardfreq.json, manifest.json")


if __name__ == "__main__":
    main()
