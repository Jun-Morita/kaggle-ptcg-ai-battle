"""exp041 Step 2 -- DAgger data generation: the NET plays, v014 labels.

Root cause addressed: plain BC only sees states the TEACHER visits; the net's
own play drifts into states with no training signal and errors compound
(exp022's mechanism). Classic DAgger fixes this by relabeling the STUDENT's
visited states with the teacher's choices -- and unlike exp022 (teacher =
tomatomato's replays, unqueryable), our teacher is our own v014 turnbeam:
queryable on any state, unlimited.

Per net decision we record the SAME 12-field layout as datagen_bc.py, except
CH = the TEACHER's (v014's) chosen candidate index on that state. Value labels
stay the final outcome of the net-piloted game (on-policy value data). Teacher
choices that don't map onto the candidate enumeration are skipped + counted
(datagen_bc measured 0 for turnbeam-as-pilot; here the state distribution is
the net's, so re-measure).

Usage: uv run python dagger_gen.py <worker_id> <n_games> <model.pth> [device]
Output: data/dagger_w<id>.pkl + data/dagger_stats_w<id>.json
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

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402  (loads the native engine at import)
from teacher_pool import build_teacher_pool  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from cg.game import battle_start, battle_finish, battle_select  # noqa: E402

sys.path.insert(0, os.path.join(WS, "exp035_turnbeam"))
import turnbeam_policy as TB  # noqa: E402

OPP_WEIGHTS = {"crustle": 1.0, "ex_lucario": 1.0, "dragapult": 1.0,
               "archaludon": 1.0, "mirror_revenge": 1.0}
CHUNK_GAMES = 100


def make_net_pilot(model, device, my_deck):
    """Raw-net argmax pilot (same as eval_raw's agent)."""
    @torch.no_grad()
    def agent(obs_dict):
        oc = to_observation_class(obs_dict)
        cands = tm.enumerate_candidates(oc)
        sv_enc = tm.get_encoder_input(oc, my_deck, None)  # oracle-free (ship condition)
        sv_dec = tm.get_decoder_input(oc, cands)
        _, policy = tm.eval_nn(sv_enc, sv_dec, model)
        best = max(range(len(cands)), key=lambda i: policy[i])
        return cands[best]
    return agent


def play_and_record(net_pilot, teacher, my_deck, opp_deck, opp_agent, my_seat, stats):
    decks = [None, None]
    decks[my_seat] = my_deck
    decks[1 - my_seat] = opp_deck
    obs, sd = battle_start(decks[0], decks[1])
    if sd.errorPlayer >= 0:
        raise ValueError(f"deck error type {sd.errorType}")
    recs = []
    try:
        while obs["current"]["result"] < 0:
            if obs["current"]["yourIndex"] == my_seat:
                oc = to_observation_class(obs)
                if oc.select is not None and oc.select.option:
                    # teacher label FIRST (on the pristine state), then net's move
                    teacher_sel = teacher(obs)
                    cands = tm.enumerate_candidates(oc)
                    key = sorted(teacher_sel)
                    tidx = next((i for i, c in enumerate(cands) if c == key), None)
                    selected = net_pilot(obs)
                    if tidx is None:
                        stats["skip_nomatch"] += 1
                    else:
                        sv_e = tm.get_encoder_input(oc, my_deck, opp_deck)
                        sv_d = tm.get_decoder_input(oc, cands)
                        recs.append((sv_e.index, sv_e.value, sv_e.offset,
                                     sv_d.index, sv_d.value, sv_d.offset,
                                     len(cands), tidx, oc.current.turn))
                        stats["recorded"] += 1
                        stats["agree"] += int(sorted(selected) == key)
                else:
                    selected = net_pilot(obs)
            else:
                selected = opp_agent(obs)
            obs = battle_select(selected)
    finally:
        battle_finish()
    result = obs["current"]["result"]
    if result not in (0, 1):
        return None, None
    return recs, result == my_seat


def main():
    wid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n_games = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    model_path = sys.argv[3] if len(sys.argv) > 3 else "results/pre1b/model_ep2.pth"
    device = torch.device(sys.argv[4] if len(sys.argv) > 4 else
                          ("cuda" if torch.cuda.is_available() else "cpu"))
    rng = random.Random(4400 + wid)
    random.seed(4400 + wid)
    os.environ.setdefault("REVENGE_BONUS", "50")

    model = tm.MyModel(128, 2, 256, 1, 1).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    my_deck = tm.load_deck("charmq")
    pool = {name: (deck, factory) for name, deck, factory, _ in build_teacher_pool(my_deck)
            if name in OPP_WEIGHTS}
    names = sorted(pool)
    weights = [OPP_WEIGHTS[n] for n in names]
    net_pilot = make_net_pilot(model, device, my_deck)
    teacher = TB.make_agent(my_deck)

    out_path = os.path.join(HERE, "data", f"dagger_w{wid}.pkl")
    stats = Counter()
    chunk, done, t0 = [], 0, time.time()
    fout = open(out_path, "ab")
    g = 0
    attempts = 0
    max_attempts = n_games * 3 + 20  # guard against a silent infinite retry loop
    while done < n_games:
        attempts += 1
        if attempts > max_attempts:
            raise RuntimeError(f"w{wid}: {attempts} attempts, only {done}/{n_games} games "
                               f"succeeded -- stats={dict(stats)}")
        name = rng.choices(names, weights=weights)[0]
        opp_deck, opp_factory = pool[name]
        my_seat = g % 2
        g += 1
        try:
            recs, won = play_and_record(net_pilot, teacher, my_deck, list(opp_deck),
                                        opp_factory(list(opp_deck)), my_seat, stats)
        except Exception as e:
            stats[f"err_{type(e).__name__}"] += 1
            continue
        if recs is None:
            stats["draws"] += 1
            continue
        outcome = 1 if won else -1
        stats[f"{'win' if won else 'loss'}_{name}"] += 1
        for r in recs:
            chunk.append(r + (outcome, name, g))
        done += 1
        if len(chunk) >= CHUNK_GAMES * 60:
            pickle.dump(chunk, fout, protocol=4)
            fout.flush()
            chunk = []
            dt = time.time() - t0
            print(f"w{wid}: {done}/{n_games} games {stats['recorded']} recs "
                  f"agree={stats['agree']/max(stats['recorded'],1):.3f} "
                  f"[{dt/max(done,1):.2f}s/g]", flush=True)
    if chunk:
        pickle.dump(chunk, fout, protocol=4)
    fout.close()
    json.dump(dict(stats), open(os.path.join(HERE, "data", f"dagger_stats_w{wid}.json"), "w"),
              indent=1)
    print(f"w{wid} DONE {done} games; stats={dict(stats)}", flush=True)


if __name__ == "__main__":
    main()
