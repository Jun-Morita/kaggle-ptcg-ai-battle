"""Build a crash-safe submission bundle for the Simulation track.

Takes our strongest baseline policy (exp002 lucario_v2) and hardens it with the
crash-safety pattern proven by the public LB-860 notebook: the public agent()
becomes _base_agent(), and a new agent() wraps it so that ANY exception or
structurally-illegal selection falls back to a guaranteed-legal move. On the
ladder an exception = a lost game (validation plays you against a mirror), so
never crashing is worth a lot of rating — and stability is also weighted in the
Strategy rubric.

Outputs into build/: main.py (hardened), deck.csv, cg/ (copied from local
engine), submission.tar.gz with main.py at the TOP level.

Usage: uv run python build_submission.py [policy_name]   # default lucario_v2
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tarfile

HERE = os.path.dirname(__file__)
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EXP2_POLICIES = os.path.join(REPO, "workspace", "exp002_baselines", "policies")
CG_DIR = os.path.join(REPO, "data", "sim_sample", "cg")
BUILD = os.path.join(HERE, "build")

SAFETY_WRAPPER = '''

# ===== crash-safety wrapper (exp005, pattern from public LB-860 notebook) =====
def _legal_fallback(select):
    """A structurally-legal selection: the first minCount distinct option indices."""
    n = len(select.option)
    if n == 0:
        return []
    k = min(max(1, select.minCount), n)
    return list(range(k))


def _valid(sel, select):
    n = len(select.option)
    if not isinstance(sel, list) or any((not isinstance(i, int)) or i < 0 or i >= n for i in sel):
        return False
    if len(set(sel)) != len(sel):
        return False
    return select.minCount <= len(sel) <= select.maxCount


def agent(obs_dict):
    """Crash-safe entry point. Never throws, never returns an illegal selection."""
    try:
        obs = to_observation_class(obs_dict)
    except Exception:
        # Cannot parse: if this looks like deck selection, return the deck.
        if obs_dict.get("select") is None:
            return list(my_deck)
        return [0]

    if obs.select is None:
        return list(my_deck)

    try:
        sel = _base_agent(obs_dict)
        if _valid(sel, obs.select):
            return sel
        return _legal_fallback(obs.select)
    except Exception:
        return _legal_fallback(obs.select)
'''


def build(policy_name: str = "lucario_v2") -> str:
    src_path = os.path.join(EXP2_POLICIES, f"{policy_name}.py")
    if not os.path.exists(src_path):
        raise FileNotFoundError(
            f"{src_path} not found. Run exp002 extract_policies.py first."
        )
    with open(src_path) as f:
        src = f.read()

    # rename the public agent() to _base_agent() (only the top-level def + return-less refs)
    if "def agent(" not in src:
        raise ValueError("policy has no agent() to wrap")
    src = re.sub(r"\bdef agent\(", "def _base_agent(", src)

    os.makedirs(BUILD, exist_ok=True)
    main_py = os.path.join(BUILD, "main.py")
    with open(main_py, "w") as f:
        f.write(src.rstrip() + "\n" + SAFETY_WRAPPER)

    # deck.csv from the policy's deck (exp002 decks.json)
    import json
    with open(os.path.join(EXP2_POLICIES, "decks.json")) as f:
        deck = json.load(f)[policy_name]
    assert len(deck) == 60, f"deck must be 60 cards, got {len(deck)}"
    with open(os.path.join(BUILD, "deck.csv"), "w") as f:
        f.write("\n".join(str(c) for c in deck) + "\n")

    # cg/ engine (exclude pycache/binaries-of-our-making)
    dst_cg = os.path.join(BUILD, "cg")
    if os.path.exists(dst_cg):
        shutil.rmtree(dst_cg)
    shutil.copytree(CG_DIR, dst_cg,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))

    # package: main.py at TOP level
    tar_path = os.path.join(BUILD, "submission.tar.gz")
    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(main_py, arcname="main.py")
        tar.add(os.path.join(BUILD, "deck.csv"), arcname="deck.csv")
        for root, _dirs, files in os.walk(dst_cg):
            for fn in files:
                if fn.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(root, fn)
                arc = os.path.join("cg", os.path.relpath(full, dst_cg))
                tar.add(full, arcname=arc)

    # verify structure
    with tarfile.open(tar_path, "r:gz") as tar:
        names = tar.getnames()
    required = {"main.py", "deck.csv", "cg/api.py", "cg/libcg.so"}
    missing = required - set(names)
    if missing:
        raise RuntimeError(f"archive missing: {sorted(missing)}")
    if any("__pycache__" in n or n.endswith((".pyc", ".pyo")) for n in names):
        raise RuntimeError("archive contains cache files")

    print(f"policy={policy_name}")
    print(f"built {tar_path}")
    print(f"top-level: {sorted(n for n in names if '/' not in n)}")
    print(f"files in archive: {len(names)}")
    return tar_path


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "lucario_v2"
    build(name)
