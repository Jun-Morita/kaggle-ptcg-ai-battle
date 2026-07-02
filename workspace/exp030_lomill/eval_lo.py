"""exp030 — threat check: our submitted v012 (v_trev + revenge) vs the public
Great Tusk LO agent (score 1083.6). Usage: uv run python eval_lo.py [n]"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp023_revenge", "exp030_lomill"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import revenge_policy as P  # noqa
from load_lo import make_lo_agent  # noqa

V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.environ.setdefault("REVENGE_BONUS", "50")
    st = run_gauntlet(P.make_agent(V_TREV), make_lo_agent(), n_games=n, swap_sides=True)
    print(f"v012 vs GreatTusk-LO: wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) err={st.errors0}")


if __name__ == "__main__":
    main()
