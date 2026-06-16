"""Extract rule-based agent policies + decks from the saved notebooks.

Reads the official sample notebooks and the public "V2" notebook from
references/raw/, and writes one importable policy module per agent into
`policies/` plus a `policies/decks.json` with each agent's 60-card deck.

The extracted policy code is competition/3rd-party material, so `policies/`
is gitignored; re-run this script to regenerate it.

Each policy module defines `agent(obs_dict) -> list[int]`. We DO NOT rely on
the modules' own deck.csv reading: the harness wrapper (see baselines.py)
injects the deck on the initial (select is None) call.
"""
from __future__ import annotations

import json
import os
import re

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OFFICIAL = os.path.join(REPO, "references/raw/official_notebooks")
PUBLIC = os.path.join(REPO, "references/raw/public_notebooks")
OUT = os.path.join(os.path.dirname(__file__), "policies")

# name -> (notebook path, deck source: "decklist" | "deck_literal")
NOTEBOOKS = {
    "dragapult":   (f"{OFFICIAL}/a-sample-rule-based-agent-dragapult-ex-deck.ipynb", "decklist"),
    "iono":        (f"{OFFICIAL}/a-sample-rule-based-agent-iono-s-deck.ipynb", "decklist"),
    "abomasnow":   (f"{OFFICIAL}/a-sample-rule-based-agent-mega-abomasnow-ex-deck.ipynb", "decklist"),
    "lucario_v1":  (f"{OFFICIAL}/a-sample-rule-based-agent-mega-lucario-ex-deck.ipynb", "decklist"),
    "lucario_v2":  (f"{PUBLIC}/validated-rule-based-agent-matchup-tests.ipynb", "deck_literal"),
}


def code_cells(nb: dict) -> list[str]:
    return ["".join(c["source"]) for c in nb["cells"] if c["cell_type"] == "code"]


def get_main_py(nb: dict) -> str:
    for src in code_cells(nb):
        if src.lstrip().startswith("%%writefile main.py"):
            # drop the magic line
            return src.split("\n", 1)[1]
    raise ValueError("no %%writefile main.py cell found")


def deck_from_decklist(main_py: str) -> list[int]:
    """Parse `NAME = ID  # xN` lines in the Decklist section."""
    deck: list[int] = []
    in_block = False
    for line in main_py.split("\n"):
        if "# Decklist" in line:
            in_block = True
            continue
        if in_block:
            m = re.match(r"\s*\w+\s*=\s*(\d+)\s*#\s*[×xX]\s*(\d+)", line)
            if m:
                cid, n = int(m.group(1)), int(m.group(2))
                deck.extend([cid] * n)
            elif line.strip() and not line.lstrip().startswith("#") and "=" not in line:
                break  # left the decklist block
    return deck


def deck_from_literal(nb: dict) -> list[int]:
    """Find a `DECK = [ ... ]` literal in any code cell."""
    for src in code_cells(nb):
        m = re.search(r"DECK\s*=\s*\[(.*?)\]", src, re.DOTALL)
        if m:
            nums = re.findall(r"\d+", m.group(1))
            return [int(x) for x in nums]
    raise ValueError("no DECK literal found")


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    open(os.path.join(OUT, "__init__.py"), "w").close()
    decks: dict[str, list[int]] = {}

    for name, (path, deck_src) in NOTEBOOKS.items():
        nb = json.load(open(path))
        main_py = get_main_py(nb)
        with open(os.path.join(OUT, f"{name}.py"), "w") as f:
            f.write(main_py)

        deck = deck_from_decklist(main_py) if deck_src == "decklist" else deck_from_literal(nb)
        if len(deck) != 60:
            raise ValueError(f"{name}: deck has {len(deck)} cards, expected 60")
        decks[name] = deck
        print(f"{name:12s} deck=60 ok  ({len(set(deck))} unique)  policy={name}.py")

    with open(os.path.join(OUT, "decks.json"), "w") as f:
        json.dump(decks, f, indent=2)
    print(f"\nwrote {len(decks)} policies + decks.json to {OUT}")


if __name__ == "__main__":
    main()
