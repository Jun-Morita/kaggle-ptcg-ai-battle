"""exp061 step 0 -- can a floor pilot REPRODUCE the ability-chip kill?

Live: koff lost the Grimmsnarl/Froslass family repeatedly (exp054-G: board wipe
with ZERO opponent attacks -- ability damage bypasses Safeguard/NZ). Local marnie
proxy loses to koff 0.83-0.89, i.e. the floor pilot does NOT execute the chip.

Step-0 question (pre-registered): with gagacrow's REAL list (grimm_froslass.json),
does the floor RVP pilot (a) use abilities at all, (b) pull koff's winrate clearly
below the 0.83-0.89 marnie-proxy reference?

Verdict rules:
  - koff wr <= 0.70 AND opponent ability usage > 0  -> chip PARTIALLY reproduced,
    exp061 (tech gate / 2nd deck / RL opponent pool) becomes measurable.
  - koff wr ~ 0.83-0.89 or ability usage ~ 0 -> floor pilot cannot express the
    archetype; reproduction needs a dedicated chip pilot (bigger project, park it).

Usage: uv run python probe_chip.py [n] [--crn]
"""
from __future__ import annotations
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, os.path.join(WS, "exp054_upperband"))
import eval_both_bands as EB  # noqa: E402  (engine + RVP + paths)
from eval_ko_off import make_lo_koforce  # noqa: E402
from load_lo import lo_deck  # noqa: E402

RVP = EB.RVP
TYPE_NAMES = {7: "play", 8: "attach", 9: "evolve", 10: "t10", 11: "t11",
              12: "retreat", 13: "attack", 14: "t14"}


def make_instrumented(deck, counts):
    base = RVP.make_agent(deck)

    def agent(obs):
        act = base(obs)
        sel = obs.get("select")
        if sel is not None and sel.get("context") == 0:
            opts = sel.get("option", [])
            if opts and len(opts) != 60 and isinstance(act, list):
                for c in act:
                    if isinstance(c, int) and c < len(opts):
                        t = opts[c].get("type")
                        counts[TYPE_NAMES.get(t, f"t{t}")] += 1
                # also record which types were AVAILABLE
                for o in opts:
                    t = o.get("type")
                    counts[f"avail_{TYPE_NAMES.get(t, f't{t}')}"] += 0  # touch keys lazily
    # simpler: count availability explicitly
        return act
    return agent


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 200
    sys.path.insert(0, EB.CRN)
    from harness_crn import run_gauntlet

    chip = json.load(open(os.path.join(HERE, "grimm_froslass.json")))
    assert len(chip) == 60
    counts = Counter()
    t0 = time.time()
    st = run_gauntlet(make_lo_koforce(lo_deck(), False), make_instrumented(chip, counts),
                      n_games=n, swap_sides=True,
                      crn_seed_base=EB.SEED + 4242)
    print(f"koff vs grimm_froslass(floor RVP): wr={st.winrate0:.3f} "
          f"({st.wins0}-{st.wins1}-{st.draws}) err=({st.errors0},{st.errors1})  "
          f"{time.time()-t0:.0f}s   [marnie-proxy ref 0.83-0.89]")
    print("opponent chosen option types:", dict(counts))


if __name__ == "__main__":
    main()
