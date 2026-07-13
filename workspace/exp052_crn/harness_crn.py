"""exp052 -- CRN-capable copy of exp001_harness's run_match/run_gauntlet.

Loads OUR patched local engine (workspace/exp052_crn/cg, libcg_crn.so — same
official source, only ApiBattleStart's seed handling touched, see
engine_src/Api.h) instead of the official data/sim_sample engine, so this
must NEVER be used to validate a real submission build (use the official
engine for that, as scripts/build_submission.py already does) -- it exists
solely to measure whether Common Random Numbers reduce variance in our own
local paired-eval gates.

Design: within a swap_sides gauntlet, pair game g (even) with its swap
partner g+1 (odd) on the SAME CG_CRN_SEED -- both members of a swap pair then
see the identical dealt hands/coin-flips, isolating "which policy played
which seat" from "which pair got the better/worse random deal", while
different pairs still get different seeds (so deal diversity across the
whole n-game run is preserved). Set crn_seed_base=None to reproduce the
original (unseeded) behavior exactly for comparison.
"""
from __future__ import annotations

import importlib
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

HERE = os.path.dirname(os.path.abspath(__file__))
CG_DIR = HERE  # workspace/exp052_crn/cg/ is importable as `cg` from here

Agent = Callable[[dict], list]


def load_engine(cg_dir: str = CG_DIR):
    if cg_dir not in sys.path:
        sys.path.insert(0, cg_dir)
    api = importlib.import_module("cg.api")
    game = importlib.import_module("cg.game")
    return api, game


def _empty_deck_obs() -> dict:
    return {"select": None, "logs": [], "current": None, "search_begin_input": None}


def _validate_selection(sel, select) -> list:
    n = len(select.option)
    if not isinstance(sel, list) or not all(isinstance(i, int) for i in sel):
        raise ValueError(f"agent returned non list[int]: {sel!r}")
    if len(set(sel)) != len(sel):
        raise ValueError(f"duplicate selection: {sel!r}")
    for i in sel:
        if i < 0 or i >= n:
            raise ValueError(f"selection index out of range: {i} (n={n})")
    if not (select.minCount <= len(sel) <= select.maxCount):
        raise ValueError(f"selection count {len(sel)} not in [{select.minCount},{select.maxCount}]")
    return sel


@dataclass
class MatchResult:
    winner: int
    moves: int
    error_player: int
    error: str | None


def run_match(agent0: Agent, agent1: Agent, cg_dir: str = CG_DIR, max_steps: int = 5000,
              crn_seed: int | None = None) -> MatchResult:
    api, game = load_engine(cg_dir)
    to_obs = api.to_observation_class
    agents = [agent0, agent1]

    decks = []
    for a in agents:
        d = a(_empty_deck_obs())
        decks.append([int(x) for x in d])

    if crn_seed is not None:
        os.environ["CG_CRN_SEED"] = str(crn_seed)
    else:
        os.environ.pop("CG_CRN_SEED", None)

    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return MatchResult(-1, 0, sd.errorPlayer, "battle_start failed")

    moves = 0
    err_player, err = -1, None
    try:
        for _ in range(max_steps):
            o = to_obs(obs)
            if o.current is not None and o.current.result != -1:
                break
            if o.select is None:
                break
            pi = o.current.yourIndex
            sel = agents[pi](obs)
            sel = _validate_selection(sel, o.select)
            obs = game.battle_select(sel)
            moves += 1
    except Exception as e:
        o = to_obs(obs)
        err_player = o.current.yourIndex if o.current is not None else -1
        err = repr(e)

    o = to_obs(obs)
    winner = -1
    if o.current is not None:
        winner = o.current.result
    if err_player != -1 and winner == -1:
        winner = 1 - err_player

    game.battle_finish()
    return MatchResult(winner, moves, err_player, err)


@dataclass
class GauntletStats:
    n: int = 0
    wins0: int = 0
    wins1: int = 0
    draws: int = 0
    errors0: int = 0
    errors1: int = 0

    @property
    def winrate0(self) -> float:
        return self.wins0 / self.n if self.n else 0.0


def run_gauntlet(agent0: Agent, agent1: Agent, n_games: int = 20, swap_sides: bool = True,
                  cg_dir: str = CG_DIR, crn_seed_base: int | None = None) -> GauntletStats:
    """crn_seed_base=None -> original unseeded behavior. Otherwise, games g and
    g+1 (a swap pair) share CG_CRN_SEED = crn_seed_base + (g // 2)."""
    st = GauntletStats()
    for g in range(n_games):
        swapped = swap_sides and (g % 2 == 1)
        a0, a1 = (agent1, agent0) if swapped else (agent0, agent1)
        seed = None if crn_seed_base is None else (crn_seed_base + (g // 2))
        r = run_match(a0, a1, cg_dir=cg_dir, crn_seed=seed)
        winner = r.winner
        if swapped and winner in (0, 1):
            winner = 1 - winner
        err_player = r.error_player
        if swapped and err_player in (0, 1):
            err_player = 1 - err_player

        st.n += 1
        if winner == 0:
            st.wins0 += 1
        elif winner == 1:
            st.wins1 += 1
        else:
            st.draws += 1
        if err_player == 0:
            st.errors0 += 1
        elif err_player == 1:
            st.errors1 += 1
    return st
