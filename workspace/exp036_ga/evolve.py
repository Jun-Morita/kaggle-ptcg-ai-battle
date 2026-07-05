"""exp036 — GA over the 12-gene pilot genome (Stage A: global genome).

Fitness: ladder-share-weighted winrate vs the opponent pool on the NATIVE engine.
Population 24, elites 4 (re-evaluated every generation), tournament(k=3) selection,
uniform crossover 0.5, gaussian mutation sigma=0.3 per gene p=0.3, genes clipped to
[-2, 2]. Per-generation JSON checkpoints in gens/ -> resumable after WSL restarts.
Holdout (LO + charmq mirror) evaluated for the champion every 5 generations.

Usage: uv run python evolve.py [n_generations]   (resumes from gens/ automatically)
"""
from __future__ import annotations
import glob
import json
import os
import random
import sys
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
NATIVE = os.path.join(ROOT, "workspace", "exp032_valuescale", "native")

POP, ELITE, TOUR = 24, 4, 3
MUT_P, MUT_S, CX_P = 0.3, 0.3, 0.5
N_FIT = 48
# (name, weight, games) — games sum to N_FIT, proportional to ladder share
POOL_SPEC = [("ex_lucario", 0.30, 14), ("dragapult", 0.20, 10), ("mirror", 0.20, 10),
             ("grimmsnarl", 0.10, 5), ("crustle", 0.10, 5), ("archaludon", 0.10, 4)]

_W = {}   # per-process worker state


def _init_worker():
    for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
              "exp013_router", "exp018_adaptive", "exp020_deckinnov", "exp022_megastarmie",
              "exp023_revenge", "exp025_unkoable", "exp030_lomill", "exp036_ga"):
        sp = os.path.join(ROOT, "workspace", p)
        if sp not in sys.path:
            sys.path.insert(0, sp)
    os.environ.setdefault("REVENGE_BONUS", "50")
    import harness
    harness.load_engine(NATIVE)
    import anti_crustle as AC
    import revenge_policy as RV
    import load_dragapult as LD
    from load_archaludon import make_archaludon_agent
    from load_lo import make_lo_agent
    import genome_policy as GP
    v_trev = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
    grim = json.load(open(os.path.join(ROOT, "workspace", "exp028_debauchery", "grimmsnarl_deck.json")))
    ch = json.load(open(os.path.join(ROOT, "workspace", "exp012_nonex", "charmq_deck.json")))
    ch = ch.get("charmq") if isinstance(ch, dict) else ch
    _W["harness"] = harness
    _W["GP"] = GP
    _W["deck"] = v_trev
    _W["mk"] = {
        "ex_lucario": lambda: AC.make_agent(AC.LUCARIO_DECK),
        "dragapult": LD.make_dragapult_agent,
        "mirror": lambda: RV.make_agent(v_trev),
        "grimmsnarl": lambda: RV.make_agent(grim),
        "crustle": AC.make_crustle_agent,
        "archaludon": make_archaludon_agent,
        "lo": make_lo_agent,
        "charmq_mirror": lambda: RV.make_agent(ch),
    }


def _eval_genome(args):
    genome, spec, seed = args
    if not _W:
        _init_worker()
    h, GP = _W["harness"], _W["GP"]
    cand = GP.make_agent(_W["deck"], genome)
    total_w, score = 0.0, 0.0
    detail = {}
    for name, w, n in spec:
        opp = _W["mk"][name]()
        wins = 0
        for g in range(n):
            a0, a1 = (cand, opp) if g % 2 == 0 else (opp, cand)
            try:
                r = h.run_match(a0, a1, cg_dir=NATIVE)
            except Exception:
                continue
            me = 0 if g % 2 == 0 else 1
            if r.winner == me:
                wins += 1
        wr = wins / max(n, 1)
        detail[name] = wr
        score += w * wr
        total_w += w
    return score / max(total_w, 1e-9), detail


def _latest_gen():
    files = sorted(glob.glob(os.path.join(HERE, "gens", "gen_*.json")))
    if not files:
        return None, -1
    f = files[-1]
    return json.load(open(f)), int(os.path.basename(f)[4:7])


def main():
    n_gen = int(sys.argv[1]) if len(sys.argv) > 1 else 40
    os.makedirs(os.path.join(HERE, "gens"), exist_ok=True)
    rng = random.Random(2026)
    import genome_policy as GPl
    NG = GPl.N_GENES

    ck, g0 = _latest_gen()
    if ck:
        pop = ck["pop"]
        rng.seed(ck["rng_seed"])
        print(f"resuming from gen {g0}", flush=True)
    else:
        pop = [[0.0] * NG]                        # seed with identity (v012)
        while len(pop) < POP:
            pop.append([rng.gauss(0, 0.4) for _ in range(NG)])
        pop = [[max(-2, min(2, x)) for x in ind] for ind in pop]

    with ProcessPoolExecutor(max_workers=4, initializer=_init_worker) as ex:
        for gen in range(g0 + 1, n_gen):
            jobs = [(ind, POOL_SPEC, gen * 1000 + i) for i, ind in enumerate(pop)]
            results = list(ex.map(_eval_genome, jobs))
            fits = [r[0] for r in results]
            order = sorted(range(POP), key=lambda i: -fits[i])
            champ = pop[order[0]]
            print(f"gen {gen:03d}: best={fits[order[0]]:.3f} "
                  f"mean={sum(fits)/POP:.3f} champ_detail={results[order[0]][1]}", flush=True)
            if gen % 5 == 0:
                ho_spec = [("lo", 0.5, 20), ("charmq_mirror", 0.5, 20)]
                ho = ex.submit(_eval_genome, (champ, ho_spec, 999000 + gen)).result()
                print(f"  holdout: {ho[0]:.3f} {ho[1]}", flush=True)
            seed_out = rng.randrange(10 ** 9)
            json.dump({"pop": pop, "fits": fits, "order": order, "rng_seed": seed_out,
                       "champ": champ},
                      open(os.path.join(HERE, "gens", f"gen_{gen:03d}.json"), "w"))
            # next generation
            new = [pop[i] for i in order[:ELITE]]
            while len(new) < POP:
                def pick():
                    c = rng.sample(range(POP), TOUR)
                    return pop[max(c, key=lambda i: fits[i])]
                a, b = pick(), pick()
                child = [ai if rng.random() < CX_P else bi for ai, bi in zip(a, b)]
                child = [max(-2, min(2, x + (rng.gauss(0, MUT_S) if rng.random() < MUT_P else 0)))
                         for x in child]
                new.append(child)
            pop = new
            rng.seed(seed_out)
    print("done", flush=True)


if __name__ == "__main__":
    main()
