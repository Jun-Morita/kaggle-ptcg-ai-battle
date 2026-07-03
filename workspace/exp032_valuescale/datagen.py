"""exp032 — mass self-play data generation on the NATIVE-compiled engine, to retest
exp014's value-calibration go/no-go at 100-1000x the data.

exp014 (319 real games): mid-game value AUC 0.585-0.637 ~ prize_diff alone; rich
features memorized (train 0.999). Open confound: DATA SIZE. The engine source drop
makes big data feasible. Here: rule-based self-play across a diverse deck pool,
one feature row per (turn, pov) at MAIN decisions, exp014's 17 strategy scalars
(imported from value_calib for comparability) + label = that pov won.

Usage: uv run python datagen.py <worker_id> <n_games>   -> data/rows_w<id>.csv
"""
from __future__ import annotations
import csv, json, os, random, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle", "exp012_nonex",
          "exp013_router", "exp014_rl_offline", "exp020_deckinnov", "exp022_megastarmie",
          "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))

CG_NATIVE = os.path.join(HERE, "native")
import harness
harness.load_engine(CG_NATIVE)
from harness import run_match  # noqa
from value_calib import featurize, FEATS as FEATURES  # noqa
import anti_crustle as AC  # noqa
import revenge_policy as P  # noqa

os.environ.setdefault("REVENGE_BONUS", "50")


def load_json(*parts):
    return json.load(open(os.path.join(ROOT, *parts)))


def deck_pool():
    v_trev = load_json("workspace", "exp027_deckratio", "v_trev.json")
    ch = load_json("workspace", "exp012_nonex", "charmq_deck.json")
    ch = ch.get("charmq") if isinstance(ch, dict) else ch
    pool = {"v_trev": v_trev, "charmq": ch, "lucario": list(AC.LUCARIO_DECK),
            "crustle": list(AC.CRUSTLE_DECK)}
    for name, parts in [("grimmsnarl", ("workspace", "exp028_debauchery", "grimmsnarl_deck.json"))]:
        try:
            pool[name] = load_json(*parts)
        except Exception:
            pass
    # OOD fix (2nd iteration): wall/alt archetypes from extracted 3rd-party decks
    for name, parts in [("archaludon", ("workspace", "exp025_unkoable", "archaludon_opp", "deck.csv")),
                        ("lo_tusk", ("workspace", "exp030_lomill", "lo_agent", "deck.csv")),
                        ("dragapult", ("references", "raw", "public_notebooks", "dragapult", "deck.csv"))]:
        try:
            path = os.path.join(ROOT, *parts)
            pool[name] = [int(x) for x in open(path).read().split() if x.strip().isdigit()]
        except Exception:
            pass
    try:
        import load_dragapult as LD  # noqa
        pool["dragapult"] = list(LD.DECK)
    except Exception:
        pass
    return pool


def make_recorder(deck, rows, pov, game_ref):
    base = P.make_agent(deck)
    seen_turns = set()

    def agent(obs_dict):
        try:
            cur = obs_dict.get("current")
            if cur is not None:
                t = cur.get("turn", 0)
                if t not in seen_turns:
                    f = featurize(obs_dict, cur.get("yourIndex", pov))
                    if f is not None:
                        rows.append([game_ref[0], pov, t] + f)
                        seen_turns.add(t)
        except Exception:
            pass
        return base(obs_dict)

    def reset():
        seen_turns.clear()
    agent.reset = reset
    return agent


def main():
    wid = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n_games = int(sys.argv[2]) if len(sys.argv) > 2 else 1000
    rng = random.Random(1000 + wid)
    pool = deck_pool()
    names = sorted(pool)
    os.makedirs(os.path.join(HERE, os.environ.get("OUT_DIR", "data")), exist_ok=True)
    out = os.path.join(HERE, os.environ.get("OUT_DIR", "data"), f"rows_w{wid}.csv")
    fout = open(out, "a", newline="")
    w = csv.writer(fout)
    if fout.tell() == 0:
        w.writerow(["game", "pov", "turn"] + FEATURES + ["label", "deck_me", "deck_opp", "game_len"])
    t0 = time.time()
    done = 0
    for g in range(n_games):
        d0n, d1n = rng.choice(names), rng.choice(names)
        rows0, rows1 = [], []
        gid = f"w{wid}g{g}"
        a0 = make_recorder(pool[d0n], rows0, 0, [gid])
        a1 = make_recorder(pool[d1n], rows1, 1, [gid])
        try:
            r = run_match(a0, a1, cg_dir=CG_NATIVE)
        except Exception:
            continue
        if r.winner not in (0, 1):
            continue
        glen = max([x[2] for x in rows0 + rows1] or [0])
        for rows, pov in ((rows0, 0), (rows1, 1)):
            lab = 1 if r.winner == pov else 0
            for row in rows:
                w.writerow(row + [lab, d0n if pov == 0 else d1n,
                                  d1n if pov == 0 else d0n, glen])
        done += 1
        if done % 200 == 0:
            fout.flush()
            dt = time.time() - t0
            print(f"w{wid}: {done}/{n_games} games, {dt:.0f}s ({dt/done:.3f}s/game)", flush=True)
    fout.close()
    print(f"w{wid} DONE: {done} games -> {out}", flush=True)


if __name__ == "__main__":
    main()
