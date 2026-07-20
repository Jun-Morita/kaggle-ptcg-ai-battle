"""exp068 step ① / ②: what is "predict the opponent, then choose our move" WORTH?

Motivation: our shipped agent (koff / build_koff2) contains NO search at all --
grep finds no search_begin, no opponent_deck/hand/prize. So opponent modelling is
genuinely untried on our main line. Before building anything, measure the lever.

exp060 measured search ON vs OFF only in the MIRROR (+0.037) and concluded the
objective was structurally capped. But mirror is the WORST case for prediction
(both seats identical, draw-order dominated). The band pool is asymmetric, so the
lever could be much larger there -- that is the untested part of exp060's claim.

Vehicle: pub1034 (tientrum's search-augmented Alakazam) is the only agent we have
with a working determinization + search layer and a clean USE_SEARCH toggle.
We measure the SAME agent, search ON vs OFF, over the full silver band pool.

Reading:
  - If ON-OFF is ~0 across the band, opponent prediction is a dead lever for this
    engine//game and no amount of better prediction machinery will pay -- close
    the lane cheaply (this is exactly the exp060 "lever-measurement-first" rule).
  - If ON-OFF is large in the matchups where koff is weak (dragapult, walls),
    then porting a search layer onto koff has measurable headroom, and we size
    the build against that number.

CRN-paired: both arms see identical seeds per matchup, so the difference is the
search layer alone.
"""
from __future__ import annotations
import os, sys, time, json

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import run_gauntlet
sys.path.insert(0, os.path.join(WS, "exp057_pubalakazam"))
import load_pub1034 as LP


def make_arm(use_search: bool):
    """pub1034 with its search layer forced ON or OFF (same weights either way)."""
    import importlib.util
    LP.load_engine()
    LP._n[0] += 1
    spec = importlib.util.spec_from_file_location(
        f"arm_{LP._n[0]}", os.path.join(LP.AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(LP.AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    mod.USE_SEARCH = bool(use_search)
    return mod.agent


def verify_toggle():
    """Confirm the toggle actually changes search_begin call counts (exp066 rule:
    never trust an advertised mechanism without a call count)."""
    import cg.api as api
    calls = {"on": 0, "off": 0}
    orig = api.search_begin
    opp = EB.opponents()
    deck, fac = opp["archaludon"]
    for label, flag in (("on", True), ("off", False)):
        n = [0]
        def probe(*a, **k):
            n[0] += 1
            return orig(*a, **k)
        api.search_begin = probe
        try:
            run_gauntlet(make_arm(flag), fac(deck), n_games=2, swap_sides=True,
                         crn_seed_base=4242)
        finally:
            api.search_begin = orig
        calls[label] = n[0]
    print(f"[verify] search_begin calls: ON={calls['on']}  OFF={calls['off']}")
    if calls["on"] == 0:
        print("[verify] WARNING: search never fired even with USE_SEARCH=True; "
              "the measurement below would be meaningless.")
    return calls


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    verify_toggle()
    opp = EB.opponents()
    res = {}
    for oname, w in sorted(EB.SILVER_BAND.items(), key=lambda x: -x[1]):
        deck, fac = opp[oname]
        row = {}
        base = EB.SEED + abs(hash("lever" + oname)) % 99991
        for label, flag in (("on", True), ("off", False)):
            t0 = time.time()
            st = run_gauntlet(make_arm(flag), fac(deck), n_games=n, swap_sides=True,
                              crn_seed_base=base)   # identical seeds both arms
            row[label] = st.winrate0
            row[label + "_t"] = time.time() - t0
        res[oname] = row
        d = row["on"] - row["off"]
        print(f"  {oname:16s} w={w:.3f}  ON {row['on']:.3f}  OFF {row['off']:.3f}  "
              f"delta {d:+.3f}   ({row['on_t']:.0f}s/{row['off_t']:.0f}s)", flush=True)
    tot = sum(EB.SILVER_BAND.values())
    on = sum(w * res[o]["on"] for o, w in EB.SILVER_BAND.items()) / tot
    off = sum(w * res[o]["off"] for o, w in EB.SILVER_BAND.items()) / tot
    print(f"\nSILVER weighted: search ON {on:.4f}  OFF {off:.4f}  "
          f"LEVER = {on-off:+.4f}")
    json.dump(res, open(os.path.join(HERE, "lever.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
