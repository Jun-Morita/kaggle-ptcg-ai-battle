"""exp060 -- JOINT optimization of pub1034's 69 WEIGHTS via separable NES.

Claim tested: exp058 showed single-knob x2-direction perturbations are a local
optimum (defaults best). That does NOT rule out a better JOINT setting. exp059
ruled out the deck axis. This is the remaining untested axis-combination.

Objective: mirror winrate vs STOCK pub1034 (the ladder mirror field is
overwhelmingly stock-lineage descendants, so vs-stock has unusually high
external validity; v025's live fixed point 884 was set by mirror 0.32 at 43%
band share).

Design (all pre-registered):
  - search space: x in R^69, per-knob multiplier 2**x on the stock value
    (all 69 stock values are positive; sign/zero issues absent)
  - sNES, lambda=12 mirrored (6 antithetic pairs), sigma0=0.30 (~ +-23%)
  - each generation: all 12 candidates play n=150 vs stock with the SAME
    CRN seed base (CRN shared across candidates -> ranking noise crushed)
  - center evaluated each gen on a FIXED held-out seed base (progress track)
  - 4 worker processes; resumable (results/state.json, --resume)
GATE (after the run, before any ship talk):
  best candidate at n=600 fresh seeds: mirror >= 0.55, then sides
  marnie/pure_wall/archaludon/crustle_LO n=200 no regression.
KILL: if no generation's best exceeds baseline + 2*SE on shared seeds by
  gen 40, close as the 20th honest negative ("weight landscape flat for the
  mirror even jointly").

Usage:
  uv run python tune_snes.py [--gens N] [--pop 12] [--n 150] [--resume]
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import math
import os
import random
import sys
import time
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
for p in ("exp052_crn", "exp001_harness", "exp057_pubalakazam"):
    sys.path.insert(0, os.path.join(WS, p))

SEED = 20260726
RESULTS = os.path.join(HERE, "results")
STATE = os.path.join(RESULTS, "state.json")

KEYS: list[str] = []   # filled in worker/main from stock WEIGHTS
STOCK: dict = {}


def _load_stock():
    from load_pub1034 import AGENT_DIR
    spec = importlib.util.spec_from_file_location("pubw_ref", os.path.join(AGENT_DIR, "main.py"))
    mod = importlib.util.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    return dict(mod.WEIGHTS)


def _make_pub(overrides):
    from load_pub1034 import AGENT_DIR, pub1034_deck
    import importlib.util as iu
    _make_pub._n = getattr(_make_pub, "_n", 0) + 1
    spec = iu.spec_from_file_location(f"pub_c{os.getpid()}_{_make_pub._n}",
                                      os.path.join(AGENT_DIR, "main.py"))
    mod = iu.module_from_spec(spec)
    prev = os.getcwd()
    try:
        os.chdir(AGENT_DIR)
        spec.loader.exec_module(mod)
    finally:
        os.chdir(prev)
    if overrides:
        mod.WEIGHTS.update(overrides)
    deck = pub1034_deck()

    def agent(obs):
        if obs.get("select") is None:
            return list(deck)
        return mod.agent(obs)
    return agent


def _overrides_from_x(x):
    return {k: STOCK[k] * (2.0 ** xi) for k, xi in zip(KEYS, x)}


_worker_ready = False


def _init_worker():
    global _worker_ready, STOCK, KEYS
    from harness_crn import load_engine
    load_engine()
    STOCK = _load_stock()
    KEYS[:] = sorted(STOCK.keys())
    _worker_ready = True


def _eval_candidate(args):
    """(x_vector or None for stock-center, n_games, crn_seed_base) -> winrate."""
    x, n, seed_base = args
    from harness_crn import run_gauntlet
    ov = _overrides_from_x(x) if x is not None else None
    st = run_gauntlet(_make_pub(ov), _make_pub(None), n_games=n,
                      swap_sides=True, crn_seed_base=seed_base)
    return (st.wins0, st.wins1, st.draws, st.errors0, st.errors1)


def utilities(lam):
    # Hansen rank-based utilities, sum ~ 0
    us = [max(0.0, math.log(lam / 2 + 1) - math.log(i + 1)) for i in range(lam)]
    s = sum(us)
    return [u / s - 1.0 / lam for u in us]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=40)
    ap.add_argument("--pop", type=int, default=12)     # even (mirrored pairs)
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)

    global STOCK, KEYS
    from harness_crn import load_engine
    load_engine()
    STOCK = _load_stock()
    KEYS[:] = sorted(STOCK.keys())
    d = len(KEYS)
    assert d == 69, d

    eta_m = 1.0
    eta_s = (3 + math.log(d)) / (5 * math.sqrt(d))
    lam = a.pop
    us = utilities(lam)

    if a.resume and os.path.exists(STATE):
        st = json.load(open(STATE))
        mean, log_sigma, g0, hist = st["mean"], st["log_sigma"], st["gen"] + 1, st["hist"]
        print(f"resumed at gen {g0}", flush=True)
    else:
        mean = [0.0] * d
        log_sigma = [math.log(0.30)] * d
        g0, hist = 0, []

    rng = random.Random(SEED)
    # burn the rng to stay deterministic across resumes
    for _ in range(g0 * lam * d):
        rng.gauss(0, 1)

    pool = Pool(a.workers, initializer=_init_worker)
    for g in range(g0, a.gens):
        t0 = time.time()
        zs = []
        for _ in range(lam // 2):
            z = [rng.gauss(0, 1) for _ in range(d)]
            zs.append(z)
            zs.append([-v for v in z])
        sig = [math.exp(v) for v in log_sigma]
        xs = [[m + s * zi for m, s, zi in zip(mean, sig, z)] for z in zs]

        seed_base = SEED + 1000 * (g + 1)          # shared by ALL candidates this gen
        center_seeds = SEED + 777_000_000          # fixed held-out base, every gen
        jobs = [(x, a.n, seed_base) for x in xs] + [(None, a.n, center_seeds),
                                                    (mean, a.n, center_seeds)]
        out = pool.map(_eval_candidate, jobs)
        cand, (b_w, b_l, *_b), (c_w, c_l, *_c) = out[:lam], out[lam], out[lam + 1]
        wrs = [w / max(1, w + l) for (w, l, dr, e0, e1) in cand]
        errs = sum(e0 + e1 for (w, l, dr, e0, e1) in cand)
        base_wr = b_w / max(1, b_w + b_l)          # stock vs stock on held-out seeds (~0.5 sanity)
        center_wr = c_w / max(1, c_w + c_l)        # current mean vs stock, held-out

        order = sorted(range(lam), key=lambda i: -wrs[i])
        g_m = [0.0] * d
        g_s = [0.0] * d
        for rank, i in enumerate(order):
            u = us[rank]
            z = zs[i]
            for j in range(d):
                g_m[j] += u * z[j]
                g_s[j] += u * (z[j] * z[j] - 1.0)
        mean = [m + eta_m * s * gm for m, s, gm in zip(mean, sig, g_m)]
        log_sigma = [ls + 0.5 * eta_s * gs for ls, gs in zip(log_sigma, g_s)]

        best_i = order[0]
        hist.append({"gen": g, "best": wrs[best_i], "pop_mean": sum(wrs) / lam,
                     "center": center_wr, "stock_sanity": base_wr, "errs": errs})
        json.dump({"gen": g, "mean": mean, "log_sigma": log_sigma, "hist": hist},
                  open(STATE, "w"))
        json.dump(_overrides_from_x(xs[best_i]),
                  open(os.path.join(RESULTS, f"best_gen{g:03d}.json"), "w"), indent=1)
        se = math.sqrt(0.25 / a.n)
        print(f"gen {g:3d}  best={wrs[best_i]:.3f}  pop={sum(wrs)/lam:.3f}  "
              f"center={center_wr:.3f}  sanity={base_wr:.3f}  errs={errs}  "
              f"(SE~{se:.3f})  {time.time()-t0:.0f}s", flush=True)
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
