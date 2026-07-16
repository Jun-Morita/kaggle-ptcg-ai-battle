"""exp058 stage 2 -- confirm top screen arms at n=300 (CRN, vs stock)."""
from __future__ import annotations
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tune_mirror import make_pub, SEED  # noqa: E402
from harness_crn import run_gauntlet  # noqa: E402

ARMS = [
    ("boss_killx2", {"boss_kill": 4524}),
    ("mine_counterx2", {"mine_counter": 36990}),
    ("boss+mine_x2", {"boss_kill": 4524, "mine_counter": 36990}),
]

def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    out = {}
    for label, ov in ARMS:
        st = run_gauntlet(make_pub(ov), make_pub(None), n_games=n, swap_sides=True,
                          crn_seed_base=SEED + 777)
        out[label] = st.winrate0
        print(f"{label:16} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1})", flush=True)
    json.dump(out, open(os.path.join(HERE, f"mirror_confirm_n{n}.json"), "w"), indent=1)

if __name__ == "__main__":
    main()
