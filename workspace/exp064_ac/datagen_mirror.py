"""exp064 Stage 0 -- pub1034 MIRROR self-play corpus for Actor-Critic.

Both seats piloted by the full pub1034 agent (search included); every decision
of BOTH seats is recorded in the official-transformer format (exp041 tuple
layout) with the seat's own +-1 outcome. Mirror-only by design: the AC target
is the 43%-share Alakazam mirror (exp060's objective, policy-space edition).

Record tuple (exp041-compatible):
  (enc.index, enc.value, enc.offset, dec.index, dec.value, dec.offset,
   n_cands, chosen_idx, turn)  + per-seat won flag at save time.

Usage:
  uv run python datagen_mirror.py <worker_id> <n_games>
Chunks land in data/mirror_w<id>_<chunk>.pkl (gitignored), resumable by count.
"""
from __future__ import annotations
import importlib.util
import os
import pickle
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp041_pilotnet"))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))
sys.path.insert(0, os.path.join(WS, "exp057_pubalakazam"))

import train_mcts as tm  # noqa: E402  (native engine)
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402

AGENT_DIR = os.path.join(WS, "exp057_pubalakazam", "agent")
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

_n = [0]


def make_pub():
    _n[0] += 1
    spec = importlib.util.spec_from_file_location(f"pub_dg{_n[0]}", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod.agent


def pub_deck():
    import json
    return json.load(open(os.path.join(WS, "exp057_pubalakazam", "pub1034_deck.json")))


def play_mirror(deck, stats):
    agents = [make_pub(), make_pub()]
    obs, sd = battle_start(deck, deck)
    if sd.errorPlayer >= 0:
        raise ValueError(f"deck error {sd.errorType}")
    recs = {0: [], 1: []}
    while obs["current"]["result"] < 0:
        seat = obs["current"]["yourIndex"]
        sel = obs.get("select")
        selected = agents[seat](obs)
        if sel is not None:
            oc = to_observation_class(obs)
            cands = tm.enumerate_candidates(oc)
            key = sorted(selected)
            idx = next((i for i, c in enumerate(cands) if c == key), None)
            if idx is None:
                stats["skip_nomatch"] += 1
            else:
                sv_e = tm.get_encoder_input(oc, deck, deck)
                sv_d = tm.get_decoder_input(oc, cands)
                recs[seat].append((sv_e.index, sv_e.value, sv_e.offset,
                                   sv_d.index, sv_d.value, sv_d.offset,
                                   len(cands), idx, oc.current.turn))
                stats["recorded"] += 1
        obs = battle_select(selected)
    battle_finish()
    result = obs["current"]["result"]
    if result not in (0, 1):
        return None
    out = []
    for seat in (0, 1):
        won = 1 if result == seat else -1
        for r in recs[seat]:
            out.append(r + (won,))
    return out


def main():
    wid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n_games = int(sys.argv[2]) if len(sys.argv) > 2 else 5000
    deck = pub_deck()
    stats = Counter()
    chunk, buf = 0, []
    # resume: skip past existing chunks
    while os.path.exists(os.path.join(DATA, f"mirror_w{wid}_{chunk:03d}.pkl")):
        chunk += 1
    done_games = chunk * 200
    t0 = time.time()
    g = 0
    while done_games + g < n_games:
        try:
            out = play_mirror(deck, stats)
        except Exception as e:
            stats["game_error"] += 1
            battle_finish()
            continue
        if out is None:
            stats["draw"] += 1
            continue
        buf.append(out)
        g += 1
        if len(buf) >= 200:
            path = os.path.join(DATA, f"mirror_w{wid}_{chunk:03d}.pkl")
            pickle.dump(buf, open(path, "wb"))
            el = time.time() - t0
            print(f"w{wid} chunk {chunk} saved ({done_games+g} games, "
                  f"{stats['recorded']} recs, skip={stats['skip_nomatch']}, "
                  f"err={stats['game_error']}, {el/max(1,g):.1f}s/game)", flush=True)
            buf, chunk = [], chunk + 1
    if buf:
        pickle.dump(buf, open(os.path.join(DATA, f"mirror_w{wid}_{chunk:03d}.pkl"), "wb"))
    print(f"w{wid} DONE {stats}", flush=True)


if __name__ == "__main__":
    main()
