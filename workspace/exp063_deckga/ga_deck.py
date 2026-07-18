"""exp063 -- GA over the koff LO deck's FLEX slots (core fixed, trainers evolve).

Rationale: koff's holes are STRUCTURAL (ability chip bypasses Safeguard/NZ,
exp054-G; Spidops rising, pilkwang 07-18) and the pilot is verified leak-free.
The remaining axis is the LIST -- discrete space, GA-native. exp059's deck⊗pilot
lesson is respected by FIXING the pilot-critical core (attacker/wall/energy/NZ/
F-tutor) and evolving only the 34 trainer flex slots; the pilot reads deck.csv,
so list changes need no code change.

CORE (26, fixed): Great Tusk x4, Dwebble x4, Crustle x4, Rock Fighting E x4,
Mist E x4, Fighting Gong x4, Neutralization Zone x1 (ACE SPEC), Terrakion x1.
FLEX (34): everything else, per-id <= 4, no additional ACE SPECs.

Pre-registered (before first run):
  - fitness = SILVER-band weighted winrate (EB.SILVER_BAND pool), n=120/candidate,
    all candidates in a generation share the same CRN seed base
  - pop 16 (stock injected gen0 + 2-elite carryover, elites re-evaluated each gen),
    tournament-2 parents, uniform flex crossover, 1-2 swap mutations
  - GATE: best individual vs stock at n=600 fresh seeds, weighted wr improvement
    >= +0.03 AND no single matchup regression > 0.05 -> then side probes
    (starmie_real / grimm_froslass / pure_wall) -> only then ship talk
  - KILL: no individual beats stock+2SE on shared seeds within 20 generations
    -> honest negative #21 (exp036 small-n GA trap is countered by CRN + the
    n=600 confirm gate; generation-best numbers are selection-biased, never used
    for conclusions)

Usage: uv run python ga_deck.py [--gens 20] [--pop 16] [--n 120] [--workers 2] [--resume]
"""
from __future__ import annotations
import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))

SEED = 20260731
RESULTS = os.path.join(HERE, "results")
STATE = os.path.join(RESULTS, "state.json")

CORE = Counter({58: 4, 344: 4, 345: 4, 20: 4, 11: 4, 1142: 4, 1247: 1, 607: 1})
STOCK_FLEX = Counter({1152: 4, 1086: 4, 1122: 4, 1123: 4, 1197: 4, 1185: 4,
                      1182: 4, 1204: 2, 1194: 2, 1121: 1, 1147: 1})
FLEX_SIZE = sum(STOCK_FLEX.values())          # 34
# new-card gene pool (trainers/tools seen in current band decks; no ACE SPECs,
# no TR-only cards, Battle Cage is the single stadium candidate on purpose)
POOL = sorted(set(STOCK_FLEX) | {
    1120,   # Crushing Hammer
    1081,   # Enhanced Hammer
    1097,   # Night Stretcher
    # 1159 Hero's Cape EXCLUDED: crashes the LO pilot every game (run1 diagnostic;
    # crash-safety is a hard ship requirement, so it can never be in a genome)
    1161,   # Handheld Fan
    1264,   # Battle Cage
    1227,   # Lillie's Determination
    1225,   # Hilda
    1231,   # Dawn
    1223,   # Harlequin
})


def genome_to_deck(flex: Counter) -> list[int]:
    deck = []
    for cid, k in sorted((CORE + flex).items()):
        deck += [cid] * k
    assert len(deck) == 60, len(deck)
    return deck


def legal(flex: Counter) -> bool:
    if sum(flex.values()) != FLEX_SIZE:
        return False
    for cid, k in flex.items():
        if k < 0 or (CORE + flex)[cid] > 4:
            return False
    return True


def mutate(flex: Counter, rng: random.Random) -> Counter:
    f = Counter(flex)
    for _ in range(rng.choice((1, 1, 2))):
        # remove one copy
        cids = [c for c in f for _ in range(f[c])]
        out = rng.choice(cids)
        f[out] -= 1
        if f[out] == 0:
            del f[out]
        # add one copy (respect <=4)
        cands = [c for c in POOL if (CORE + f)[c] < 4]
        f[rng.choice(cands)] += 1
    return f


def crossover(a: Counter, b: Counter, rng: random.Random) -> Counter:
    child = Counter()
    for cid in set(a) | set(b):
        lo, hi = sorted((a.get(cid, 0), b.get(cid, 0)))
        child[cid] = rng.randint(lo, hi)
    child = Counter({c: k for c, k in child.items() if k > 0})
    # repair size
    n = sum(child.values())
    while n > FLEX_SIZE:
        cids = [c for c in child for _ in range(child[c])]
        c = rng.choice(cids)
        child[c] -= 1
        if child[c] == 0:
            del child[c]
        n -= 1
    while n < FLEX_SIZE:
        cands = [c for c in POOL if (CORE + child)[c] < 4]
        child[rng.choice(cands)] += 1
        n += 1
    return child


# ---------------- worker side ----------------
_ctx = {}


def _init_worker():
    import eval_both_bands as EB
    sys.path.insert(0, EB.CRN)
    from harness_crn import run_gauntlet
    from eval_ko_off import make_lo_koforce
    _ctx["EB"] = EB
    _ctx["run"] = run_gauntlet
    _ctx["mk"] = make_lo_koforce
    _ctx["opp"] = EB.opponents()


def _eval(args):
    deck, n, seed_base = args
    EB, run, mk, opp = _ctx["EB"], _ctx["run"], _ctx["mk"], _ctx["opp"]
    tot_w = sum(EB.SILVER_BAND.values())
    wsum = 0.0
    per = {}
    errs = 0
    for oname, w in EB.SILVER_BAND.items():
        odeck, fac = opp[oname]
        n_o = max(4, 2 * round(n * (w / tot_w) / 2))
        st = run(mk(list(deck), False), fac(odeck), n_games=n_o, swap_sides=True,
                 crn_seed_base=seed_base + (abs(hash(oname)) % 99991))
        per[oname] = st.winrate0
        errs += st.errors0 + st.errors1
        wsum += w * st.winrate0
    return wsum / tot_w, per, errs


# ---------------- driver ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gens", type=int, default=20)
    ap.add_argument("--pop", type=int, default=16)
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--resume", action="store_true")
    a = ap.parse_args()
    os.makedirs(RESULTS, exist_ok=True)
    rng = random.Random(SEED)

    if a.resume and os.path.exists(STATE):
        st = json.load(open(STATE))
        pop = [Counter({int(k): v for k, v in f.items()}) for f in st["pop"]]
        g0, hist = st["gen"] + 1, st["hist"]
        for _ in range(g0 * 1000):
            rng.random()
        print(f"resumed at gen {g0}", flush=True)
    else:
        pop = [Counter(STOCK_FLEX)]
        while len(pop) < a.pop:
            pop.append(mutate(Counter(STOCK_FLEX), rng))
        g0, hist = 0, []

    pool = Pool(a.workers, initializer=_init_worker)
    stock_deck = genome_to_deck(Counter(STOCK_FLEX))
    for g in range(g0, a.gens):
        t0 = time.time()
        seed_base = SEED + 100_000 * (g + 1)
        jobs = [(genome_to_deck(f), a.n, seed_base) for f in pop] + \
               [(stock_deck, a.n, seed_base)]
        out = pool.map(_eval, jobs)
        fits = [o[0] for o in out[:-1]]
        stock_fit = out[-1][0]
        errs = sum(o[2] for o in out)
        order = sorted(range(len(pop)), key=lambda i: -fits[i])
        best_i = order[0]
        se = (0.25 / a.n) ** 0.5
        hist.append({"gen": g, "best": fits[best_i], "stock": stock_fit,
                     "mean": sum(fits) / len(fits), "errs": errs,
                     "beats_stock_2se": fits[best_i] >= stock_fit + 2 * se})
        json.dump({"flex": dict(pop[best_i]), "fit": fits[best_i],
                   "stock_fit": stock_fit, "per": out[best_i][1]},
                  open(os.path.join(RESULTS, f"best_gen{g:03d}.json"), "w"), indent=1)
        print(f"gen {g:3d}  best={fits[best_i]:.3f}  stock={stock_fit:.3f}  "
              f"mean={sum(fits)/len(fits):.3f}  errs={errs}  (SE~{se:.3f})  "
              f"{time.time()-t0:.0f}s", flush=True)

        # next generation: 2 elites + offspring
        nxt = [Counter(pop[order[0]]), Counter(pop[order[1]])]
        while len(nxt) < a.pop:
            t1, t2 = rng.sample(range(len(pop)), 2)
            p1 = pop[t1] if fits[t1] >= fits[t2] else pop[t2]
            t3, t4 = rng.sample(range(len(pop)), 2)
            p2 = pop[t3] if fits[t3] >= fits[t4] else pop[t4]
            child = crossover(p1, p2, rng)
            child = mutate(child, rng)
            if legal(child):
                nxt.append(child)
        pop = nxt
        json.dump({"gen": g, "pop": [dict(f) for f in pop], "hist": hist},
                  open(STATE, "w"))
    pool.close(); pool.join()


if __name__ == "__main__":
    main()
