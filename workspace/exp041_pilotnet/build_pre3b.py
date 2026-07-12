"""Build the pre3b candidate as a separate, self-contained artifact for a
paired mirror eval vs v014 (build_v014). Same deck as v014's actual build
(exp027_deckratio/v_trev.json, NOT charmq_deck.json -- confirmed 2-card diff
2026-07-11) so this is a genuine mirror, and same numpy-free npmcts_policy.py
(SEARCH_COUNT=0, the actual ship-path config) so the eval reflects what would
really be submitted.

Usage: uv run python build_pre3b.py
"""
from __future__ import annotations
import json
import os
import shutil

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
CG = os.path.join(ROOT, "data", "sim_sample", "cg")
DECK = os.path.join(ROOT, "workspace", "exp027_deckratio", "v_trev.json")
WEIGHTS_SRC = os.path.join(HERE, "results", "pre3b", "weights_pure.pkl")
OUT = os.path.join(HERE, "build_pre3b")


def build():
    deck = json.load(open(DECK))
    assert len(deck) == 60
    os.makedirs(OUT, exist_ok=True)
    shutil.copy(os.path.join(HERE, "npmcts_policy.py"), os.path.join(OUT, "main.py"))
    open(os.path.join(OUT, "deck.csv"), "w").write("\n".join(map(str, deck)) + "\n")
    dst = os.path.join(OUT, "cg")
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(CG, dst, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
    shutil.copy(WEIGHTS_SRC, os.path.join(dst, "weights_pure.pkl"))
    print(f"built {OUT} (deck={DECK}, weights={WEIGHTS_SRC})")


if __name__ == "__main__":
    build()
