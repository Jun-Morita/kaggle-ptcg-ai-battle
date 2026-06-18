"""Build v003: anti-Crustle patched lucario_v2 policy + crash-safety.

main.py = patched policy (ex/megaEx deals 0 to ex-immune targets -> the policy
auto-pivots to the non-ex Hariyama line that one-shots Crustle) wrapped with the
v001 crash-safety pattern. Same Lucario deck. Beats Crustle control 0.10->0.60
locally while holding mirror/Dragapult.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import tarfile

from patch_policy import patched_source

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXP2_POLICIES = os.path.join(REPO, "workspace", "exp002_baselines", "policies")
CG_DIR = os.path.join(REPO, "data", "sim_sample", "cg")
BUILD = os.path.join(HERE, "build")

SAFETY = '''

# ===== crash-safety wrapper (v003, same as v001) =====
def _legal_fallback(select):
    n = len(select.option)
    if n == 0:
        return []
    return list(range(min(max(1, select.minCount), n)))


def _valid(sel, select):
    n = len(select.option)
    if not isinstance(sel, list) or any((not isinstance(i, int)) or i < 0 or i >= n for i in sel):
        return False
    if len(set(sel)) != len(sel):
        return False
    return select.minCount <= len(sel) <= select.maxCount


def agent(obs_dict):
    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        if obs_dict.get("select") is None:
            return list(my_deck)
        return [0]
    if obs.select is None:
        return list(my_deck)
    try:
        sel = _base_agent(obs_dict)
        return sel if _valid(sel, obs.select) else _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
'''


def build():
    src = patched_source()
    src = re.sub(r"\bdef agent\(", "def _base_agent(", src)
    os.makedirs(BUILD, exist_ok=True)
    main_py = os.path.join(BUILD, "main.py")
    open(main_py, "w").write(src.rstrip() + "\n" + SAFETY)

    deck = json.load(open(os.path.join(EXP2_POLICIES, "decks.json")))["lucario_v2"]
    assert len(deck) == 60
    open(os.path.join(BUILD, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")

    dst = os.path.join(BUILD, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG_DIR, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

    tarp = os.path.join(BUILD, "submission.tar.gz")
    with tarfile.open(tarp, "w:gz") as tar:
        tar.add(main_py, arcname="main.py")
        tar.add(os.path.join(BUILD, "deck.csv"), arcname="deck.csv")
        for root, _d, files in os.walk(dst):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                tar.add(full, arcname=os.path.join("cg", os.path.relpath(full, dst)))
    names = tarfile.open(tarp).getnames()
    assert {"main.py", "deck.csv", "cg/api.py", "cg/libcg.so"} <= set(names), names
    print("built", tarp)
    print("top-level:", sorted(n for n in names if "/" not in n), "files:", len(names))


if __name__ == "__main__":
    build()
