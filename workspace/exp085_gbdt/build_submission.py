"""Package the GBDT ranker as a submission tar: main.py + deck.csv + cg/.

Three sandbox facts drive the shape of this, all paid for by earlier failures:

  __file__ is undefined. Kaggle runs the agent with exec() on main.py's SOURCE, so
  module-level code that touches __file__ dies before agent() exists, and a
  try/except cannot catch it (v015 through v015-fix3, four ERROR submissions).
  BASE is resolved by probing /kaggle_simulations/agent and cwd instead.

  numpy is absent. Nothing here imports it: the scorer walks Python lists.

  cg/ is proven to arrive. The model pickle rides inside cg/ for the same reason
  the transformer's weights did -- libcg.so must be delivered for any agent to
  run at all, so nothing in that directory can be dropped by a whitelist.

main.py is assembled by concatenating feats.py and gbdt_policy.py with their local
imports stripped, rather than shipping them as modules, so there is exactly one
top-level file and no import-path assumptions.

Usage: uv run python build_submission.py [--tag v3] [--n 40]
"""
from __future__ import annotations
import importlib.util, json, os, re, shutil, sys, tarfile, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(WS, ".."))
CG = os.path.join(ROOT, "data", "sim_sample", "cg")
DECK = os.path.join(WS, "exp080_bc", "grimmsnarl_deck.json")


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


HEADER = '''"""PTCG agent: gradient-boosted option ranker (exp085). Pure stdlib, no search."""
from __future__ import annotations
import os, pickle, sys
from collections import Counter

# Kaggle exec()s this source; __file__ may be undefined. Probe instead.
if "__file__" in globals():
    BASE = os.path.dirname(os.path.abspath(globals()["__file__"]))
else:
    BASE = next((c for c in ("/kaggle_simulations/agent", os.getcwd())
                 if os.path.isfile(os.path.join(c, "cg", "gbdt.pkl"))), os.getcwd())
if BASE not in sys.path:
    sys.path.insert(0, BASE)

from cg.api import AreaType, OptionType, all_attack, all_card_data, to_observation_class
'''

DRIVER = '''

_MODEL_PATH = os.path.join(BASE, "cg", "gbdt.pkl")
_DECK = [int(x) for x in open(os.path.join(BASE, "deck.csv")).read().split() if x.strip()]
try:
    _PURE = load_pure(_MODEL_PATH)
    _AGENT = make_agent_from_pure(_PURE, _DECK)
except Exception:
    _AGENT = None


def agent(obs):
    """Never raises: a malformed answer costs the game by rules-violation."""
    try:
        if _AGENT is not None:
            return _AGENT(obs)
    except Exception:
        pass
    try:
        sel = obs.get("select") if isinstance(obs, dict) else None
        if sel is None:
            return list(_DECK)
        n = len(sel.get("option") or [])
        lo = int(sel.get("minCount", 0) or 0)
        return list(range(min(n, max(lo, 1))))
    except Exception:
        return [0]
'''


def strip_module(path, drop_prefixes):
    """Source of a local module minus its dev-only import block."""
    out = []
    for line in open(path).read().splitlines():
        if any(line.startswith(p) for p in drop_prefixes):
            continue
        out.append(line)
    return "\n".join(out)


def main():
    tag = arg("--tag", "v3")
    n = int(arg("--n", "40"))
    out = os.path.join(HERE, f"build_{tag}")
    pure = os.path.join(HERE, "results", f"gbdt_pure_{tag}.pkl")
    assert os.path.exists(pure), pure
    deck = json.load(open(DECK))
    assert len(deck) == 60, len(deck)
    os.makedirs(out, exist_ok=True)

    drop = ('from __future__', 'import sys, os', 'from collections import Counter',
            'HERE =', 'WS =', 'for p in (', '    if os.path.join(WS',
            '        sys.path.insert', 'from harness import', 'load_engine()',
            'from cg.api import', 'import os\n', 'import pickle',
            'from cg.api import to_observation_class', '    import feats',
            '    from cg.api import')
    body = [HEADER,
            "\n# ---- feats.py ----\n",
            strip_module(os.path.join(HERE, "feats.py"), drop),
            "\n# ---- gbdt_policy.py ----\n",
            strip_module(os.path.join(HERE, "gbdt_policy.py"), drop),
            DRIVER]
    src = "\n".join(body)
    # gbdt_policy.make_agent takes a path and imports feats; inline, both are local
    src = src.replace("def make_agent(pure_path, deck):",
                      "def make_agent_from_pure(pure, deck):")
    src = src.replace("    pure = load_pure(pure_path)\n", "")
    # feats ships inlined, so the module-qualified call has no module to resolve.
    # Left unfixed this raises NameError on EVERY decision, the except returns a
    # legal-but-arbitrary move, and the agent loses every game with zero errors.
    src = src.replace("    option_rows = _feats.option_rows\n", "")
    open(os.path.join(out, "main.py"), "w").write(src)
    open(os.path.join(out, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")

    dst = os.path.join(out, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    shutil.copy(pure, os.path.join(dst, "gbdt.pkl"))

    tarp = os.path.join(out, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(os.path.join(out, "main.py"), arcname="main.py")
        tar.add(os.path.join(out, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))
    names = set(tarfile.open(tarp).getnames())
    assert {"main.py", "deck.csv", "cg/gbdt.pkl", "cg/api.py", "cg/libcg.so"} <= names
    print(f"built {tarp} | top-level={sorted(x for x in names if '/' not in x)} | "
          f"files={len(names)} | size={os.path.getsize(tarp)/1e6:.1f}MB")
    return tarp, n


def smoke(tarp, n):
    """Run the EXTRACTED artifact, not the dev modules: the only way to catch a
    packaging error (missing file, bad path, stripped import) before Kaggle does."""
    for p in ("exp001_harness", "exp002_baselines", "exp007_anti_crustle"):
        sys.path.insert(0, os.path.join(WS, p))
    from harness import load_engine, run_gauntlet
    load_engine()
    import anti_crustle as AC
    import baselines as B
    d = tempfile.mkdtemp(prefix="smoke_gbdt_")
    with tarfile.open(tarp) as t:
        t.extractall(d, filter="data")
    spec = importlib.util.spec_from_file_location("built", os.path.join(d, "main.py"))
    m = importlib.util.module_from_spec(spec)
    prev = os.getcwd(); os.chdir(d)
    t0 = time.time()
    src = open(os.path.join(d, "main.py")).read()
    # exec the SOURCE the way Kaggle's loader does -- no __file__ defined
    g = {"__name__": "built"}
    exec(compile(src, "main.py", "exec"), g)
    os.chdir(prev)
    print(f"module load (exec, no __file__) took {time.time()-t0:.1f}s")
    assert g.get("_AGENT") is not None, "model failed to load inside the artifact"

    opps = [("lucario_v2(ex)", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("Crustle", AC.make_crustle_agent),
            ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    print(f"\n=== smoke (built artifact, n={n}/matchup) ===")
    ok = True
    for name, mk in opps:
        st = run_gauntlet(g["agent"], mk(), n_games=n, swap_sides=True)
        print(f"  vs {name:14s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) "
              f"err0={st.errors0} err1={st.errors1}")
        if st.errors0:
            ok = False
    st = getattr(g["_AGENT"], "state", {})
    fb, dec = st.get("fallbacks", -1), st.get("decisions", -1)
    print(f"  model-answered decisions {dec}, silent fallbacks {fb}")
    if fb != 0:
        ok = False
        print("  FALLBACKS > 0: the packaged agent is not using its model")
    print("SMOKE", "OK" if ok else "FAILED")
    return ok


if __name__ == "__main__":
    tarp, n = main()
    smoke(tarp, n)
