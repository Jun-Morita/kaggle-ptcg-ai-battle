"""exp060 final gate (pre-registered, primary = FINAL CENTER vector).

Primary: center (mean) overrides vs stock, mirror n=600 CRN fresh seeds, >= 0.55.
Secondary: best-fitness historical individual (selection-biased; report only).
"""
import json, math, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tune_snes as T

def main():
    st = json.load(open(T.STATE))
    from harness_crn import run_gauntlet  # loaded via tune_snes path setup
    T.STOCK = T._load_stock(); T.KEYS[:] = sorted(T.STOCK.keys())
    center_ov = T._overrides_from_x(st["mean"])
    json.dump(center_ov, open(os.path.join(T.RESULTS, "center_final.json"), "w"), indent=1)
    # best historical individual
    best_gen = max(st["hist"], key=lambda h: h["best"])["gen"]
    best_ov = json.load(open(os.path.join(T.RESULTS, f"best_gen{best_gen:03d}.json")))
    arms = [("CENTER(primary)", center_ov), (f"best_gen{best_gen}(secondary)", best_ov)]
    GATE_SEED = 20260899
    for name, ov in arms:
        t0 = time.time()
        stg = run_gauntlet(T._make_pub(ov), T._make_pub(None), n_games=600,
                           swap_sides=True, crn_seed_base=GATE_SEED)
        print(f"{name:24s} wr={stg.winrate0:.4f} ({stg.wins0}-{stg.wins1}-{stg.draws}) "
              f"err=({stg.errors0},{stg.errors1}) {time.time()-t0:.0f}s  [gate >=0.55]", flush=True)

if __name__ == "__main__":
    from harness_crn import load_engine
    load_engine()
    main()
