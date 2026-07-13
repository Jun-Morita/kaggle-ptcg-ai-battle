# Field intel batch 2 (0713): LB noise, turn-order data, Archaludon counter chatter, engine notes

Fetched via nvidia-kaggle-skill (discussion_ingest/query/read against the
`pokemon-tcg-ai-battle` competition), 2026-07-13. Raw bodies cached in
`data/discussions.db` (sqlite, gitignored) plus a full copy of disc724187 at
`../raw/discussions/724187_pokeforge_postmortem.md` (see that file for the
PokéForge postmortem — most actionable single item this batch, has its own
knowledge file).

## disc712621 — "Leaderboard Scoring Inconsistency" (67 votes)
Poster submitted **two byte-identical agents** twice, for two different decks:
Crustle/Kangaskhan pair converged to 940.7 vs 790.8 (~150pt gap); a
"festival lead" pair converged to 1104.6 vs 687.4 (**~400pt gap**), after
only ~10hrs/few games. Same policy, same deck, wildly different settled LB
score — attributed to early-game opponent-matching variance compounding
during μ600 convergence.
**Implication for us**: a single submission's LB number is not a reliable
strength estimate on its own (we already knew μ600 convergence is noisy;
this quantifies it — up to 400 points for a TRUE null difference). Reinforces
our existing practice of using **local paired evals as the real decision
gate**, not the live LB number, and of not over-reacting to either v019 or
v020's early ladder swings. Does NOT suggest a fix on our side beyond what
we already do; submitting the same agent twice to bracket the range would
cost a real submission slot, not worth it given our slot budget.

## disc723591 — "First or second — which do agents pick?" (11 votes)
Large-N field study (5,333 games, 2026-07-06 top-episode dataset):
- 91.5% of agents choose to go first when they hold the choice.
- First-turn win rate 55.2% vs second 44.8% (**~+10 rating points for going
  first**, field-wide average across all archetypes/agents pooled).
- Because ~91.5% of agents grab first when they win the coin toss, going
  **second is the state you can reliably engineer** (~96% of the time if you
  want it) while going first is largely coin-toss luck (~54%).
**Cross-check against our own result**: exp050 (`IS_FIRST` flip on the v020
Archaludon pilot, which defaults to always taking second) found flipping to
"always go first" was a **clear regression** (mirror n=200, 0.420, z≈-2.3).
This field-wide average (first is generally +10pts) does NOT contradict our
deck-specific finding — it means the *public Archaludon pilot's* choice to
go second is a deliberate, correct, deck-specific adaptation (reactive/wall
playstyle benefits from seeing the opponent's opening first), consistent
with deck⊗pilot inseparability. Good corroborating context for the
Strategy report's discussion of why we did NOT ship the IS_FIRST override.

## disc716207 — "How to Disrupt the Archaludon Meta: Ogerpon" (2 votes)
A participant claims Cornerstone Mask Ogerpon ex's Ability immunity fully
walls Archaludon (which relies on an Ability). But their own hybrid attempts
to make a competitive Ogerpon deck (Ogerpon+Electric, Ogerpon+Archaludon)
both **failed** in their own testing (too slow / inconsistent), and no decklist
or ladder result is given — this is a discovered *mechanic*, not a proven
*winning deck*. **Read as: monitor, not urgent.** We do not have a ready
Cornerstone-Ogerpon-wall decklist to test against (disc721010's Ogerpon
variants are combo decks with only 0-1 copies of Cornerstone Ogerpon, not a
dedicated ability-wall build) — building one from scratch would be
speculative deck design, low ROI given the original poster couldn't make it
work either. Revisit only if `/meta-watch` shows a real Ogerpon-ability-wall
archetype gaining share against v020 specifically.

## disc716045 — official "June 30 Update" (37 votes, Addison Howard/staff)
Engine dataset refresh: added macOS (`libcg.dylib`) and Linux ARM64 binaries;
**no change to `main.py`/`deck.csv`/cg API** — existing submissions
unaffected. Simulator change: games that previously could end in a **draw**
due to the step-limit now instead let the looping player **lose by timeout**
once the step limit is hit (existing settled scores preserved). No action
needed on our side (our submissions don't rely on step-limit draws), but
worth knowing our v014/v019/v020 crash-safety fallback behavior doesn't need
to change — a stuck-loop failure mode is now a timeout loss, not a draw.

## disc711329 — API extension proposal re: search + card-draw abilities (22 votes)
Well-documented black-box finding: within one `SearchId`, a fixed deck order
means repeatedly triggering a draw-ability (e.g. Psychic Draw) from the same
searched state is **deterministic** (same cards every time); only
re-`SearchBegin` with a new determinization reshuffles. This means any
search/lookahead code (including our turn-beam) that imagines drawing cards
via an ability WITHIN a single planned line sees a fixed, already-known future
draw — a clairvoyance bias for decks that chain draw abilities
(Alakazam/Dudunsparce-style). **Does not affect our current shipped chain**
(v014/v019/v020 don't plan through chained draw-ability sequences in a single
search line the way this proposal describes), but is a real caveat to note if
we ever revisit turn-beam/MCTS work on a draw-engine deck — the search would
over-value drawing-ability lines unless we force a re-determinization after
each in-line shuffle.

## Minor / low-priority items skimmed, no action
- disc712657 (matching-process complaint, low info).
- disc715117 (JP, informal account of a top-60 push using Crustle+Cornerstone
  Ogerpon vs big-damage decks; anecdotal, no decklist).
- disc716241 (rare 1/660 Rare Candy evolution-skip engine bug; already
  covered by our crash-safe fallback design, no action).
- disc711644 (RL/PPO/MCTS engineering thread: BC-then-PPO-with-KL-penalty
  hit 25% win vs heuristic baseline w/o search, citing 1-second/turn MCTS
  budget as ~10 rollouts; consistent with our own "search barely helps
  against tuned heuristics" findings, no new actionable idea beyond what
  disc724362 already established).
- disc712011 ("[Dataset+Notebook] 16 Decks That Actually Won Real Pokémon
  Tournaments") — a ready-to-use deck.csv resource, same spirit as
  disc721010; note as a secondary decklist source if we need more local
  eval-pool variety later.
