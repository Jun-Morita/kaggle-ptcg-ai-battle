"""exp041 Phase 1 -- competent-pilot game generation for supervised pretraining.

Root-cause fix (SESSION_NOTES "原因1"): exp040's self-play trainee never beat
crustle -> its crustle samples were all loss-labeled -> nothing to learn, and
loss reweighting only amplified "we lose". v014 (turnbeam) beats crustle 0.905;
this script has v014/revenge PILOT the charmq side against the established
5-matchup field and records, at every pilot decision, everything the official
transformer needs for BC + value pretraining:

    (enc_idx, enc_val, enc_off,          # get_encoder_input(obs, my_deck, opp_deck)
     dec_idx, dec_val, dec_off,          # get_decoder_input(obs, candidates)
     n_candidates, chosen_candidate_idx, # pilot's move mapped onto enumerate_candidates
     turn,                               # for phase-bucketed value AUC (exp032's gate is
                                         # specifically MID-game AUC)
     outcome (+1/-1 from pilot POV),     # final result; draws skipped (exp032 pattern)
     matchup_name,
     game_idx)                           # worker-local game counter -> GAME-level holdout
                                         # split (exp014 lesson: sample-level split leaks
                                         # ~73 same-game samples between train/val)

Pilot moves that don't map onto the official candidate list (64-combination cap
overflow, or partial selections when minCount < maxCount -- the official action
space can only ever pick exactly maxCount) are SKIPPED and counted: the skip
rate doubles as a measurement of the official sample's action-space gap.

Usage: uv run python datagen_bc.py <worker_id> <n_games> [pilot]
    pilot: turnbeam (default, v014, slower/stronger) | revenge (fast baseline)
Output: data/samples_<pilot>_w<id>.pkl (appended pickle chunks; read with
        repeated pickle.load until EOF), data/stats_<pilot>_w<id>.json
"""
from __future__ import annotations
import json
import os
import pickle
import random
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp040_mctsv2"))

import train_mcts as tm  # noqa: E402  (loads the native engine at import)
from teacher_pool import build_teacher_pool  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402

sys.path.insert(0, os.path.join(WS, "exp019_finisher"))
from prize_tracker import PrizeTracker  # noqa: E402  (ENC_V2 prized-card word)

sys.path.insert(0, os.path.join(WS, "exp035_turnbeam"))
sys.path.insert(0, os.path.join(WS, "exp023_revenge"))
import turnbeam_policy as TB  # noqa: E402
import revenge_policy as RVP  # noqa: E402

# Opponent mix = the real 5-matchup field (pool_eval's exact opponents) plus a
# mirror. "random"/mirror_turnbeam from teacher_pool are excluded: this dataset
# should reflect competent play on BOTH sides of the matchups we are measured
# on, and mirror_revenge already covers the mirror cheaply.
# grimmsnarl added 2026-07-10 (new ladder-#1 deck, beats our archetype 0.71).
# DATAGEN_ONLY=<name[,name]> env var restricts the mix (e.g. grimmsnarl-only
# top-up runs that extend the existing 5-matchup corpus without regenerating it).
OPP_WEIGHTS = {"crustle": 1.0, "ex_lucario": 1.0, "dragapult": 1.0,
               "archaludon": 1.0, "mirror_revenge": 1.0, "grimmsnarl": 1.0}
_only = [s for s in os.environ.get("DATAGEN_ONLY", "").split(",") if s]
if _only:
    OPP_WEIGHTS = {k: v for k, v in OPP_WEIGHTS.items() if k in _only}
CHUNK_GAMES = 200  # pickle-dump cadence


def make_pilot(kind, deck):
    if kind == "turnbeam":
        return TB.make_agent(deck)
    if kind == "revenge":
        return RVP.make_agent(deck)
    raise ValueError(f"unknown pilot {kind!r}")


def play_and_record(pilot, my_deck, opp_deck, opp_agent, my_seat, stats):
    """One game; returns (list of sample tuples, won:bool) or (None, None) on draw."""
    decks = [None, None]
    decks[my_seat] = my_deck
    decks[1 - my_seat] = opp_deck
    obs, sd = battle_start(decks[0], decks[1])
    if sd.errorPlayer >= 0:
        raise ValueError(f"deck error type {sd.errorType}")
    recs = []
    # ENC_V2 (exp046) per-game trackers: revenge window (opp prize count dropped
    # since our previous decision => one of our Pokemon was KO'd) + PrizeTracker
    # (prized-card deduction whenever a search shows the full deck).
    ptrack = PrizeTracker(my_deck) if tm.ENC_V2 else None
    rev = {"turn": None, "last_opp": None, "window": False}  # per-TURN, like revenge_policy._rev
    while obs["current"]["result"] < 0:
        if obs["current"]["yourIndex"] == my_seat:
            selected = pilot(obs)
            oc = to_observation_class(obs)
            extra = None
            if ptrack is not None:
                ptrack.update(oc)
                t = oc.current.turn
                cur_opp = len(oc.current.players[1 - my_seat].prize)
                if t != rev["turn"]:
                    rev["window"] = rev["last_opp"] is not None and cur_opp < rev["last_opp"]
                    rev["last_opp"] = cur_opp
                    rev["turn"] = t
                extra = {"window": rev["window"], "prized": ptrack.prized()}
            cands = tm.enumerate_candidates(oc)
            key = sorted(selected)
            idx = next((i for i, c in enumerate(cands) if c == key), None)
            if idx is None:
                stats["skip_nomatch"] += 1
            else:
                sv_e = tm.get_encoder_input(oc, my_deck, opp_deck, extra=extra)
                sv_d = tm.get_decoder_input(oc, cands)
                recs.append((sv_e.index, sv_e.value, sv_e.offset,
                             sv_d.index, sv_d.value, sv_d.offset,
                             len(cands), idx, oc.current.turn))
                stats["recorded"] += 1
        else:
            selected = opp_agent(obs)
        obs = battle_select(selected)
    battle_finish()
    result = obs["current"]["result"]
    if result not in (0, 1):
        return None, None  # draw -> skip whole game (keep +-1 labels clean)
    won = result == my_seat
    return recs, won


def main():
    wid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n_games = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    pilot_kind = sys.argv[3] if len(sys.argv) > 3 else "turnbeam"
    rng = random.Random(4100 + wid)
    random.seed(4100 + wid)  # pilots/teachers use the global RNG

    my_deck = tm.load_deck("charmq")
    pool = {name: (deck, factory) for name, deck, factory, _ in build_teacher_pool(my_deck)
            if name in OPP_WEIGHTS}
    names = sorted(pool)
    weights = [OPP_WEIGHTS[n] for n in names]

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    out_pkl = os.path.join(HERE, "data", f"samples_{pilot_kind}_w{wid}.pkl")
    out_json = os.path.join(HERE, "data", f"stats_{pilot_kind}_w{wid}.json")

    stats = Counter()
    wins = Counter()
    games = Counter()
    chunk = []
    t0 = time.time()
    fout = open(out_pkl, "ab")
    done = 0
    for g in range(n_games):
        name = rng.choices(names, weights=weights, k=1)[0]
        opp_deck, factory = pool[name]
        my_seat = g % 2
        pilot = make_pilot(pilot_kind, my_deck)
        opp_agent = factory(opp_deck)
        try:
            recs, won = play_and_record(pilot, my_deck, list(opp_deck), opp_agent,
                                        my_seat, stats)
        except Exception as e:
            stats["game_error"] += 1
            print(f"w{wid} game {g} ({name}) error: {e!r}", flush=True)
            continue
        if recs is None:
            stats["draw_skipped"] += 1
            continue
        outcome = 1.0 if won else -1.0
        games[name] += 1
        if won:
            wins[name] += 1
        for r in recs:
            chunk.append(r + (outcome, name, g))
        done += 1
        if done % CHUNK_GAMES == 0:
            pickle.dump(chunk, fout, protocol=4)
            fout.flush()
            chunk = []
            dt = time.time() - t0
            wr = {n: f"{wins[n]}/{games[n]}" for n in names if games[n]}
            print(f"w{wid}: {done}/{n_games} games {dt:.0f}s ({dt/done:.2f}s/game) "
                  f"samples={stats['recorded']} skip={stats['skip_nomatch']} wr={wr}",
                  flush=True)
    if chunk:
        pickle.dump(chunk, fout, protocol=4)
    fout.close()
    summary = {"pilot": pilot_kind, "worker": wid, "games_done": done,
               "stats": dict(stats), "wins": dict(wins), "games": dict(games),
               "sec": round(time.time() - t0, 1)}
    json.dump(summary, open(out_json, "w"), indent=1)
    print(f"w{wid} DONE: {json.dumps(summary)}", flush=True)


if __name__ == "__main__":
    main()
