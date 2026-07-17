"""exp054-F -- quantify the Starmie hole (live: koff went 0-3 vs Mega Starmie pilots).

Starmie is the documented sharp counter to wall/LO lines (public_code_sweep_0713)
and sits inside v026's losing mixed_ex3 bucket (3-9, share 14%->20%). Local pool
has NO starmie opponent. Proxy = Star-mine's real extracted 60 (starmie_real.json)
piloted by the generic RVP pilot -- a FLOOR proxy, so read results one-sided:
a low winrate here is decisive (real pilots are stronger); a high one is NOT
clearance.

Measures, n per matchup (default 200, CRN):
  koff (v023/v026/v027 build)  vs starmie_real
  v020 archaludon              vs starmie_real
  pub1034 (v025)               vs starmie_real

Usage: uv run python probe_starmie.py [n]
"""
from __future__ import annotations
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import eval_both_bands as EB  # noqa: E402
from eval_ko_off import make_lo_koforce  # noqa: E402
from load_lo import lo_deck  # noqa: E402
from load_archaludon import make_archaludon_agent  # noqa: E402

sys.path.insert(0, os.path.join(EB.WS, "exp057_pubalakazam"))
from load_pub1034 import make_pub1034_agent  # noqa: E402

RVP = EB.RVP


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    sys.path.insert(0, EB.CRN)
    from harness_crn import run_gauntlet

    starmie = json.load(open(os.path.join(HERE, "starmie_real.json")))
    assert len(starmie) == 60

    ours = [
        ("koff", lambda: make_lo_koforce(lo_deck(), False)),
        ("v020_archaludon", lambda: make_archaludon_agent()),
        ("pub1034", lambda: make_pub1034_agent()),
    ]
    print(f"vs starmie_real (floor RVP pilot), n={n}, CRN\n", flush=True)
    out = {}
    for name, fac in ours:
        t0 = time.time()
        kw = {"crn_seed_base": EB.SEED + abs(hash("starmie_" + name)) % 99991}
        st = run_gauntlet(fac(), RVP.make_agent(starmie), n_games=n, swap_sides=True, **kw)
        out[name] = st.winrate0
        print(f"  {name:16s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}-{st.draws}) "
              f"err=({st.errors0},{st.errors1})  {time.time()-t0:.0f}s", flush=True)
    json.dump(out, open(os.path.join(HERE, f"starmie_probe_n{n}.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
