# Reading the Meta, Not Just the Board
### Opponent Modeling and Data-Driven Meta-Tracking in a Partially-Observed Trading Card Game

*Strategy Writeup — Pokémon TCG AI Battle Challenge*

---

## Abstract

Most agents in this competition try to play the *board* well. We argue the
decisive skill is playing the *meta* well. We contribute three results. **(1)
Opponent modeling, not raw search, determines an agent's strength.** A controlled
experiment shows that grounding the search's hidden-information model in a *real*
believed decklist beats a placeholder model **5× (0.417 vs 0.083** win-rate vs the
rule-based pool). **(2) The ladder is a *rotating* rock-paper-scissors** —
ex-beatdown → anti-ex wall → single-prize non-ex → … — and we built a
replay-analysis pipeline that *measures* the rotation and ships a counter for each
phase, reaching LB ~1120 (top-quartile) with a deck we reconstructed from a
top-ranker's replays. **(3) We empirically closed both "smarter" levers.** Using
319 real top-ranker games, a learned value net cannot read the mid-game
(AUC 0.64 < 0.70); and an *exact* near-terminal search still fails to beat the
tuned heuristic. At mid compute, **a meta-reading rule-based agent with good
piloting is the achievable ceiling** — and we show *why* with data.

## 1. Game and Challenge

The cabt engine simulates Pokémon TCG: partially observed (opponent's hand, deck
order, and prizes are hidden), stochastic (coin flips, draws), and with a
*variable, heterogeneous* action space (an agent returns option indices, not a
fixed action head — so vanilla fixed-head RL is a poor fit). Submissions are
agents (`main.py` + `deck.csv` + engine), ranked by a live TrueSkill ladder
(μ₀=600, win/loss only, latest-2 submissions scored, ~10 min/game). Because
ranking is *live and relative*, the field you face changes daily — the central
difficulty is not a fixed opponent but a *moving distribution*.

## 2. Methodology

We built a local match harness (side-swapped to cancel first-player bias,
illegal moves = forfeit, ~10 ms/game) and scored agents by average win-rate over
a fixed opponent pool. Crucially, we built a **replay-analysis pipeline**: pull
our own and top players' ladder episodes, reconstruct every decklist (the only
60-card action), label opponents by archetype, and compute matchup win-rates and
loss causes. This pipeline is our meta-sensing organ; every strategic decision
below is grounded in it, not in intuition. *(Figure 1: matchup matrix; Figure 2:
strength ranking.)*

## 3. Central Finding: Opponent Modeling Determines the Value of Search

Naïve search is *harmful* here. One-ply lookahead (0.21–0.27), cold-start
AlphaZero (0.03), and behavior-cloning + MCTS (0.23) all score **below** the
rule-based baseline (0.68). Diagnosis: the engine's determinization fills the
hidden opponent with **placeholders** (Snorlax/energy), so the search optimizes
against a *fake passive opponent* and picks moves that backfire against real,
strong play.

Our fix is **belief-grounded determinization**: sample the opponent's hidden
cards from a *real believed decklist*, so the in-search opponent plays a realistic
strategy. A controlled experiment (identical search, only the determinization
swapped) is decisive: belief **0.417** vs placeholder **0.083** against the
rule-based pool — a **5× gain** — and the in-search opponent now makes ~50 moves
per game instead of 33 (it actually plays). With belief, search even **beats
Dragapult 0.667** (above plain rule-based 0.60). *The value of search is bounded
by the quality of your opponent model, not by search depth.* This is the
originality core of our work and, to our knowledge, unverified in public
notebooks (where the search API is often called with a wrong signature, i.e.
effectively disabled). *(Figure 3: belief vs placeholder; in-search opponent
activity.)*

## 4. The Rotating Three-Way Meta — and How We Track It

The meta is **not static; it rotates**, exactly like real Pokémon TCG. Our
replay pipeline measured a full turn of the cycle:

- **06-18 — anti-ex wall control** dominates: Crustle's "Safeguard" prevents *all*
  damage from the opponent's Pokémon-ex, hard-countering the all-ex sample decks
  (which is what most public agents run).
- **06-20 — ex-beatdown returns** (57% of our field): the wall fades, Mega Lucario
  ex aggro resurges.
- **late 06-20 — single-prize non-ex becomes the apex**: decks of 1-prize
  attackers (Hop's Trevenant) that we measured beating *both* ex-beatdown (0.69)
  *and* the wall (0.70).

The mechanism is real prize-trade theory. A **single-prize** attacker wins the
prize race against multi-prize ex (when the opponent KOs our attacker they take
**1** prize; when we KO their ex we take **2–3**), and non-ex damage **bypasses
the ex-only Safeguard**. So non-ex > {ex, wall}; ex > wall; wall > ex — a genuine
rock-paper-scissors that also *converges* as players pile into the apex.

We **tracked the rotation and shipped a counter for each phase**:

| Phase | Counter we submitted | Result |
|---|---|---|
| Wall dominant | v003 anti-Crustle (auto-pivot to non-ex Hariyama when ex damage is negated) | **LB 1123**, our first top-quartile |
| ex resurges | v004 Crustle wall (piloted by the generic policy) | climbs from μ600 |
| non-ex apex | v006/v008 non-ex apex, **deck reconstructed from a top-ranker's replays** | vs ex **0.80**, vs wall **0.77**, LB ~1120 |

*(Figure 4: meta-rotation timeline; Figure 5: three-way diagram + prize-liability.)*

## 5. Deck (Deck Score)

Our deck is a **single-prize, non-ex "Hop's Trevenant" beatdown**, reconstructed
exactly from a top-ranker's replays and then *out-piloted*. Concept: never give
the opponent a good prize trade, and bypass damage-prevention walls. Key cards:

- **Hop's Trevenant** ("Horrifying Revenge", 1 energy, boostable) — the 1-prize
  main attacker.
- **Dunsparce → Dudunsparce** ("Run Away Draw") — the consistency engine that
  keeps an attack coming every turn (tempo).
- **Hop's Choice Band (+30 / −1 cost)** and **Postwick stadium (+30)** — the
  damage tools that push attacks into KO thresholds on ex.
- **Hop's Snorlax** ("Extra Helpings", +30 to Hop's attacks while benched).
- **Boss's Orders** — gust a benched threat or an engine piece for the close.

Every attacker is single-prize, so the deck is structurally favored in the prize
race and immune to ex-only Safeguard. *(Figure 6: deck list + key-card synergy.)*

## 6. Piloting: A Generic Policy + Targeted Patches

A deck is only as good as its pilot — **deck and policy are tightly coupled**. We
confirmed this sharply: copying the #1 player's *list* and running it under our
stock policy scored just **0.167** vs ex (it bricks — the policy can't drive its
tutor engine). The fix is *not* a full rewrite (our full-rewrite control policy
lost to the generic one). Instead, a **generic rule-based policy + small,
targeted patches**: we inject the non-ex attack model (Choice Band / Postwick /
Extra Helpings, correct Weakness type) and a **search-target priority** so tutors
fetch the engine pieces in the right order. This single change lifts consistency
across the board — vs ex 0.71→**0.80**, vs wall 0.63→**0.77** — and wins the
mirror over the un-patched policy (0.56). The lesson: *inject one module, don't
rewrite* — it preserves the tuned behavior while adding deck awareness. *(Figure
7: Boss's-Orders usage before/after plan formation; mirror smart-vs-generic.)*

## 7. Stability and Operations (the Model "robustness" axis)

Two unglamorous factors dominate ladder rating. **Crash-safety**: a wrapper that
turns any exception or illegal move into a legal fallback — public agents gain an
estimated +64 rating from this alone, and it guarantees we never forfeit.
**Speed**: 0.02–0.16 s/move keeps us far inside the timeout (our search-heavy
PIMC variant, at ~30 s/move, was too slow to ship). Operationally we run a weekly
loop: `meta-watch` (detect rotation) → `extract-deck` (clone the new apex) →
`build-submit` (build, smoke-test the real artifact, submit). *(Figure 8:
stability vs LB; rating convergence.)*

## 8. We Closed Both "Smarter" Levers — With Data

A credible strategy report must say what *didn't* work. We rigorously tested the
two obvious paths beyond a heuristic and show both are empirically bounded at our
resource level.

**Learning (RL).** Self-play belief-MCTS fine-tuning is an honest negative,
verified four ways: Phase-2 policy collapse; a 0.31 mirror ceiling; and a
*decisive* probe — win-rate *drops* as search grows (0.31→0.19→0.13 at
24→48→96 sims), proving the learned **value net is the bottleneck** (good value ⇒
more search helps). We then tested the one principled unblocker — *calibrate value
on real outcomes* — on the best possible data: **319 top-ranker games** with real
win/loss labels, episode-level holdout. The value net **cannot read the mid-game**
(phase-0.4–0.6 AUC **0.637** with strategy-lens scalars, **0.585** even with
card-level hand+board embeddings — both ≈ "prize-difference alone", 0.688). Only
the *late* game is predictable (AUC **0.80**). This mechanistically explains
"more search = worse": the value is uninformative exactly where search must act,
so MCTS amplifies noise. Mid-game outcome variance here appears *game-intrinsic*
(luck/draws), not a modeling gap. *(Figure 9: phase-wise AUC.)*

**Search.** Following the "late game is readable" result, we built a *non-learning*
tactical layer: use the engine's *exact* forward search on **our own turn only**
— which is near-perfect-information (the opponent doesn't act, our hand is
visible, so the placeholder problem of §3 vanishes) — to catch lethal KOs the
heuristic's damage estimate misses. Three variants (prize-maximize, lethal-only,
K-sample-robust lethal) **all fail to beat the tuned policy in the mirror
(≤0.47)**. Even exact near-terminal search loses, because (a) our own draws make
the turn not truly deterministic (false-positive lethals), (b) greedy
near-terminal optimization breaks the heuristic's coherent multi-turn gust-and-KO
plan, and (c) the heuristic already catches lethals. *(Figure 10: 3 variants ≤0.47.)*

Together, exp014 (learning) and exp015 (search) close both levers: **the
meta-reading rule-based agent with good piloting is the achievable ceiling.**

## 9. Conclusion

Strength in this game is reading the *rotating meta*, not just the board. Our
contributions — a controlled proof that opponent modeling sets the value of
search, a data-driven pipeline that tracks and counters a real three-way
rotation, and a rigorous demonstration that *both* learning and exact search fail
to exceed a well-piloted heuristic — together form a reproducible, honest account
of *why* a mid-compute team should invest in meta-tracking and piloting rather
than ever-bigger models. Future work: automatic archetype inference for
production-time belief, spread-deck robustness, and deck innovation against the
converged apex.

*Code, decklists, per-experiment notes, and the numeric ledger backing every
figure are in the project repository (exp001–exp015, `report_evidence.md`).*
