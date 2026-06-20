"""Generic submission builder + validator + smoke test (backs the /build-submit skill).

Takes a base policy .py, a 60-card deck JSON, and an optional patch (.py text
appended after the class to override methods, e.g. exp012's non-ex attack model),
and produces a self-contained submission.tar.gz:  main.py (top-level) + deck.csv +
cg/.  It then validates the tar structure and SMOKE-TESTS the BUILT artifact (the
actual main.py, not the dev policy) against the meta gauntlet with the exp001
harness, reporting winrates + error counts.  Submit only after this passes and the
user approves (per CLAUDE.md); then record to submit/SUBMISSIONS.md + submissions.csv.

Usage:
  uv run python scripts/build_submission.py \
      --deck workspace/exp012_nonex/charmq_deck.json \
      --policy workspace/exp002_baselines/policies/lucario_v2.py \
      --out workspace/exp012_nonex/build_v00X \
      [--patch workspace/exp012_nonex/nonex_policy.py]   # file exposing PATCH_SRC, or a .txt of patch source
      [--smoke 16] [--no-smoke]
"""
from __future__ import annotations
import argparse
import importlib.util
import json
import os
import re
import shutil
import sys
import tarfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CG = os.path.join(ROOT, "data", "sim_sample", "cg")

SAFETY = '''

# ===== crash-safety wrapper =====
def _legal_fallback(select):
    n=len(select.option)
    return [] if n==0 else list(range(min(max(1,select.minCount),n)))
def _valid(sel,select):
    n=len(select.option)
    if not isinstance(sel,list) or any((not isinstance(i,int)) or i<0 or i>=n for i in sel): return False
    if len(set(sel))!=len(sel): return False
    return select.minCount<=len(sel)<=select.maxCount
def agent(obs_dict):
    try: obs=to_observation_class(obs_dict)
    except Exception:
        return list(my_deck) if obs_dict.get("select") is None else [0]
    if obs.select is None: return list(my_deck)
    try:
        sel=_base_agent(obs_dict)
        return sel if _valid(sel,obs.select) else _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
'''


def load_patch(patch_arg):
    if not patch_arg:
        return ""
    if patch_arg.endswith(".py"):
        spec = importlib.util.spec_from_file_location("patchmod", patch_arg)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        return getattr(m, "PATCH_SRC", "")
    return open(patch_arg).read()


def build(deck_path, policy_path, out_dir, patch_arg=None):
    deck = json.load(open(deck_path))
    assert len(deck) == 60, f"deck must be 60 cards, got {len(deck)}"
    patch = load_patch(patch_arg)
    src = open(policy_path).read()
    src = re.sub(r"\bdef agent\(", "def _base_agent(", src)
    os.makedirs(out_dir, exist_ok=True)
    main = src.rstrip() + "\n" + (patch + "\n" if patch else "") + SAFETY
    open(os.path.join(out_dir, "main.py"), "w").write(main)
    open(os.path.join(out_dir, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")
    dst = os.path.join(out_dir, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    tarp = os.path.join(out_dir, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(os.path.join(out_dir, "main.py"), arcname="main.py")
        tar.add(os.path.join(out_dir, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))
    names = set(tarfile.open(tarp).getnames())
    assert {"main.py", "deck.csv", "cg/api.py", "cg/libcg.so"} <= names, f"bad tar: {sorted(names)[:6]}"
    top = sorted(n for n in names if "/" not in n)
    assert top == ["deck.csv", "main.py"], f"main.py/deck.csv must be top-level, got {top}"
    print(f"built {tarp} | top-level={top} | files={len(names)}")
    return tarp


def smoke(tarp, n):
    """Extract the BUILT artifact and run it vs the meta gauntlet via the harness."""
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp001_harness"))
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp002_baselines"))
    sys.path.insert(0, os.path.join(ROOT, "workspace", "exp007_anti_crustle"))
    from harness import load_engine, run_gauntlet
    load_engine()
    import anti_crustle as AC
    import baselines as B
    import tempfile
    d = tempfile.mkdtemp(prefix="smoke_")
    with tarfile.open(tarp) as t:
        t.extractall(d, filter="data")
    spec = importlib.util.spec_from_file_location("built", os.path.join(d, "main.py"))
    m = importlib.util.module_from_spec(spec)
    prev = os.getcwd(); os.chdir(d); spec.loader.exec_module(m); os.chdir(prev)
    opps = [("lucario_v2(ex)", lambda: AC.make_agent(AC.LUCARIO_DECK)),
            ("Crustle", AC.make_crustle_agent),
            ("dragapult", lambda: B.make_policy_agent("dragapult"))]
    print(f"\n=== smoke test (built artifact, n={n}/matchup) ===")
    ok = True
    for name, mk in opps:
        st = run_gauntlet(m.agent, mk(), n_games=n, swap_sides=True)
        print(f"  vs {name:14s} wr={st.winrate0:.3f} ({st.wins0}-{st.wins1}) err0={st.errors0} err1={st.errors1}")
        if st.errors0:
            ok = False
    print("SMOKE OK (0 errors)." if ok else "SMOKE WARNING: built agent raised errors — investigate before submitting.")
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--deck", required=True)
    ap.add_argument("--policy", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--patch", default=None)
    ap.add_argument("--smoke", type=int, default=16)
    ap.add_argument("--no-smoke", action="store_true")
    args = ap.parse_args()
    tarp = build(args.deck, args.policy, args.out, args.patch)
    if not args.no_smoke:
        smoke(tarp, args.smoke)
    print(f"\nNext (after user approval): kaggle competitions submit -c pokemon-tcg-ai-battle "
          f"-f {tarp} -m \"...\"  then record_submission.py + SUBMISSIONS.md")


if __name__ == "__main__":
    main()
