# exp052 — CRN (Common Random Numbers) feasibility investigation

## Motivation
disc724187 (PokéForge postmortem) and pilkwang's meta-snapshot notebook
(`public_code_sweep_0713.md`) both independently report/flag the same gap:
this engine is unseeded through its exposed API, so paired candidate-vs-
baseline evals can't force identical deals. PokéForge reports CRN (forcing
both compared policies to see the same dealt hands) cuts variance ~4.88x for
near-clone comparisons — if we could do this, our n=200→1000 escalation
pattern (exp047 SEARCH_PRI3, etc.) could plausibly shrink to n≈200 for
equivalent power. User asked to investigate feasibility.

## Finding 1: the exposed ctypes API has NO seed hook (confirmed empirically)
`cg/sim.py`'s `BattleStart(arg)` takes only the concatenated 120-card deck
array (`deck0+deck1`); no seed parameter anywhere in the exported symbol
table (`nm -D libcg.so`: only BattleStart/Select/SearchBegin/Step/End/Release/
GameInitialize/GetBattleData/AgentStart/AllAttack/AllCard/BattleFinish/
VisualizeData — no Seed-anything). Empirical test (same process, same deck
argument, same fixed action sequence, 3 trials): opening hands differed every
trial (see raw output below), confirming the engine's internal RNG is
NOT a function of the input deck order and has no client-controllable seed
via the shipped Python wrapper. This matches disc711329's black-box report
(determinism only within one already-started SearchId; a fresh BattleStart or
re-`SearchBegin` always reshuffles from fresh entropy).

```
trial0 hands: [1147,57,8,1097,1122,1182,1185]
trial1 hands: [1097,190,1227,1182,169,1147,169]
trial2 hands: [169,190,8,8,1121,1152,1182]
```
(same deck, same battle_start args, same `[0]`-selection sequence — three
different hands ⇒ no exposed determinism.)

## Finding 2: we already have the engine SOURCE and a validated native-build path
Unlike a from-scratch reverse-engineering effort (the ambiguous territory
disc711737 asked the host to rule on), the official engine source was later
released (disc717141, `references/raw/ptcg_engine/`, license: "provided
solely for use in this competition... intended use... is for local testing,
verification, and training"). We already built and validated a native
`libcg_local.so` from this source in exp032/exp040 (`g++ -std=c++20 -O2
-fPIC -shared Export.cpp -o libcg_local.so`, confirmed byte-compatible
drop-in replacement for `cg/libcg.so`, used purely for local self-play
throughput — never for the actual submitted agent, which always ships the
untouched official `cg/` folder). This precedent is the key enabler: adding
a seed hook to OUR OWN LOCAL BUILD, for OUR OWN LOCAL EVALUATION ONLY, is
squarely inside the license's stated permitted use — not "exploiting a bug"
or "unintended simulator behavior" (the disc717141 rule we must respect), and
never touches what we submit or how the live ladder resolves matches.

## Finding 3: traced the exact RNG plumbing (grep across the 42 source files)
```
Api.h:29    std::random_device rd;                       // ApiBattleStart's local rd
Api.h:78    data->game.rng = std::mt19937(seq);           // ApiAgentStart path (search)
Api.h:88-90 config.seed = std::random_device()();  data->game.rng = std::mt19937(config.seed);
Game.h:61   std::mt19937 rng;                             // the "seedable" engine, per-Game instance
Game.h:82-84 config.seed == 0 -> rd();  rng = mt19937(config.seed);   // Game::init() already DOES support a nonzero external seed!
CardMove.h:263   std::shuffle(ps.deck.begin(), ps.deck.end(), std::random_device());     // DECK SHUFFLE — bypasses game.rng entirely
EffectInstant.h:585  std::shuffle(state.targetList.begin(), state.targetList.end(), std::random_device());  // secondary shuffle (target-list effects)
SelectProc.h:56,94  (config.deviceRand ? std::random_device()() : state.game->rng())    // coin flips — respects game.rng IF deviceRand==false
```
`ApiBattleStart` (`Api.h:23-77`) currently: sets `config.seed = rd()` (fresh
entropy every call), `config.deviceRand = true` (forces coin flips to bypass
`game.rng` and use raw `random_device` regardless of `config.seed`), calls
`data->init(config)` (which WOULD seed `game.rng` from `config.seed` per
`Game::init`), then **immediately re-seeds `game.rng` a second time** with a
fresh `std::seed_seq{rd(),rd(),rd(),rd()}` — throwing away the config.seed
path entirely. So today, NOTHING about a real battle's outcome is
seed-controllable, on three independent axes: deck shuffle (always raw
device), coin flips (forced raw device via `deviceRand=true`), and
`game.rng` itself (redundantly re-randomized right after being seeded).

## Conclusion: CRN is feasible, cheaply, and within license
**Correction after reading full context (not just the first grep hit):** the
engine already gates EVERY randomness source behind `state.game->config.
deviceRand` — deck shuffle (`CardMove.h:262-266`), the secondary target-list
shuffle (`EffectInstant.h:583-588`), and both coin-flip resolutions
(`SelectProc.h:56,94`) all branch cleanly between `std::random_device()`
(when `deviceRand==true`) and the seeded `state.game->rng` (when false).
`EffectProc.h:697` and `Search.h:207` already use `game->rng` unconditionally.
**So the ENTIRE fix is contained to one function, `Api.h`'s `ApiBattleStart`**,
which today (a) always draws a fresh `rd()` seed, (b) hardcodes
`config.deviceRand = true` (forcing coin flips through the raw device
regardless of seed), and (c) immediately re-seeds `game.rng` a second time
right after `data->init(config)`, discarding the config.seed path entirely.

## Implementation (done, 2026-07-13)
1. Copied the licensed source to `workspace/exp052_crn/engine_src/` (raw copy
   under `references/raw/ptcg_engine/` left untouched, per license terms).
2. Patched only `Api.h::ApiBattleStart`: reads `CG_CRN_SEED` from the
   environment (nonzero -> deterministic mode: `config.seed` = that value,
   `config.deviceRand = false`, skip the redundant re-seed so `game.rng`
   keeps the config.seed-derived state from `data->init()`); unset/zero ->
   byte-identical original behavior (fresh `rd()` seed, `deviceRand = true`,
   the original re-seed line still runs). Added `#include <cstdlib>` for
   `getenv`/`strtoul`.
3. Rebuilt with the exact proven exp032/040 command:
   `g++ -std=c++20 -O2 -fPIC -shared Export.cpp -o libcg_crn.so` (clean, 0
   warnings). Copied into `workspace/exp052_crn/cg/` alongside the official
   Python wrapper files (`sim.py`/`game.py`/`api.py`/`utils.py`/`__init__.py`,
   unmodified, copied from `data/sim_sample/cg/`) as `libcg.so`.
4. **Verified determinism empirically** (`arch_own_deck.json`, 3 trials each):
   `CG_CRN_SEED=12345` x3 -> **byte-identical opening-hand sequences all 3
   times**; `CG_CRN_SEED=99999` -> different hands from the 12345 runs;
   `CG_CRN_SEED` unset -> different hands each trial (original behavior
   preserved). Pass/fail bar cleared.
5. Built `harness_crn.py` (CRN-aware copy of `exp001_harness`'s
   `run_match`/`run_gauntlet`, pointed at this patched local `cg` package):
   `run_gauntlet(..., crn_seed_base=None|int)` — when given, swap-pair games
   `g` and `g+1` (the `swap_sides` mechanism our real ship-gates already use)
   share `CG_CRN_SEED = crn_seed_base + g//2`, so both orderings of a swap
   pair see the identical dealt hands/coin-flips, isolating "which policy
   played which seat" from "which pair got the luckier deal" — this is the
   correct CRN unit for OUR specific gate shape (head-to-head paired eval
   with seat-swapping), as opposed to naively sharing one seed across the
   whole n-game run.
6. `measure_variance.py`: re-ran our OWN real exp047 gate (SEARCH_PRI3
   candidate `exp047_pri_tobench/build_sp3` vs baseline
   `exp035_turnbeam/build_v014`) as repeated small batches, with vs without
   CRN, comparing between-repeat std-dev of the winrate estimate — the direct
   analogue of PokéForge's reported "~4.88x variance reduction for near-clone
   comparisons" claim, measured on our own gate/data rather than taken on
   faith.

## Result: measured variance reduction (6 repeats x n=30, real exp047 gate)
```
no-CRN: mean=0.4611 sd=0.0989  values=[0.6, 0.4, 0.367, 0.6, 0.4, 0.4]      (394s)
CRN:    mean=0.4889 sd=0.0458  values=[0.5, 0.567, 0.5, 0.433, 0.433, 0.5]  (348s)
variance ratio (no-CRN/CRN) = 4.66x   |   std-dev ratio = 2.16x
```
**Confirmed on our own data**: CRN cut the between-repeat variance of the
paired winrate estimate by 4.66x — remarkably close to PokéForge's reported
~4.88x for near-clone comparisons (this candidate/baseline pair is a small
single-select-context patch, i.e. a near-clone in their sense). Practical
implication: our established n=200→600→1000 escalation ladder (exp047,
exp050, etc.) could plausibly compress to roughly n/4.66 games for equivalent
statistical power under CRN — e.g. an n≈220 CRN run for the same power as our
current n=1000 non-CRN gate. Not yet adopted for a real ship decision (this
was a methodology-validation run, not a gate); next step would be swapping
`eval_paired.py`'s engine import to this patched local one and re-running a
live candidate through the CRN path before trusting it as the deciding gate.

## Follow-up work not yet done
- Swap a REAL in-flight candidate gate over to `harness_crn.py` and use CRN
  as the actual deciding evidence (this session only validated the technique
  on an already-decided pair, sp3 vs v014).
- Double-check CRN behavior doesn't change qua win-rate MEAN (only variance)
  on a larger confirming run — the two means above (0.461 vs 0.489) differ by
  less than 1 game out of 30 and are well within each other's noise, so no
  mean-shift artifact is evident, but this was not a dedicated test for that.
- Decide whether to route ALL future paired gates through the CRN-patched
  local engine by default, or keep it as an optional accelerant.

## Compliance note
All of the above touches only a LOCAL derivative build living entirely under
`workspace/exp052_crn/` — the official `cg/` package used by
`scripts/build_submission.py` for anything we actually submit is never
modified or replaced. This matches the license's stated permitted use
("Use it only to build and test your competition entries... local testing,
verification, and training") and the exact precedent already set by
exp032/040's native-build performance work.

## Scope / effort actually spent
~1 hour: source copy, single-function patch, rebuild, empirical determinism
check, CRN-aware harness, and the variance-measurement script — smaller than
the original 1-2h estimate once the full `deviceRand` gating was understood
(only 1 file needed changes, not 3).
