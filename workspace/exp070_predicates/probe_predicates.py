"""exp070 — exhaustive predicate-misspecification scan of the SHIPPED koff pilot.

Rationale: piloting has a HUGE dynamic range (exp055: the same 60 cards score
0.28 with our generic pilot vs 3-0 for a real pilot) yet every generic method
failed -- weights single/joint (exp058/060), BC/AC (exp064), search (exp068).
The ONE method that ever produced a win was finding a MISSPECIFIED PREDICATE and
disabling it: KO_OFF (+0.046 even after the exp069 recalibration).

That method has only ever been applied to 2 of the pilot's ~12 gates
(should_ko_mode, should_wall_mode). This scans them all.

Two failure signatures we are hunting, both seen before:
  (a) NEVER FIRES  -- should_wall_mode was 0/783 in the 07-13 probe, i.e. the
      intended behaviour is simply absent.
  (b) FIRES OFTEN, CORRELATES WITH LOSSES -- should_ko_mode fired on 73.2% of
      calls for a 1W-11L record; that was KO_OFF.

Priority target: should_wall_mode. Walls are 32.6% of koff's losses under the
calibrated pool (the single largest hole), and the 07-13 probe used our OWN
ex-less AC wall, whose own caveat reads: "the real pure wall runs Mega Kangaskhan
ex, so wall_mode COULD fire against it". The predicate guarding our biggest hole
has never been instrumented against the real thing.

Output: per matchup, per predicate -- call count, fire rate, and fire rate split
by eventual W/L. Diagnosis only; counterfactual forcing comes after.
"""
from __future__ import annotations
import os, sys, json, collections

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB
sys.path.insert(0, EB.CRN)
from harness_crn import load_engine, _empty_deck_obs, _validate_selection

KOFF_DIR = os.path.join(WS, "exp054_upperband", "build_koff2")

# Gates worth instrumenting. Boolean predicates only: their fire rate is
# directly interpretable. (card_keep_value / play_score are scorers, not gates.)
PREDICATES = [
    "should_wall_mode",
    "should_ko_mode",
    "opponent_can_attack_soon",
    "facing_lucario_strong",
    "active_is_ready_crustle",
    "active_tusk_ready",
    "can_bench_more",
    "opponent_has_ex_or_ex_line_pressure",
]


def load_koff():
    """Load the shipped pilot as a fresh module so we can wrap its functions."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        f"koff_{load_koff.n}", os.path.join(KOFF_DIR, "main.py"))
    load_koff.n += 1
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(KOFF_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return mod


load_koff.n = 0


def instrument(mod, tally):
    """Wrap each predicate to count calls and True-returns."""
    found = []
    for name in PREDICATES:
        fn = getattr(mod, name, None)
        if fn is None or not callable(fn):
            continue
        found.append(name)

        def make(name, fn):
            def wrapped(*a, **k):
                r = fn(*a, **k)
                tally[name]["calls"] += 1
                if r:
                    tally[name]["fired"] += 1
                return r
            return wrapped

        setattr(mod, name, make(name, fn))
    return found


def play(mod, opp_agent, our_seat, crn_seed, max_steps=5000):
    api, game = load_engine()
    to_obs = api.to_observation_class
    ours = mod.agent
    agents = [ours, opp_agent] if our_seat == 0 else [opp_agent, ours]
    decks = [[int(x) for x in a(_empty_deck_obs())] for a in agents]
    os.environ["CG_CRN_SEED"] = str(crn_seed)
    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return None
    try:
        for _ in range(max_steps):
            o = to_obs(obs)
            if o.current is not None and o.current.result != -1:
                break
            if o.select is None:
                break
            pi = o.current.yourIndex
            obs = game.battle_select(_validate_selection(agents[pi](obs), o.select))
    except Exception:
        pass
    o = to_obs(obs)
    w = o.current.result if o.current is not None else -1
    game.battle_finish()
    return w == our_seat


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    only = sys.argv[2] if len(sys.argv) > 2 else None
    opp_all = EB.opponents()
    targets = [only] if only else list(EB.SILVER_BAND.keys())

    report = {}
    for oname in targets:
        deck, fac = opp_all[oname]
        # tallies split by eventual outcome
        per = {"W": collections.defaultdict(lambda: {"calls": 0, "fired": 0}),
               "L": collections.defaultdict(lambda: {"calls": 0, "fired": 0})}
        wins = 0
        names = None
        for g in range(n):
            tally = collections.defaultdict(lambda: {"calls": 0, "fired": 0})
            mod = load_koff()
            names = instrument(mod, tally)
            our_seat = g % 2
            won = play(mod, fac(deck), our_seat, crn_seed=20261100 + g)
            if won is None:
                continue
            wins += int(won)
            k = "W" if won else "L"
            for pname, c in tally.items():
                per[k][pname]["calls"] += c["calls"]
                per[k][pname]["fired"] += c["fired"]
        report[oname] = {"n": n, "wins": wins, "W": dict(per["W"]), "L": dict(per["L"])}
        print(f"\n=== {oname}  ({wins}W-{n-wins}L)  weight {EB.SILVER_BAND.get(oname,0):.3f} ===")
        print(f"  {'predicate':38s}{'fire% W':>10}{'fire% L':>10}{'calls/g':>10}")
        for pname in (names or []):
            w, l = per["W"][pname], per["L"][pname]
            fw = 100 * w["fired"] / w["calls"] if w["calls"] else float("nan")
            fl = 100 * l["fired"] / l["calls"] if l["calls"] else float("nan")
            cg = (w["calls"] + l["calls"]) / max(1, n)
            flag = ""
            if w["calls"] + l["calls"] > 0 and w["fired"] + l["fired"] == 0:
                flag = "  <== NEVER FIRES"
            elif w["calls"] and l["calls"] and abs(fw - fl) > 12:
                flag = "  <== W/L SPLIT"
            print(f"  {pname:38s}{fw:10.1f}{fl:10.1f}{cg:10.1f}{flag}")
    json.dump(report, open(os.path.join(HERE, "predicates.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
