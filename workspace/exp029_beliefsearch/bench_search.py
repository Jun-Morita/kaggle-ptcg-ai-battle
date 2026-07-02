"""exp029 Stage 0 — measure the wall-clock cost of the search primitives that the
belief-search v2 design (opponent-reply guard / selective PIMC) would pay per decision.

Plays real games (v012 deck + revenge policy, self-play) and at MAIN single-pick
decisions times: search_begin, a single search_step, a full OUR-turn rollout, and a
full OPPONENT-turn rollout (the Stage-1 guard's unit of work). Placeholder
determinization — engine cost is identical, fidelity irrelevant for timing.

Usage: uv run python bench_search.py [n_games] [max_samples]
"""
from __future__ import annotations
import dataclasses, json, os, statistics, sys, time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
api, _ = load_engine()
import revenge_policy as P  # noqa

to_obs = api.to_observation_class
V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))
T = {"begin": [], "step": [], "our_turn": [], "opp_turn": [], "steps_per_opp_turn": []}


def _clamp(sel, select):
    n = len(select.option)
    sel = [i for i in sel if 0 <= i < n]
    sel = list(dict.fromkeys(sel))[: max(1, select.maxCount)]
    if not (select.minCount <= len(sel) <= select.maxCount):
        sel = list(range(min(max(1, select.minCount), n)))
    return sel


def make_bench_agent(deck, max_samples):
    base = P.make_agent(deck)
    inner = P.make_agent(deck)  # rollout policy (separate closure, same rules)

    import random
    rng = random.Random(0)

    def det(obs, me, opp):
        # realistic fill: sample card ids from the real decklist so rollouts play
        # full turns (an all-energy placeholder deck ends turns in ~3 steps)
        pool = list(deck)
        samp = lambda k: [pool[rng.randrange(len(pool))] for _ in range(k)]
        return dict(your_deck=samp(me.deckCount), your_prize=samp(len(me.prize)),
                    opponent_deck=samp(opp.deckCount),
                    opponent_prize=samp(len(opp.prize)),
                    opponent_hand=samp(opp.handCount),
                    opponent_active=samp(1) if (len(opp.active) > 0 and opp.active[0] is None) else [])

    def agent(obs_dict):
        sel_out = base(obs_dict)
        if len(T["opp_turn"]) >= max_samples:
            return sel_out
        obs = to_obs(obs_dict)
        if obs.select is None or obs.select.maxCount != 1 or len(obs.select.option) <= 1:
            return sel_out
        my = obs.current.yourIndex
        me, opp = obs.current.players[my], obs.current.players[1 - my]
        try:
            t0 = time.perf_counter()
            ss = api.search_begin(obs, **det(obs, me, opp))
            T["begin"].append(time.perf_counter() - t0)

            t0 = time.perf_counter()
            ss = api.search_step(ss.searchId, _clamp(sel_out, obs.select))
            T["step"].append(time.perf_counter() - t0)

            # finish OUR turn with the rollout policy
            t0 = time.perf_counter()
            guard = 0
            while guard < 60:
                guard += 1
                o = ss.observation
                if o.current is None or o.current.result != -1 or o.select is None:
                    break
                if o.current.yourIndex != my:
                    break
                ss = api.search_step(ss.searchId, _clamp(inner(dataclasses.asdict(o)), o.select))
            T["our_turn"].append(time.perf_counter() - t0)

            # play the OPPONENT's whole turn with the same rules = Stage-1 guard unit
            t0 = time.perf_counter()
            nsteps = 0
            guard = 0
            while guard < 80:
                guard += 1
                o = ss.observation
                if o.current is None or o.current.result != -1 or o.select is None:
                    break
                if o.current.yourIndex == my:
                    break
                ss = api.search_step(ss.searchId, _clamp(inner(dataclasses.asdict(o)), o.select))
                nsteps += 1
            T["opp_turn"].append(time.perf_counter() - t0)
            T["steps_per_opp_turn"].append(nsteps)
        except Exception as e:
            T.setdefault("errors", []).append(repr(e))
        finally:
            try:
                api.search_end()
            except Exception:
                pass
        return sel_out

    return agent


def stats(v):
    if not v:
        return "n=0"
    s = sorted(v)
    return (f"n={len(v)} mean={statistics.mean(v):.3f}s median={s[len(s)//2]:.3f}s "
            f"p90={s[int(len(s)*0.9)]:.3f}s max={s[-1]:.3f}s")


def main():
    n_games = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    max_samples = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    cand = make_bench_agent(V_TREV, max_samples)
    opp = P.make_agent(V_TREV)
    st = run_gauntlet(cand, opp, n_games=n_games, swap_sides=True)
    print(f"games={n_games} result {st.wins0}-{st.wins1}-{st.draws} err={st.errors0}")
    for k in ("begin", "step", "our_turn", "opp_turn"):
        print(f"  {k:14s} {stats(T[k])}")
    if T["steps_per_opp_turn"]:
        print(f"  opp-turn steps  mean={statistics.mean(T['steps_per_opp_turn']):.1f}")
    if T.get("errors"):
        print(f"  ERRORS ({len(T['errors'])}): {T['errors'][:3]}")
    # budget math: one Stage-1 guard = begin + our_turn-remainder + opp_turn per determinization
    if T["begin"] and T["opp_turn"]:
        unit = statistics.mean(T["begin"]) + statistics.mean(T["our_turn"]) + statistics.mean(T["opp_turn"])
        print(f"\n  guard unit (begin+our_turn+opp_turn) ~ {unit:.3f}s; "
              f"K=3 -> {3*unit:.2f}s, K=5 -> {5*unit:.2f}s per guarded decision")


if __name__ == "__main__":
    main()
