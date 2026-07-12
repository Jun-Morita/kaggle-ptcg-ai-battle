"""exp041 plan-A -- convert OUR OWN ladder replays (v012/v013/v014-lineage subs)
into datagen_bc-format training records: the REAL-META counterpart of Phase 1.

Why: the 5.9M synthetic corpus covers only the fixed 5-matchup pool, but the
ladder plays ~10 archetypes (incl. the new #1 Grimmsnarl ex). Our own ladder
replays contain, at every step, the full observation dict AND the action the
submitted agent actually took -- so for v012-v014-lineage submissions the
policy label (= the shipped pilot's real choice) and the value label (= the
real game outcome under that same policy) are CONSISTENT by construction; no
teacher re-inference needed. This yields Phase-1-quality records on the TRUE
opponent distribution, for (a) mixing into pre3 fine-tuning and (b) measuring
the synthetic->real distribution gap (top-1 by archetype).

Record layout == datagen_bc.py (12-tuple), GID = kaggle episode id, MU = the
opponent archetype decoded from their 60-card deck action. The opp_deck oracle
word IS included (reconstructed from the replay) so train-time opp-dropout
keeps working unchanged; oracle-free eval drops it as usual.

Usage: uv run python replay_to_records.py [corpus] [out_wid]
  corpus: "ladder" (default; our own v012-v014-lineage replays, wid 9)
        | "expert" (Yushin Ito's OLD same-archetype sub 53955703, wid 8)
  Reads the cached replay dirs listed in CORPORA (references/raw/replays/*),
  writes data/<corpus>_w<wid>.pkl (+ stats json). Idempotent full rebuild.
"""
from __future__ import annotations
import json
import os
import pickle
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))
sys.path.insert(0, os.path.join(WS, "exp001_harness"))

import train_mcts as tm  # noqa: E402  (loads the engine; enumerate/encoder/decoder)
from cg.api import to_observation_class  # noqa: E402
from analyze import card_map, archetype  # noqa: E402

OUR_TEAM = "Junichiro Morita"
# corpus name -> (target team name, [replay cache dirs])
# "ladder": our own v012-v014-lineage subs (v_trev deck, revenge/guard/turnbeam pilots)
# "expert": Yushin Ito's OLD submission 53955703 -- SAME Hop's-Trevenant archetype
#           as ours, LB 1097 at n=1000 games; with the fixed action pairing his
#           decisions are clean expert labels for policy fine-tuning.
CORPORA = {
    "ladder": (OUR_TEAM, ["0704_54269701", "0705_54315009", "0707_54315009",
                           "ladder_v012", "ladder_v013", "ladder_v014",
                           "ladder_v014clone"]),
    "expert": ("Yushin Ito", ["top_yushin_0708"]),
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
    idxs = [i for i, n in enumerate(names or []) if n == team]
    return idxs  # may be [i] or [0,1] (self-play validation) or []


def convert_replay(rep, byid, stats, team):
    """Yield 12-tuple records for every our-seat decision in one replay.

    CRITICAL pairing rule (verified 2026-07-10 on 9k+ decisions): the action
    stored at steps[t] is the response to the observation at steps[t-1] —
    i.e. obs[t] pairs with steps[t+1][ti]["action"]. Same-step pairing yields
    4% out-of-range actions and systematically wrong labels; next-step pairing
    yields 0% out-of-range and a 100% candidate-space capture rate (matching
    synthetic datagen's skip=0). NOTE: exp043's extract_selects.py used
    same-step pairing — its 6,058 TO_HAND records carry this misalignment.
    """
    idxs = team_indices(rep, team)
    if not idxs:
        stats["skip_not_ours"] += 1
        return
    decks = decks_from_replay(rep)
    rewards = rep.get("rewards") or [None, None]
    steps = rep.get("steps", [])
    epid = rep.get("info", {}).get("EpisodeId") or 0
    for ti in idxs:
        my_deck = decks.get(ti)
        opp_deck = decks.get(1 - ti)
        if not my_deck or not opp_deck:
            stats["skip_no_deck"] += 1
            continue
        r = rewards[ti] if ti < len(rewards) else None
        if r not in (1, -1):
            stats["skip_draw_or_err"] += 1
            continue
        outcome = int(r)
        mu = archetype(opp_deck, byid)
        for si, st in enumerate(steps):
            if ti >= len(st):
                continue
            ag = st[ti]
            if ag.get("status") != "ACTIVE":
                continue
            obs = ag.get("observation")
            if si + 1 >= len(steps) or ti >= len(steps[si + 1]):
                stats["skip_no_next"] += 1
                continue
            act = steps[si + 1][ti].get("action")
            if not isinstance(obs, dict) or obs.get("select") is None or not isinstance(act, list):
                continue
            if len(act) == 60:      # the deck-submission pseudo-step
                continue
            try:
                oc = to_observation_class(obs)
            except Exception:
                stats["skip_obs_convert"] += 1
                continue
            if oc.select is None or not oc.select.option:
                continue
            cands = tm.enumerate_candidates(oc)
            key = sorted(act)
            idx = next((i for i, c in enumerate(cands) if c == key), None)
            if idx is None:
                stats["skip_nomatch"] += 1
                continue
            try:
                sv_e = tm.get_encoder_input(oc, my_deck, opp_deck)
                sv_d = tm.get_decoder_input(oc, cands)
            except Exception:
                stats["skip_feat"] += 1
                continue
            stats["recorded"] += 1
            stats[f"mu_{mu}"] += 1
            yield (sv_e.index, sv_e.value, sv_e.offset,
                   sv_d.index, sv_d.value, sv_d.offset,
                   len(cands), idx, oc.current.turn, outcome, mu, int(epid))


def main():
    corpus = sys.argv[1] if len(sys.argv) > 1 else "ladder"
    out_wid = int(sys.argv[2]) if len(sys.argv) > 2 else (9 if corpus == "ladder" else 8)
    team, dirs = CORPORA[corpus]
    out_pkl = os.path.join(HERE, "data", f"{corpus}_w{out_wid}.pkl")
    out_json = os.path.join(HERE, "data", f"{corpus}_w{out_wid}_stats.json")
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    byid = card_map()
    stats = Counter()
    games = Counter()
    chunk = []
    seen_epids = set()
    with open(out_pkl, "wb") as fout:  # full rebuild each run (idempotent)
        for tag in dirs:
            raw = os.path.join(ROOT, "references", "raw", "replays", tag)
            if not os.path.isdir(raw):
                print(f"  !! missing dir {tag}")
                continue
            files = sorted(f for f in os.listdir(raw) if f.endswith("replay.json"))
            n_before = stats["recorded"]
            for fn in files:
                try:
                    rep = json.load(open(os.path.join(raw, fn)))
                except Exception:
                    stats["skip_bad_json"] += 1
                    continue
                epid = rep.get("info", {}).get("EpisodeId")
                if epid in seen_epids:     # day-dirs overlap for the same sub
                    stats["skip_dup_episode"] += 1
                    continue
                seen_epids.add(epid)
                n0 = stats["recorded"]
                for rec in convert_replay(rep, byid, stats, team):
                    chunk.append(rec)
                    if len(chunk) >= 20000:
                        pickle.dump(chunk, fout, protocol=4)
                        chunk = []
                if stats["recorded"] > n0:
                    games[tag] += 1
            print(f"{tag}: {len(files)} files, +{stats['recorded']-n_before} records", flush=True)
        if chunk:
            pickle.dump(chunk, fout, protocol=4)
    json.dump({"stats": dict(stats), "games": dict(games)}, open(out_json, "w"), indent=1)
    print(f"\n[{corpus}/{team}] total recorded={stats['recorded']} games={sum(games.values())} "
          f"nomatch={stats['skip_nomatch']} obs_convert_fail={stats['skip_obs_convert']}")
    print(f"by archetype: {sorted(((k, v) for k, v in stats.items() if k.startswith('mu_')), key=lambda x: -x[1])}")
    print(f"wrote {out_pkl} ({os.path.getsize(out_pkl)/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
