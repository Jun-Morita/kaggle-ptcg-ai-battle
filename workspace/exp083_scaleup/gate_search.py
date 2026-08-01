"""Field gate for a SEARCH setting (gate_field.py compares two nets, not two searches).

Exists because of v046: a candidate that wins the self-mirror can be losing the
field, and a mirror-only gate cannot see it. FINAL_PICK=visit_q measured 0.644
(z=+3.64) against the shipped setting in the self-mirror; that is a paired result
on one matchup, and the mirror is 30% of the weight. This runs the same candidate
against all six archetypes at the weights we actually meet on the ladder.

Same net on both sides -- only the search settings differ -- so unlike gate_field
there is no encoder version to juggle.

Usage: ENC_V3=1 uv run python gate_search.py <model.pth> [n] --final visit_q
                                                            [--only mixed_ex1]
"""
from __future__ import annotations
import contextlib
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import torch  # noqa: E402
import gate_field as GF  # noqa: E402  (loads the engine and sys.path)
from gate_field import ER, enc_version, tm  # noqa: E402
from eval_mcts import make_mcts_agent_factory  # noqa: E402

# duplicated from ab_search.py on purpose: importing that module would call
# load_engine() a second time.
KNOBS = ("SEARCH_TEMP", "PUCT_C", "DET_COUNT", "VALUE_SCALE", "FINAL_PICK")
BASE = {"SEARCH_TEMP": 10.0, "PUCT_C": 0.4, "DET_COUNT": 1, "VALUE_SCALE": 1.0,
        "FINAL_PICK": "visit"}


@contextlib.contextmanager
def settings(cfg):
    old = {k: getattr(tm, k) for k in KNOBS}
    for k, val in cfg.items():
        setattr(tm, k, val)
    try:
        yield
    finally:
        for k, val in old.items():
            setattr(tm, k, val)


def make_agent(model, v, my_deck, sc, cfg):
    mk = make_mcts_agent_factory(sc, oracle_free=True)

    def agent(obs_dict):
        with enc_version(v), settings(cfg):
            return mk(model, my_deck, my_deck)(obs_dict)
    return agent


def main():
    pth = next(a for a in sys.argv[1:] if a.endswith(".pth"))
    n = next((int(a) for a in sys.argv[1:] if a.isdigit()), 150)
    sc = int(sys.argv[sys.argv.index("--sc") + 1]) if "--sc" in sys.argv else 16
    only = sys.argv[sys.argv.index("--only") + 1] if "--only" in sys.argv else None
    cand = dict(BASE)
    for flag, key, cast in (("--temp", "SEARCH_TEMP", float), ("--c", "PUCT_C", float),
                            ("--det", "DET_COUNT", int), ("--vscale", "VALUE_SCALE", float),
                            ("--final", "FINAL_PICK", str)):
        if flag in sys.argv:
            cand[key] = cast(sys.argv[sys.argv.index(flag) + 1])
    changed = {k: v for k, v in cand.items() if v != BASE[k]}
    if not changed:
        sys.exit("nothing to gate: pass at least one search flag")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model, v, _cfg, _p = GF.load(pth, device)
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    opp_decks = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
    opps = [o for o in GF.opponents(grimm, opp_decks) if only is None or o[0] == only]

    print(f"gate_search: {os.path.relpath(pth, WS)} sc={sc} n={n}\n  cand {changed}\n",
          flush=True)
    rows = {}
    for k, odeck, fac in opps:
        row = {}
        for name, cfg in (("cand", cand), ("base", BASE)):
            t0 = time.time()
            w, l, d, e = ER.run_matchup(
                model, grimm, odeck, fac, n,
                agent_factory=lambda _m, my, _o: make_agent(model, v, my, sc, cfg))
            played = max(1, w + l + d)
            row[name] = {"wr": w / played, "w": w, "l": l, "d": d, "err": e}
            print(f"  {GF.LABEL[k]:<20} {name:<5} {w/played:.3f}  ({w}-{l}-{d}, err={e})"
                  f"  ({time.time()-t0:.0f}s)", flush=True)
        row["delta"] = row["cand"]["wr"] - row["base"]["wr"]
        row["weight"] = GF.WEIGHT[k]
        print(f"  {GF.LABEL[k]:<20} delta {row['delta']:+.3f}  "
              f"(se {(2*0.25/max(1,n))**0.5:.3f}, weight {GF.WEIGHT[k]:.2f})\n", flush=True)
        rows[k] = row

    wsum = sum(GF.WEIGHT[k] for k in rows)
    gain = sum(GF.WEIGHT[k] * rows[k]["delta"] for k in rows) / wsum
    print(f"weighted delta over {wsum:.2f} of the field: {gain:+.4f}")
    os.makedirs(os.path.join(HERE, "results"), exist_ok=True)
    tag = "_".join(f"{k.lower()}{val}" for k, val in sorted(changed.items()))
    json.dump({"model": pth, "sc": sc, "n": n, "cand": cand, "rows": rows,
               "weighted_delta": gain},
              open(os.path.join(HERE, "results",
                                f"gate_search_{tag}_{only or 'all'}_n{n}.json"), "w"),
              indent=1)


if __name__ == "__main__":
    main()
