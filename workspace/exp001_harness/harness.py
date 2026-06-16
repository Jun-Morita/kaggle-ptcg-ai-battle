"""Local match harness for the PTCG AI Battle engine.

Runs two `agent(obs_dict) -> list[int]` callables against each other using the
local `cg` engine (libcg.so / cg.dll), and aggregates win rate, prize (side)
difference, move count, and per-move timing.

The engine keeps a single global battle at a time (Battle.battle_ptr is a class
attribute and lib.GameInitialize() runs once at import), so matches are run
sequentially within one process.

Agent contract (same as the Kaggle submission):
  - First, the agent is asked for its deck: it is called with an observation whose
    `select` is None and must return a list of 60 Card IDs.
  - Then, for every decision it is called with the current observation and must
    return a list of option indices, length in [minCount, maxCount], no
    duplicates, each index in [0, len(option)).
"""
from __future__ import annotations

import os
import sys
import time
import importlib
from dataclasses import dataclass, field
from typing import Callable

# --- locate the cg engine package -------------------------------------------------
# Default: data/sim_sample (downloaded from the Simulation competition sample).
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_CG_DIR = os.path.join(REPO_ROOT, "data", "sim_sample")


def load_engine(cg_dir: str = DEFAULT_CG_DIR):
    """Import and return the cg engine modules (api, game). Idempotent."""
    if cg_dir not in sys.path:
        sys.path.insert(0, cg_dir)
    api = importlib.import_module("cg.api")
    game = importlib.import_module("cg.game")
    return api, game


Agent = Callable[[dict], list]


@dataclass
class MatchResult:
    winner: int            # 0 / 1 / 2(=draw) / -1(=error-no-result)
    reason: int            # RESULT.reason: 1 prize0, 2 deckout, 3 no-active, 4 effect; -1 unknown
    moves: int             # total battle_select calls
    prize_remaining: tuple[int, int]  # prize cards left per player (lower = closer to win)
    error_player: int      # player whose agent raised, else -1
    error: str | None      # exception repr if any
    move_time: tuple[float, float]    # cumulative agent decision seconds per player
    first_player: int      # who went first


def _empty_deck_obs() -> dict:
    return {"select": None, "logs": [], "current": None, "search_begin_input": None}


def _validate_selection(sel, select) -> list:
    """Clamp/validate a selection against the SelectData; raise on hard violations."""
    n = len(select.option)
    if not isinstance(sel, list) or not all(isinstance(i, int) for i in sel):
        raise ValueError(f"agent returned non list[int]: {sel!r}")
    if len(set(sel)) != len(sel):
        raise ValueError(f"duplicate selection: {sel!r}")
    for i in sel:
        if i < 0 or i >= n:
            raise ValueError(f"selection index out of range: {i} (n={n})")
    if not (select.minCount <= len(sel) <= select.maxCount):
        raise ValueError(
            f"selection count {len(sel)} not in [{select.minCount},{select.maxCount}]"
        )
    return sel


def run_match(
    agent0: Agent,
    agent1: Agent,
    cg_dir: str = DEFAULT_CG_DIR,
    max_steps: int = 5000,
) -> MatchResult:
    """Play one match. agent0 is player index 0, agent1 is player index 1."""
    api, game = load_engine(cg_dir)
    to_obs = api.to_observation_class
    agents = [agent0, agent1]

    # 1) collect decks
    decks = []
    for a in agents:
        d = a(_empty_deck_obs())
        decks.append([int(x) for x in d])

    # 2) start battle
    obs, sd = game.battle_start(decks[0], decks[1])
    if game.Battle.battle_ptr in (None, 0):
        return MatchResult(-1, -1, 0, (6, 6), sd.errorPlayer, "battle_start failed",
                           (0.0, 0.0), -1)

    move_time = [0.0, 0.0]
    moves = 0
    first_player = -1
    err_player, err = -1, None

    try:
        for _ in range(max_steps):
            o = to_obs(obs)
            if o.current is not None and first_player == -1:
                first_player = o.current.firstPlayer
            if o.current is not None and o.current.result != -1:
                break
            if o.select is None:
                # no decision pending but no result -> unexpected
                break
            pi = o.current.yourIndex
            t0 = time.perf_counter()
            sel = agents[pi](obs)
            move_time[pi] += time.perf_counter() - t0
            sel = _validate_selection(sel, o.select)
            obs = game.battle_select(sel)
            moves += 1
    except Exception as e:  # the offending agent loses
        o = to_obs(obs)
        err_player = o.current.yourIndex if o.current is not None else -1
        err = repr(e)

    o = to_obs(obs)
    winner, reason = -1, -1
    prize = (6, 6)
    if o.current is not None:
        winner = o.current.result
        prize = (
            len(o.current.players[0].prize),
            len(o.current.players[1].prize),
        )
    for lg in (o.logs or []):
        if lg.type == api.LogType.RESULT:
            reason = lg.reason if lg.reason is not None else reason
    if err_player != -1 and winner == -1:
        winner = 1 - err_player  # erroring agent forfeits

    game.battle_finish()
    return MatchResult(winner, reason, moves, prize, err_player, err,
                       (move_time[0], move_time[1]), first_player)


@dataclass
class GauntletStats:
    n: int = 0
    wins0: int = 0
    wins1: int = 0
    draws: int = 0
    errors0: int = 0
    errors1: int = 0
    total_moves: int = 0
    max_move_time0: float = 0.0
    max_move_time1: float = 0.0
    reasons: dict = field(default_factory=dict)

    @property
    def winrate0(self) -> float:
        return self.wins0 / self.n if self.n else 0.0

    def summary(self) -> str:
        return (
            f"n={self.n} winrate(agent0)={self.winrate0:.3f} "
            f"(w0={self.wins0} w1={self.wins1} draw={self.draws}) "
            f"err0={self.errors0} err1={self.errors1} "
            f"avg_moves={self.total_moves / self.n:.1f} "
            f"max_move_s=({self.max_move_time0:.3f},{self.max_move_time1:.3f}) "
            f"reasons={self.reasons}"
        )


def run_gauntlet(
    agent0: Agent,
    agent1: Agent,
    n_games: int = 20,
    swap_sides: bool = True,
    cg_dir: str = DEFAULT_CG_DIR,
    verbose: bool = False,
) -> GauntletStats:
    """Play n_games. If swap_sides, alternate which agent is player 0 (fair)."""
    st = GauntletStats()
    for g in range(n_games):
        swapped = swap_sides and (g % 2 == 1)
        a0, a1 = (agent1, agent0) if swapped else (agent0, agent1)
        r = run_match(a0, a1, cg_dir=cg_dir)
        # map back to "agent0" perspective
        winner = r.winner
        if swapped and winner in (0, 1):
            winner = 1 - winner
        err_player = r.error_player
        if swapped and err_player in (0, 1):
            err_player = 1 - err_player
        mt0 = r.move_time[1] if swapped else r.move_time[0]
        mt1 = r.move_time[0] if swapped else r.move_time[1]

        st.n += 1
        st.total_moves += r.moves
        st.max_move_time0 = max(st.max_move_time0, mt0)
        st.max_move_time1 = max(st.max_move_time1, mt1)
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
        st.reasons[r.reason] = st.reasons.get(r.reason, 0) + 1
        if verbose:
            print(f"game {g} swapped={swapped} -> winner(agent0persp)={winner} "
                  f"reason={r.reason} moves={r.moves} err={r.error}")
    return st
