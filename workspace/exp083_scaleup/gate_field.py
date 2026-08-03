"""Field gate: two nets across the REAL opponent spread, not the mirror.

Why this exists. Every net gate so far (gate.py, eval_cross.py) put the same
Grimmsnarl deck on both seats, so a PASS only ever meant "better in the mirror".
v046 passed that gate at 0.608 (z=+4.30) and then lost 146 ladder points to v045:

                      ladder   Alakazam   lucario_ex   mirror
  v045 (v3s+search)    886.9   0.70 n=40   0.62 n=8    0.39 n=41
  v046 (v15s+search)   740.4   0.50 n=12   0.27 n=15   0.33 n=6

Same 0.537 overall winrate, against weaker opponents. The 15-day corpus is 46%
mirror, so the net specialised into the mirror and gave up the field -- a
regression a mirror-only gate cannot see by construction.

Weights are OUR OWN observed ladder shares (v045, n=136), renormalised over the
archetypes we can actually simulate (77% of real games). lucario_ex matters most
of all here: it is where v046 collapsed, and the ladder pool is ~87% a single
pilot (lucario_v2), so the local stand-in is faithful.

Raw argmax both sides: search is applied equally at ship time and costs ~5x the
wall clock, so it dilutes rather than sharpens a net-vs-net read.

Usage: ENC_V4=1 uv run python gate_field.py --new <a.pth> --old <b.pth> [--n 60]
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
PILOT = os.path.join(WS, "exp041_pilotnet")
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle",
          "exp041_pilotnet", "exp040_mctsv2", "exp019_finisher", "exp080_bc",
          "exp025_unkoable"):
    sys.path.insert(0, os.path.join(WS, p))

from harness import load_engine  # noqa: E402
load_engine()

import torch  # noqa: E402
import train_mcts as tm  # noqa: E402
import eval_raw as ER  # noqa: E402
import eval_gate as EG  # noqa: E402
import anti_crustle as AC  # noqa: E402
import baselines as B  # noqa: E402
import load_archaludon as AR  # noqa: E402
from cg.api import to_observation_class  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402

# our own ladder shares (v045, n=136), restricted to simulable archetypes
# exp083n: reweighted from the public score-band snapshot
# (myso1987/ptcg-ai-battle-leaderboard-deck-meta-by-score-band, 07-27, 283
# classified teams in 800-899 -- OUR band). The old weights came from our own
# replay sample and were wrong in two ways that both cost measuring power:
#   mirror       0.30 -> 0.237   Grimmsnarl is 58.8% at 1100+ but 23.7% here, and
#                                the mirror cell is pinned at 0.99 (no headroom)
#   archaludon   0.00 -> 0.163   MISSING ENTIRELY, and it is 27.6% one band below
# Mega Lucario is 3.9% here but 24-30% in the 500-699 bands a new submission
# passes through, so a fresh agent meets a different field on the way up.
WEIGHT = {"mixed_ex1": 0.276, "mixed_ex3": 0.237, "archaludon": 0.163,
          "crustle_control": 0.120, "lucario_ex": 0.039, "dragapult": 0.035}
WEIGHT_OLD = {"mixed_ex3": 0.30, "mixed_ex1": 0.29, "crustle_control": 0.08,
          "lucario_ex": 0.06, "dragapult": 0.02, "mixed_ex2": 0.02}
LABEL = {"archaludon": "Archaludon",
         "mixed_ex3": "Grimmsnarl(mirror)", "mixed_ex1": "Alakazam",
         "crustle_control": "Crustle", "lucario_ex": "lucario_v2",
         "dragapult": "Dragapult", "mixed_ex2": "TR Spidops"}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


@contextlib.contextmanager
def enc_version(v):
    old = (tm.ENC_V3, getattr(tm, "ENC_V4", 0), tm.num_words_encoder, tm.encoder_size)
    tm.ENC_V3 = 1 if v >= 3 else 0
    tm.ENC_V4 = 1 if v >= 4 else 0
    tm.num_words_encoder = 28 if v >= 4 else (26 if v >= 3 else 25)
    tm.encoder_size = 38000 if v >= 4 else (34000 if v >= 3 else 24000)
    try:
        yield
    finally:
        (tm.ENC_V3, tm.ENC_V4, tm.num_words_encoder, tm.encoder_size) = old


def load(pth, device):
    pth = pth if os.path.isabs(pth) else os.path.join(PILOT, pth)
    cfg = json.load(open(os.path.join(os.path.dirname(pth), "arch.json")))
    v = int(cfg.get("enc_version", 1))
    with enc_version(v):
        m = tm.MyModel(cfg["d_model"], cfg["heads"], cfg["d_ff"],
                       cfg["enc_layers"], cfg["dec_layers"]).to(device)
        m.load_state_dict(torch.load(pth, map_location=device))
    m.eval()
    return m, v, cfg, pth


def make_agent(model, v, my_deck, sc=0):
    """sc>0 = the SHIP configuration (net + MCTS). This matters for more than
    realism: raw argmax exercises only the POLICY head, while ENC_V4's main
    additions (select context, remainDamageCounter/remainEnergyCost) are state
    information that feeds the VALUE head -- and the value head is what search
    consumes. A raw-argmax gate therefore under-measures any change aimed at
    evaluation rather than at move ranking."""
    if sc:
        mk = make_mcts_agent_factory(sc, oracle_free=True)

        def agent_s(obs_dict):
            with enc_version(v):
                return mk(model, my_deck, my_deck)(obs_dict)
        return agent_s

    def agent(obs_dict):
        oc = to_observation_class(obs_dict)
        cands = tm.enumerate_candidates(oc)
        if len(cands) == 1:
            return cands[0]
        with enc_version(v):
            sv_e = tm.get_encoder_input(oc, my_deck, None)
            sv_d = tm.get_decoder_input(oc, cands)
            _, policy = tm.eval_nn(sv_e, sv_d, model)
        return cands[max(range(len(cands)), key=lambda i: policy[i])]
    return agent


# SPAR: path to a LEARNED pilot to seat as the Alakazam opponent instead of the
# rule-based pub1034. The gate's whole problem is that its opponents are weak --
# we beat four of six at 0.89-0.99 while scoring 0.55 on the real ladder, and
# adding Archaludon (16.3% of our band, and genuinely unsaturated at 0.71) still
# did not let it see that v046's net is 116 ladder points worse. A pilot trained
# on 3.7M Alakazam decisions from the same Daily Top Episodes is the closest thing
# we can build to a real ladder opponent. SPAR_SC>0 gives it search too.
SPAR = os.environ.get("SPAR", "")
SPAR_SC = int(os.environ.get("SPAR_SC", "0"))
# CHAMP: seat a net (normally the one we currently ship) as the MIRROR opponent
# instead of rule-based pub1034. That cell is 0.237 of the weight and pins at
# 0.99 against pub1034, i.e. it contributes weight but no information. Against
# the champion it sits at 0.50 by construction and asks the only question that
# matters for a ship decision -- is the candidate better than what is already on
# the ladder. Costs no training; the champion checkpoint already exists.
CHAMP = os.environ.get("CHAMP", "")
CHAMP_SC = int(os.environ.get("CHAMP_SC", "16"))
_SPAR = {}


def _pilot(path, deck, sc):
    if path not in _SPAR:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        _SPAR[path] = load(path, dev)
    m, v, _cfg, _p = _SPAR[path]
    return make_agent(m, v, list(deck), sc)


def spar_pilot(deck):
    return _pilot(SPAR, deck, SPAR_SC)


def champ_pilot(deck):
    return _pilot(CHAMP, deck, CHAMP_SC)


def opponents(grimm, opp_decks):
    """(key, opponent deck, factory taking that deck -> agent)."""
    out = []
    for k in WEIGHT:
        if k == "archaludon":
            # public rule-based pilot + its own 60-card list (exp025). 16.3% of our
            # band and 27.6% one band down, and it was never in this gate at all.
            out.append((k, list(AR.ARCH_DECK), lambda _d: AR.make_archaludon_agent()))
        elif k == "lucario_ex":
            out.append((k, list(AC.LUCARIO_DECK),
                        lambda _d: AC.make_agent(AC.LUCARIO_DECK)))
        elif k == "crustle_control":
            out.append((k, list(opp_decks[k]), lambda _d: AC.make_crustle_agent()))
        elif k == "dragapult":
            out.append((k, list(opp_decks[k]),
                        lambda _d: B.make_policy_agent("dragapult")))
        elif k == "mixed_ex3" and CHAMP:
            out.append((k, list(grimm), champ_pilot))
        elif k == "mixed_ex1" and SPAR:
            out.append((k, list(opp_decks[k]), spar_pilot))
        else:
            deck = grimm if k == "mixed_ex3" else opp_decks[k]
            out.append((k, list(deck), EG.make_pub1034))
    return out


def run(model, v, grimm, opps, n, sc=0):
    res, total = {}, 0.0
    for k, odeck, fac in opps:
        w, l, d, e = ER.run_matchup(
            model, grimm, odeck, fac, n,
            agent_factory=lambda _m, my, _o: make_agent(model, v, my, sc))
        played = max(1, w + l + d)
        wr = w / played
        res[k] = (wr, w, l, d, e)
        total += WEIGHT[k] * wr
        print(f"    {LABEL[k]:<20} {wr:.3f}  ({w}-{l}-{d}, err={e})", flush=True)
    return res, total / sum(WEIGHT.values())


def main():
    n = int(arg("--n", "60"))
    sc = int(arg("--sc", "0"))
    tag = arg("--tag", "field")
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    opp_decks = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
    # --only runs a single archetype so the six can be parallelised across cores;
    # the weighted total is then meaningless for that process, so it is suppressed.
    only = arg("--only", "")
    new, vn, cfgn, pn = load(arg("--new"), device)
    old, vo, cfgo, po = load(arg("--old"), device)
    print(f"NEW {os.path.relpath(pn, WS)}  enc_version={vn}")
    print(f"OLD {os.path.relpath(po, WS)}  enc_version={vo}")
    print(f"{'MCTS sc=%d (SHIP config)' % sc if sc else 'raw argmax'}, oracle-free, "
          f"seats alternated, n={n} per matchup\n", flush=True)

    opps = [o for o in opponents(grimm, opp_decks) if not only or o[0] == only]
    t0 = time.time()
    print("  NEW:")
    rn, tn = run(new, vn, grimm, opps, n, sc)
    print("  OLD:")
    ro, to = run(old, vo, grimm, opps, n, sc)
    if not only:
        print(f"\n  weighted   NEW {tn:.3f}   OLD {to:.3f}   delta {tn - to:+.3f}"
              f"   ({time.time()-t0:.0f}s)")
    print("  per-matchup delta: " + "  ".join(
        f"{LABEL[k]} {rn[k][0]-ro[k][0]:+.2f}" for k in rn))
    print("VERDICT:", "PASS" if tn - to >= 0.03 else
          ("FLAT" if tn - to > -0.03 else "NEGATIVE"))
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    json.dump({"new": pn, "old": po, "n": n, "weight": WEIGHT,
               "new_res": rn, "old_res": ro, "new_total": tn, "old_total": to},
              open(os.path.join(HERE, "results", f"{tag}_{only or 'all'}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
