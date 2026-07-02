"""exp028 — does our submitted v012 (v_trev deck + v011 revenge policy) already beat
the #1 ladder deck (Debauchery Tea Party's Marnie's Grimmsnarl ex rush, sub 54176312)?

Grimmsnarl piloted with the generic policy (same convention as our other extracted
foreign decks: Archaludon/Dragapult). Usage: uv run python eval_grimmsnarl.py [n]
"""
from __future__ import annotations
import json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
for p in ("exp001_harness", "exp002_baselines", "exp023_revenge"):
    sys.path.insert(0, os.path.join(ROOT, "workspace", p))
from harness import load_engine, run_gauntlet  # noqa
load_engine()
import revenge_policy as P  # noqa

GRIM = json.load(open(os.path.join(os.path.dirname(__file__), "grimmsnarl_deck.json")))
V_TREV = json.load(open(os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    os.environ.setdefault("REVENGE_BONUS", "50")
    ours = P.make_agent(V_TREV)
    grim = P.make_agent(GRIM)  # generic policy pilots the foreign deck
    st = run_gauntlet(ours, grim, n_games=n, swap_sides=True)
    print(f"v012(v_trev+revenge) vs Grimmsnarl-ex(generic pilot): "
          f"wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) n={n} err={st.errors0}")


if __name__ == "__main__":
    main()
