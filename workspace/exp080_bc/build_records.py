"""exp080 step 2 -- convert TEACHER seats (from scan_teachers.py's index) into
datagen_bc-format 12-tuple training records, streamed straight out of the daily zip.

Difference from exp041/replay_to_records.py: that one keys on a single team name
across cached per-submission replay dirs. Here the teachers are MANY different
top-band players (>=1000 LB) who WON while piloting one target archetype, listed
in teachers_index.json as (member, seat, archetype, score). We stream only those
members out of the 21.5GB daily zip (random access by name -- never extracted).

Record layout == datagen_bc.py / exp041 (12-tuple):
  (enc.index, enc.value, enc.offset, dec.index, dec.value, dec.offset,
   n_cands, chosen_idx, turn, outcome, mu, epid)
outcome is +1 for every teacher seat (we filtered WON in scan_teachers). mu = the
opponent archetype decoded from their 60-card deck. The obs->action pairing is the
verified next-step rule from exp041 (action at steps[t+1] answers obs at steps[t]).

Usage: uv run python build_records.py [archetype] [max_eps]
  archetype: target teacher deck label (default: mixed_ex3 = Grimmsnarl)
  max_eps:   cap episodes for a smoke run (default: all)
Writes data/<archetype>_w7.pkl (+ stats json). Idempotent full rebuild.
"""
from __future__ import annotations
import json, os, sys, pickle, zipfile
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp011_meta_watch"))

import train_mcts as tm  # noqa: E402  (loads engine + encoder/decoder/enumerate)
from cg.api import to_observation_class  # noqa: E402
from analyze import card_map, archetype  # noqa: E402

WID = 7  # teacher corpus word-id (ladder=9, expert=8 in exp041; teacher=7 here)


def decks_from_ep(ep):
    d = {}
    for st in ep.get("steps", []):
        for i, ag in enumerate(st):
            a = (ag or {}).get("action")
            if isinstance(a, list) and len(a) == 60 and i not in d:
                d[i] = [int(x) for x in a]
        if len(d) >= 2:
            break
    return d


def convert_seat(ep, ti, byid, stats):
    """Yield 12-tuple records for one teacher seat `ti` of one episode."""
    decks = decks_from_ep(ep)
    my_deck, opp_deck = decks.get(ti), decks.get(1 - ti)
    if not my_deck or not opp_deck:
        stats["skip_no_deck"] += 1
        return
    rewards = ep.get("rewards") or [None, None]
    r = rewards[ti] if ti < len(rewards) else None
    if r not in (1, -1):
        stats["skip_draw_or_err"] += 1
        return
    outcome = int(r)
    mu = archetype(opp_deck, byid)
    epid = ep.get("info", {}).get("EpisodeId") or ep.get("id") or 0
    steps = ep.get("steps", [])
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
        if len(act) == 60:
            continue
        try:
            oc = to_observation_class(obs)
        except Exception:
            stats["skip_obs_convert"] += 1
            continue
        if oc.select is None or not oc.select.option:
            continue
        cands = tm.enumerate_candidates(oc)
        idx = next((i for i, c in enumerate(cands) if c == sorted(act)), None)
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
    target = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].isdigit() else "mixed_ex3"
    max_eps = next((int(a) for a in sys.argv[1:] if a.isdigit()), None)

    idx = json.load(open(os.path.join(HERE, "teachers_index.json")))
    zp = idx["zip"]
    seats = [t for t in idx["teachers"] if t[2] == target]
    if max_eps:
        seats = seats[:max_eps]
    print(f"target={target}  teacher seats={len(seats)}  zip={os.path.basename(zp)}", flush=True)

    byid = card_map()
    z = zipfile.ZipFile(zp)
    stats = Counter()
    chunk, games = [], 0
    out_pkl = os.path.join(HERE, "data", f"{target}_w{WID}.pkl")
    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(out_pkl, "wb") as fout:
        for n, (member, seat, arch, sc) in enumerate(seats):
            try:
                ep = json.loads(z.read(member))
            except Exception:
                stats["skip_bad_json"] += 1
                continue
            n0 = stats["recorded"]
            for rec in convert_seat(ep, seat, byid, stats):
                chunk.append(rec)
                if len(chunk) >= 20000:
                    pickle.dump(chunk, fout, protocol=4)
                    chunk = []
            if stats["recorded"] > n0:
                games += 1
            if (n + 1) % 200 == 0:
                print(f"  ...{n+1}/{len(seats)} eps, recorded {stats['recorded']}", flush=True)
        if chunk:
            pickle.dump(chunk, fout, protocol=4)

    out_json = os.path.join(HERE, "data", f"{target}_w{WID}_stats.json")
    json.dump({"stats": dict(stats), "games": games, "target": target}, open(out_json, "w"), indent=1)
    print(f"\n[{target}] recorded={stats['recorded']} from games={games}  "
          f"nomatch={stats['skip_nomatch']} obs_fail={stats['skip_obs_convert']} feat_fail={stats['skip_feat']}")
    print("opp archetype mix:", sorted(((k[3:], v) for k, v in stats.items() if k.startswith('mu_')), key=lambda x: -x[1]))
    print(f"wrote {out_pkl} ({os.path.getsize(out_pkl)/1e6:.1f}MB)")


if __name__ == "__main__":
    main()
