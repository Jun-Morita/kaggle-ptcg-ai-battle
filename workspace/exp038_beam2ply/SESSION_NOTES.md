# exp038 — depth-2 alpha-beta search + archetype-matched opponent model

## Hypothesis
Extend v014's depth-1 turn-beam to depth-2 (our turn + opponent's modeled reply),
using an archetype-matched opponent policy (not our own deck's policy) to rank the
opponent's moves, a richer eval (+threat-removed term), probe-based move ordering,
and alpha-beta pruning. Same "verified-override" philosophy as v013/v014: only fire
when the search's candidate beats the base policy's own action.

## Result: NOT shippable yet. Crustle recovered from catastrophic to a real gain;
other matchups remain catastrophic for a different, unresolved reason.

## Bugs found and fixed (in `search_lib.py` / `beam2_policy.py` / `revenge_policy.py`)

All found by systematic isolation (toggling K, alpha-beta, eval_fn, opp_mode, depth)
plus direct tracing of fired decisions (`B2_DEBUG=1`) once toggling stopped moving
the needle. Each is real and worth keeping regardless of ship decision:

1. **Apples-to-oranges root comparison**: candidate and base actions were scored via
   SEPARATE `api.search_begin()` calls. Fixed: one shared root, `must_include`
   forces both to be scored from the same determinization.
2. **`_rev` cross-branch contamination**: `roll` (the search's own move-ranking
   policy instance) is called across many hypothetical branches spanning a turn
   boundary at depth=2, corrupting its revenge-window turn-tracker. Fixed with
   snapshot/restore around every search call (`revenge_policy.py`'s `agent._mod`
   now exposes the module dict for this).
3. **`_rev` never advances across REAL decisions**: the snapshot/restore fix above
   captured the snapshot BEFORE `roll`'s own first real call for the current
   decision (since `roll` is only ever invoked from inside `search_best_action`,
   never on the bare real obs). Every restore then reset `roll` back to
   pre-this-turn state forever, freezing its revenge-window detection at the
   initial default. Fixed by bootstrapping one real `roll(obs_dict)` call before
   capturing the snapshot.
4. **Shared `node_budget` depleted sequentially across root candidates**: whichever
   root candidate's subtree was scored first (or got lucky) explored deeper/more
   completely; later candidates got truncated subtrees that fall back to an
   optimistic eval_fn on an unresolved position. Fixed: equal, independent budget
   share per root candidate (`per_cand_budget = node_budget // len(cand0)`), and
   `must_include` items evaluated FIRST so the baseline action is never starved.
5. **Epsilon-margin qualification**: `cand_v > base_v` on a continuous, noisy,
   single-determinization eval tuple fires on bare epsilon differences — unlike
   v013/v014's chunky margin (e.g. `dmg >= base_dmg + 30`). Added
   `_meaningfully_better()`: requires a real prize-margin swing (>=1), or (tied)
   a real threat-margin swing (>=0.5), or (tied) a real HP swing (>=30).
   Empirically did NOT reduce the fire rate much (~34-36% either way) — most
   fires are confidently wrong, not noisy, pointing at #6.
6. **Horizon effect (the big one for crustle)**: traced actual fired decisions via
   `B2_DEBUG=1` and found a recurring pattern — the search overrides a real
   ATTACK with END (skip the attack). The depth=2 lookahead sees the opponent's
   counter-KO after we attack, but not that skipping the attack only DELAYS that
   same loss past its horizon — it looks like "avoided the loss" when it's really
   "deferred it, and forfeited our own attack." This is a textbook minimax horizon
   effect, and especially damaging here because trading prizes via KOs IS this
   game's win condition, not something to avoid. Added `_is_horizon_dodge()`:
   reject any override where base is ATTACK and the candidate is END/RETREAT.

## Measured impact (crustle, n=30, paired swap_sides)
- Before any fix (buggy n=100 chunked run, now stale/invalid): ~0.05-0.10.
- After bugs 1-5 (must-first ordering, equal budget, _rev bootstrap, margin): ~0.23-0.27
  (noisy small-n bounced 0.27-0.47, but a larger n=30 run confirmed ~0.23-0.27 — the
  higher one-off reads were noise).
- After bug 6 (horizon-dodge guard): **0.70 (21-9, n=30)**, then **0.75 (15-5, n=20)**
  in the field battery. Real, large, reproducible gain. Still below the pure
  base-policy-alone baseline (0.9, no search at all) but a completely different
  regime from "catastrophic."

## Still broken (not yet resolved)
- Field battery (n=20): ex_lucario 0.35, dragapult 0.10, archaludon 0.10,
  mirror_chq 0.10, crustle 0.75. Only crustle recovered.
- Traced dragapult's fired decisions and found the SAME family of problem but in
  shapes the current guard doesn't cover: `ATTACK -> PLAY(Boss's Orders)` (not
  END, so not caught), and `END -> PLAY(Boss's Orders)` with `base_v` showing a
  near-certain-loss value (-999998, i.e. `cur.result` resolved to a loss inside
  the simulated continuation) that looks like a phantom worst-case driven by a
  single random hidden-hand sample (K=1) rather than the opponent's true hand —
  plausible especially against burst/combo archetypes (Dragapult, Archaludon)
  where "if they happen to have card X" swings the simulated outcome hugely.
- Confirmed opp_mode="policy" (no minimax, single archetype-matched reply, no
  worst-case probing) does NOT fix dragapult either (wr=0.067, n=15) — so the
  problem is not specifically minimax-amplified pessimism, it's deeper (most
  likely the single-K hidden-hand sampling itself, or further un-guarded
  horizon-effect shapes).
- **Stale artifacts**: `b2_*.log`, `chunks_b2/`, `B2_DONE`, `run_b2.sh`'s
  `chunks_b2/*` markers all predate every fix above and must be discarded /
  re-run before drawing any conclusion from them.

## Follow-up round: exclusion-based hidden-info sampling (2026-07-05, later)
User request: track played/seen cards to make the search more efficient, and use
the official simulator to narrow candidate options further.

Implemented: `opponent_model.py`'s `OpponentModel` now exposes `.deck` — the
detected archetype's EXACT 60-card decklist (Dragapult/Archaludon/LO read from
the real `deck.csv` files their own loaders already use; Crustle/Lucario reuse
`anti_crustle.CRUSTLE_DECK`/`LUCARIO_DECK`; Grimmsnarl reuses its JSON deck).
`beam2_policy.py`'s `det()` now maintains a cumulative, monotonic per-card-id
"seen from the opponent" counter across the WHOLE game (element-wise max against
each new observation), and when the archetype's deck is known, samples the
opponent's hidden deck/prize/hand via clean EXCLUSION (known deck minus what
we've actually seen, no replacement) instead of the old heuristic (sample WITH
replacement from cards we've happened to see) — which could invent impossible
duplicate copies of a 1-of, i.e. a phantom combo the opponent doesn't actually
have. Falls back to the old heuristic only when the archetype/deck is unknown or
the accounting doesn't add up (defensive). "Narrow candidate options via the
simulator" turned out not to need separate code: `select.option` at each
opponent-turn node is already generated by the real engine from whatever hidden
hand we supply, so once the hidden hand is accurate, the option list it exposes
is already the correctly-narrowed one.

**Result**: crustle unaffected (0.73, n=30 — matches the pre-change 0.70-0.75,
confirming no regression from the more principled sampling). **dragapult
unchanged** (0.067, n=15) — so K=1 phantom-hand sampling was NOT the (or not the
only) driver of dragapult's failure. Traced fired decisions again (`B2_DEBUG=1`)
post-fix: no more `ATTACK->END` (guarded), but new shapes of the same underlying
problem remain — `PLAY->END` (skip playing a bench Pokemon entirely) and
`ATTACK->PLAY` (skip attacking in favor of a trainer card), both showing the same
"shallow horizon prefers passivity" signature. Tested depth=3 (one more ply, so
the true cost of delaying would fall inside the window) at reduced branch/probe
caps to stay tractable: dragapult **0.067 -> 0.200** (n=15) — a real but small
and still nowhere near viable improvement, at much higher cost. Kept the
exclusion-sampling fix (correct and free of regression) and a `B2_DEPTH` env
knob for future testing; did NOT change the shipped `CFG.depth` default (still 2).

**Conclusion**: the remaining dragapult/archaludon/mirror failure is NOT
primarily a hidden-info-accuracy problem — it's the horizon effect showing up in
more shapes than the one guard (`ATTACK->END/RETREAT`) covers, and it resists
being fixed by going one ply deeper alone (helps a little, not enough, at high
cost). A general fix would need either a broader class of horizon-dodge
detection (harder: `PLAY`/`ATTACK` alternatives are often legitimately better,
so a blanket rule risks false rejects) or accepting the depth=2 search only where
proven (crustle-style walls) via archetype dispatch, falling back to v014's
depth=1 elsewhere.

## Next steps (not yet executed, optional)
- Broaden the horizon-dodge guard beyond `ATTACK->END/RETREAT` to cover
  `ATTACK->PLAY`-shaped dodges (harder: PLAY is a legitimate real action too, so
  a blanket ban isn't safe — needs a sharper signal, e.g. "did the candidate's
  branch also decline to ever throw a punch within the horizon"). Deferred: the
  qualifying condition isn't clean yet and a wrong guard risks false rejects.
- Raise K substantially specifically for depth=2 opponent-turn modeling (costly),
  or restrict depth=2/opponent-model search to archetypes where it's demonstrated
  to help (crustle-style walls) via the existing archetype dispatch, falling back
  to plain v014 depth=1 turn-beam elsewhere.
- Re-run a clean n=100/200 chunked verification only once the non-crustle
  matchups are addressed (or once a crustle-only gated deployment is decided).

## Follow-up round 2 (2026-07-05, later still): two more real bugs + a re-calibration

Fixed two more genuine bugs, found while trying to verify the round-1 gains:
1. **Cross-matchup/cross-game state leakage**: `eval_b2.py` builds ONE `cand =
   B2.make_agent(deck)` and `harness.run_gauntlet` reuses that SAME callable
   across all `n_games` of a matchup, and the field battery reuses it across
   ALL 5 different opponent archetypes in one process. The round-1
   `seen_opp` counter (exclusion-sampling bug fix) never reset, so by the 3rd or
   4th matchup it was subtracting a COMPLETELY DIFFERENT opponent's cards from
   the CURRENT opponent's known deck, and even within one matchup it slowly
   exhausted the pool over many games of the same opponent. Fixed: detect a new
   game via `obs.current.turn` regressing (strictly non-decreasing within one
   game) and hard-reset `seen_opp` + force `OpponentModel` to re-detect/rebuild.
2. **Crash on `minCount=0` single-select decisions** ("you may attach 0
   energy"-style optional choices): `_policy_sel`/`_clamp` correctly returns an
   EMPTY selection for these (valid, since minCount=0 permits declining), but
   `_walk_single_ply`'s cheap single-child path did `pref[0]`, raising
   `IndexError` on genuinely empty `pref`. Surfaced as ~9-20% of all decisions
   erroring specifically against Archaludon's real 3rd-party pilot. Fixed: step
   with `pref` itself (0 or 1 elements, already correctly clamped) instead of
   assuming `pref[0]` exists.

**Result after both fixes, full field battery (n=20)**: ex_lucario 0.35
(baseline 0.75), dragapult 0.10 (baseline 0.15), archaludon 0.10 (baseline
0.10), mirror_chq 0.15 (baseline 0.55), crustle 0.40 (baseline 0.765-0.90).

**Re-calibration — this is a more sober picture than round 1 suggested.**
Round 1 compared crustle's recovering numbers (0.70-0.75) against its OWN
earlier catastrophic reads (0.05-0.33) and called it a win. But crustle's
ACTUAL historical no-search baseline is 0.765-0.90 (v012/v013/v014 all land
there) — so even the "success" case has not been shown to beat the baseline;
it has only been shown to recover from "badly broken" to "roughly at or
somewhat below baseline." Isolated re-tests of crustle alone bounced between
0.40 and 0.80 across several n=15-30 runs (high variance, small n), so the
crustle number specifically needs a much larger, cleaner verification (n=50+)
before any claim of "beats baseline" can be trusted — it has NOT been
established yet.

**Honest current state**: after 2 rounds of debugging (7 real, confirmed bugs
fixed: apples-to-oranges root comparison, `_rev` cross-branch contamination,
`_rev` never-advances, asymmetric root-candidate budget, epsilon-margin
qualification, the ATTACK->END horizon-effect guard, opponent-model exclusion
sampling, opponent-model cross-branch state contamination, cross-game/
cross-matchup `seen_opp` leakage, and a `minCount=0` crash), **no matchup has
been robustly shown to beat its historical no-search baseline**. depth=3/4
experiments (see below) made things worse, not better. The bugs fixed were all
real and are worth keeping (this module is much more correct now than when
this experiment started), but the experiment has not yet produced a positive
result to ship.

## Follow-up round 3 (2026-07-05, later still): broaden horizon guard, then a real n=40 verification

Kept finding the SAME horizon-effect signature in new shapes when re-tracing
ex_lucario/mirror_chq: `PLAY->END`, `ABILITY->END`, and critically
`ATTACK->PLAY` (base_v showed losing 3 whole prizes for attacking vs 0 for
playing a bench card instead — an implausible swing). Broadened
`_is_horizon_dodge()`: reject ANY override whose candidate is END (not just
after ATTACK), and reject ANY override away from a real ATTACK to a
non-ATTACK candidate (not just to END/RETREAT) — the base policy already has
real domain logic for whether/what to attack, and every traced override away
from a real attack has looked spurious.

Also tried tightening `_meaningfully_better`'s margins further (threat 0.5->1.0,
hp 30->60): fired rate barely moved (~30% either way) and results bounced
within noise — reverted to the original margins.

**Decisive result — a real n=40/matchup chunked run** (2×20-game chunks,
`run_b2.sh`, survives interruption), the largest sample this experiment has had:

| matchup | beam2 (n=40) | baseline (v012, no search) |
|---|---:|---:|
| ex_lucario | 0.500 | 0.75-0.77 |
| dragapult | 0.100 | 0.15-0.155 |
| archaludon | 0.050 | 0.10-0.175 |
| mirror_chq | 0.250 | 0.55-0.585 |
| crustle | 0.675 | 0.765-0.90 |
| **total** | **1.575** | **2.45** (v012) / 2.58 (v013) / 2.67 (v014) |

This is the first sample size in this experiment large enough to trust (n=20
per matchup bounced all over: crustle alone read 0.40, 0.55, 0.60, 0.65, 0.70,
0.73, 0.75, 0.80 across different small-n runs during this session). At n=40,
the picture is unambiguous: **every matchup is at or below its no-search
baseline**, and the total (1.575) is far below even the pre-any-of-our-fixes
v012 baseline (2.45). Crustle, the one matchup that looked like a clear win
during round 1's small-n testing, is now merely close to (slightly below) its
own baseline.

## Conclusion (2026-07-05, final for this session)
11 real, confirmed bugs were found and fixed across three debugging rounds
(apples-to-oranges root comparison, `_rev` cross-branch contamination, `_rev`
never-advances, asymmetric root-candidate budget, epsilon-margin qualification,
horizon-effect guards (3 shapes), opponent-model exclusion sampling,
opponent-model cross-branch state contamination, cross-game/cross-matchup
`seen_opp` leakage, and a `minCount=0` crash) — all genuine and worth keeping
as engineering lessons (documented above). Depth=3/4 experiments made results
worse, not better. Despite all of this, **the underlying design (depth=2
alpha-beta search + archetype-matched opponent modeling) does not beat the
existing verified-override designs (v013 doom-veto, v014 turn-beam) at a
sample size large enough to trust.** This should be recorded as an honest
negative, in the same family as exp033 (value-guided override) and exp036
(GA over pilot constants): a plausible-looking idea, implemented carefully,
that does not survive rigorous measurement.

## Ship decision: DO NOT SHIP. v014 remains the shipped baseline and should not
be replaced by this experiment's design. If resumed in the future, the
starting point should be the n=40 numbers above (not the earlier small-n reads
that looked promising), and the core open question is WHY a 2-ply search with
a real, archetype-matched opponent model still underperforms a 1-ply
turn-beam (v014) — something more structural than the 11 bugs fixed here is
likely still at play (candidates: the horizon effect exists in forms beyond
the 3 guarded shapes; a single K=1 hidden-info sample is fundamentally too
noisy for a verified-override design at this depth; or minimax opponent
modeling itself, even bug-free, is simply the wrong shape of pessimism for
this game).
