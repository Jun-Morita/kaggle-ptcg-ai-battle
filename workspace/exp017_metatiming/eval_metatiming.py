"""exp017: is the Dragapult (spread) counter well-timed for the CURRENT field?

2026-06-22 meta-watch (sub 53898216) field shares -> our local opponents:
  non_ex 34% (charmq, piloted by v008)   lucario_ex+ex_beatdown 28% (lucario_v2)
  Alakazam(mixed_ex1) 20%                crustle 7% (crustle deck via generic policy = v004)
  abomasnow(mixed_ex4) 7%                iono(mixed_ex3) 5%
Compute each test agent's WEIGHTED expected field win-rate. Compare the Dragapult
spread counter vs our current v008 (charmq non-ex).

Usage: uv run python eval_metatiming.py [n_per_matchup]
"""
from __future__ import annotations
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
for p in (os.path.join(ROOT, "workspace", "exp001_harness"),
          os.path.join(ROOT, "workspace", "exp002_baselines"),
          os.path.join(ROOT, "workspace", "exp013_router"),
          os.path.join(ROOT, "workspace", "exp016_pubnb"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

from harness import run_gauntlet  # noqa: E402
import baselines as B  # noqa: E402
import router_policy as R  # noqa: E402
from load_alakazam import make_alakazam_agent  # noqa: E402

CRUSTLE = json.load(open(os.path.join(ROOT, "workspace", "exp007_anti_crustle", "crustle_deck.json")))
CHARMQ = R.charmq_deck()

# field opponents as fresh-agent factories + share weights (from meta-watch 0622)
OPPONENTS = {
    "non_ex(charmq)":   (lambda: R.make_agent(CHARMQ),               0.34),
    "lucario_ex":       (lambda: B.make_policy_agent("lucario_v2"),  0.28),
    "Alakazam":         (lambda: make_alakazam_agent(),              0.20),
    "crustle(v004)":    (lambda: R.make_agent(CRUSTLE),              0.07),
    "abomasnow":        (lambda: B.make_policy_agent("abomasnow"),   0.07),
    "iono":             (lambda: B.make_policy_agent("iono"),        0.05),
}

TEST_AGENTS = {
    "Dragapult(spread)": lambda: B.make_policy_agent("dragapult"),
    "v008(charmq non-ex)": lambda: R.make_agent(CHARMQ),
}


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 24
    wsum = sum(w for _, w in OPPONENTS.values())
    print(f"field weights (normalized over {wsum:.2f}):")
    for name, (_, w) in OPPONENTS.items():
        print(f"  {name:18s} {w/wsum:.3f}")
    print()
    for tname, tfac in TEST_AGENTS.items():
        exp = 0.0
        print(f"=== {tname} ===")
        for oname, (ofac, w) in OPPONENTS.items():
            st = run_gauntlet(tfac(), ofac(), n_games=n, swap_sides=True)
            wr = st.winrate0
            exp += (w / wsum) * wr
            print(f"  vs {oname:18s} wr={wr:.3f}  (w0={st.wins0} w1={st.wins1}) err={st.errors0}/{st.errors1}")
        print(f"  --> WEIGHTED expected field win-rate: {exp:.3f}\n")


if __name__ == "__main__":
    main()
