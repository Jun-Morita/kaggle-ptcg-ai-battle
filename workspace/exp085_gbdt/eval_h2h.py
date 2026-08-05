"""Head-to-head on the harness that every shipped submission was measured with.

Replaces eval_gbdt.py, whose hand-rolled loop cannot be trusted. That loop drove
cg.game directly, skipped harness._validate_selection, and seated decks by hand;
it reported the GBDT at 0.480 vs Mega Lucario ex where run_gauntlet -- running the
same model, same weights, same code -- reports 0.120. The mirror control that
seemed to validate the loop (defer_ref.py --defer all = 0.492) could not have
caught a deck/seat mixup, because both seats held the same deck by construction.

Everything here goes through harness.run_gauntlet: it asks each agent for its own
60 cards, alternates seats, validates selections, and attributes errors -- the
same path used for v014 through v051.

Opponents:
  ship      our v3s net + MCTS sc16, i.e. what is on the ladder now. The gate.
  ref       the public tetsutani agent (identical deck).
  lucario / crustle / dragapult / archaludon / alakazam   the field spread.

Usage: uv run python eval_h2h.py --opp ship [--n 200] [--pure results/...]
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

import feats  # noqa: E402  (loads engine)
from harness import run_gauntlet  # noqa: E402
from gbdt_policy import make_agent  # noqa: E402


def artifact_agent(tarp):
    """Load the agent out of the built tar, the way Kaggle does (exec, no __file__).

    Gates run on this, not on the dev module. The two are supposed to be the same
    code, and twice this session they were not: the packaged build lost every game
    while the dev module was fine, because a stripped import made every decision
    fall through to a legal-but-arbitrary move with no error raised.
    """
    import tarfile, tempfile
    d = tempfile.mkdtemp(prefix="h2h_art_")
    with tarfile.open(tarp) as t:
        t.extractall(d, filter="data")
    prev = os.getcwd()
    os.chdir(d)
    try:
        g = {"__name__": "built"}
        exec(compile(open("main.py").read(), "main.py", "exec"), g)
    finally:
        os.chdir(prev)
    assert g.get("_AGENT") is not None, "artifact failed to load its model"
    return g["agent"], g["_AGENT"]


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def with_deck(fn, deck):
    """run_match asks an agent for its decklist by handing it select=None.
    Rule-based helpers already answer that; search agents do not."""
    def a(obs):
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return list(deck)
        return fn(obs)
    return a


def opponent(kind, grimm):
    if kind == "ref":
        from load_ref import make_ref_agent
        return make_ref_agent()
    if kind == "ship":
        import torch, train_mcts as tm
        from eval_mcts import make_mcts_agent_factory
        pth = arg("--ship", os.path.join(WS, "exp041_pilotnet", "results",
                                         "sc083_v3s", "model_ep14.pth"))
        a = json.load(open(os.path.join(os.path.dirname(pth), "arch.json")))
        v = int(a.get("enc_version", 1))
        tm.ENC_V3 = 1 if v >= 3 else 0
        tm.ENC_V4 = 1 if v >= 4 else 0
        tm.num_words_encoder = 28 if v >= 4 else (26 if v >= 3 else 25)
        tm.encoder_size = 38000 if v >= 4 else (34000 if v >= 3 else 24000)
        tm.FINAL_PICK = "visit_q"
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        m = tm.MyModel(a["d_model"], a["heads"], a["d_ff"],
                       a["enc_layers"], a["dec_layers"]).to(dev)
        m.load_state_dict(torch.load(pth, map_location=dev))
        m.eval()
        mk = make_mcts_agent_factory(16, oracle_free=True)
        return with_deck(mk(m, list(grimm), list(grimm)), grimm)
    import anti_crustle as AC
    if kind == "lucario":
        return AC.make_agent(AC.LUCARIO_DECK)
    if kind == "crustle":
        return AC.make_crustle_agent()
    if kind == "dragapult":
        import baselines as B
        return B.make_policy_agent("dragapult")
    if kind == "archaludon":
        import load_archaludon as AR
        return with_deck(AR.make_archaludon_agent(), AR.ARCH_DECK)
    if kind == "alakazam":
        import eval_gate as EG
        od = json.load(open(os.path.join(WS, "exp080_bc", "opp_decks.json")))
        return with_deck(EG.make_pub1034(list(od["mixed_ex1"])), od["mixed_ex1"])
    raise SystemExit(f"unknown --opp {kind}")


def main():
    kind = arg("--opp", "ship")
    n = int(arg("--n", "200"))
    grimm = json.load(open(os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")))
    tarp = arg("--artifact")
    if tarp:
        me, inner = artifact_agent(tarp)
        pure = tarp
    else:
        pure = arg("--pure", os.path.join(HERE, "results", "gbdt_pure_grimm.pkl"))
        me = make_agent(pure, list(grimm))
        inner = me
    opp = opponent(kind, grimm)
    print(f"GBDT({os.path.basename(pure)}) vs {kind}  n={n}", flush=True)
    t0 = time.time()
    st = run_gauntlet(me, opp, n_games=n, swap_sides=True)
    wr = st.wins0 / max(1, st.n)
    z = (wr - 0.5) / ((0.25 / max(1, st.n)) ** 0.5)
    sst = getattr(inner, "state", {})
    fb, dec = sst.get("fallbacks", -1), sst.get("decisions", -1)
    print(f"\n  vs {kind}: {st.wins0}-{st.wins1}-{st.draws}  wr {wr:.3f}  z {z:+.2f}  "
          f"err_us {st.errors0} err_opp {st.errors1}  "
          f"max_move {st.max_move_time0:.3f}s  decisions {dec} fallbacks {fb}  "
          f"({time.time()-t0:.0f}s)")
    if fb:
        print("  WARNING: silent fallbacks -- this measurement is not of the model")
    json.dump({"opp": kind, "pure": pure, "n": st.n, "w": st.wins0, "l": st.wins1,
               "d": st.draws, "err_us": st.errors0, "wr": wr, "z": z,
               "max_move_time": st.max_move_time0},
              open(os.path.join(HERE, "results", f"h2h2_{kind}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
