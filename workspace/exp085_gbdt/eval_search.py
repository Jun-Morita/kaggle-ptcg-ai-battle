"""A/B the search: same ranker, same value model, search on vs off.

Both arms run through harness.run_gauntlet against the same opponent with seats
alternated. The only difference between them is the `use_search` flag, so the
delta is attributable to lookahead and nothing else -- unlike v2, where the corpus
and the feature set moved together and the result could not be read.

Usage: uv run python eval_search.py --opp lucario --n 200 [--tag v4] [--value v1]
"""
from __future__ import annotations
import json, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle",
          "exp040_mctsv2", "exp041_pilotnet", "exp019_finisher", "exp080_bc",
          "exp025_unkoable", "exp084_council"):
    sys.path.insert(0, os.path.join(WS, p))

import feats  # noqa: E402
from harness import run_gauntlet  # noqa: E402
from eval_h2h import opponent, arg  # noqa: E402
from gbdt_search_policy import make_agent  # noqa: E402


def main():
    kind = arg("--opp", "lucario")
    n = int(arg("--n", "200"))
    tag = arg("--tag", "v4")
    vtag = arg("--value", "v1")
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    pure = os.path.join(HERE, "results", f"gbdt_pure_{tag}.pkl")
    vpath = os.path.join(HERE, "results", f"value_{vtag}")
    print(f"search A/B: ranker={tag} value={vtag} vs {kind} n={n}", flush=True)
    out = {}
    for label, use in (("no-search", False), ("search", True)):
        me = make_agent(pure, vpath, list(grimm), use_search=use)
        t0 = time.time()
        st = run_gauntlet(me, opponent(kind, grimm), n_games=n, swap_sides=True)
        wr = st.wins0 / max(1, st.n)
        s = me.state
        print(f"  {label:<10} {st.wins0}-{st.wins1}-{st.draws}  wr {wr:.3f}  "
              f"err {st.errors0}  max_move {st.max_move_time0:.3f}s  "
              f"decisions {s['decisions']} fallbacks {s['fallbacks']} "
              f"overrides {s['overrides']}/{s['searched']}  ({time.time()-t0:.0f}s)",
              flush=True)
        out[label] = {"w": st.wins0, "l": st.wins1, "d": st.draws, "wr": wr,
                      "err": st.errors0, "max_move": st.max_move_time0,
                      "fallbacks": s["fallbacks"], "overrides": s["overrides"],
                      "searched": s["searched"]}
    d = out["search"]["wr"] - out["no-search"]["wr"]
    se = (2 * 0.25 / max(1, n)) ** 0.5
    print(f"\n  delta {d:+.3f}   (se {se:.3f}, z {d/se:+.2f})")
    json.dump({"opp": kind, "n": n, "tag": tag, "value": vtag, "arms": out,
               "delta": d}, open(os.path.join(HERE, "results",
                                              f"search_ab_{kind}_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
