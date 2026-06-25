# Reading the Meta, Not Just the Board
### Opponent Modeling and Data-Driven Meta-Tracking in a Partially-Observed Trading Card Game

*Strategy Writeup — Pokémon TCG AI Battle Challenge*

---

## Abstract

Most agents in this competition try to play the *board* well. We argue the
decisive skill is playing the *meta* well. We contribute three results. **(1)
Opponent modeling, not raw search, determines an agent's strength.** A controlled
experiment shows that grounding the search's hidden-information model in a *real*
believed decklist beats a placeholder **5× (0.417 vs 0.083** vs the rule-based
pool). **(2) The ladder is a *rotating* rock-paper-scissors** — ex-beatdown →
anti-ex wall → single-prize non-ex → … — and we built a replay pipeline that
*measures* the rotation and ships a counter for each phase, reaching LB ~1120
(top-quartile) with a deck reconstructed from a top-ranker's replays. **(3) Piloting is the #1 lever — and information-bounded for us.** A top player
out-scores us by 200 rating with our *exact* deck, so the gap is piloting, not deck.
Yet we close *every* lever above a tuned heuristic: a learned value net can't read
the mid-game (AUC 0.64 < 0.70), exact near-terminal search fails, and **six** ways to
imitate a top pilot (behavior cloning, k-NN retrieval, self-imitation, self-play
MCTS…) all fall *below* a generic policy — because the expert's move is only ~50%
predictable from the observable state at our data scale. At mid compute, **a
meta-reading rule-based agent with a strong deck is the achievable ceiling** (≈**0.66**
win-rate vs the live field) — and we show *why* with data.

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
loss causes. Every strategic decision below is grounded in this pipeline, not
intuition. *(Figure 1: matchup matrix; Figure 2: strength ranking.)*

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
originality core of our work, and unverified in public notebooks (where the search
API is often called with a wrong signature, i.e. disabled). *(Figure 3: belief vs
placeholder.)*

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

- **Hop's Trevenant** ("Horrifying Revenge", 1 energy, boostable) — 1-prize main attacker.
- **Dunsparce → Dudunsparce** ("Run Away Draw") — the consistency/tempo engine.
- **Hop's Choice Band (+30 / −1 cost)** and **Postwick stadium (+30)** — push attacks to KO thresholds on ex.
- **Hop's Snorlax** ("Extra Helpings", +30 while benched); **Boss's Orders** — gust for the close.

Every attacker is single-prize, so the deck is structurally favored in the prize
race and immune to ex-only Safeguard. *(Figure 6: deck list + synergy.)*

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
7: patched-vs-generic gains.)*

**Discipline is the one heuristic that moves the mirror.** Splitting top players'
replays by opponent archetype showed their edge is **not** opponent-reading (our
move-match is a uniform ~0.28 everywhere) but **prize-liability discipline**: they
bench fewer Pokémon (~3 vs our 4+), giving up fewer 1-prize KO targets. Our patch
(cap the attacker line, keep a bench slot, add an attacker only when behind on
prizes) is the first heuristic to beat our own mirror — 0.55 paired (n=200, CI
excludes 0.5). But the *ladder* mirror stayed ~0.40: real opponents out-pilot us by
more than the patch recovers — a first hint that piloting is the binding ceiling (§8).

## 7. Stability and Operations (the Model "robustness" axis)

Two unglamorous factors dominate ladder rating. **Crash-safety**: a wrapper that
turns any exception or illegal move into a legal fallback — worth an estimated +64
rating and a guarantee we never forfeit. **Speed**: 0.02–0.16 s/move keeps us far
inside the timeout (our PIMC search variant, at ~30 s/move, was too slow to ship).
Operationally we run a weekly loop: `meta-watch` (detect rotation) →
`extract-deck` (clone the new apex) → `build-submit` (build, smoke-test the real
artifact, submit). *(Figure 8: stability vs LB.)*

## 8. We Closed Both "Smarter" Levers — With Data

A credible strategy report must say what *didn't* work — and every path beyond a
tuned heuristic is empirically bounded at our resource level.

**Learning (RL).** Self-play belief-MCTS is an honest negative: win-rate *drops* as
search grows (0.31→0.19→0.13 at 24→48→96 sims), so the learned **value net is the
bottleneck**. We then tested the principled unblocker — calibrate value on real
outcomes — on **319 top-ranker games** (real labels, episode-level holdout). The value
net **cannot read the mid-game** (phase-0.4–0.6 AUC **0.637** with scalars, **0.585**
even with card embeddings — both ≈ prize-difference alone, 0.688); only the *late* game
is predictable (AUC **0.80**). This explains "more search = worse": value is
uninformative exactly where search acts, so MCTS amplifies noise — and the variance
appears *game-intrinsic*. *(Figure 9: phase-wise AUC.)*

**Search.** A *non-learning* tactical layer — the engine's *exact* forward search on
**our own turn only** (near-perfect-info, so §3's placeholder problem vanishes) to
catch lethals — also fails: three variants all score ≤0.47 in the mirror, because our
own draws make the turn non-deterministic (false-positive lethals), greedy
near-terminal play breaks the heuristic's multi-turn plan, and the heuristic already
catches real lethals. *(Figure 10: 3 variants ≤0.47.)*

**Deck innovation and setup discipline** close the same way. An *original* deck
around a structural anti-mirror attacker (Tinkaton, "Windup Swing"
240 − 60×opponent-energy) scored **0.00** in the mirror: its Stage-2 line is
unpilotable by a generic policy — *pilotability is the binding constraint*, which is
why we run a Stage-1 deck. And trimming our (host-confirmed optional) setup-bench is
a **no-op** for our Basic-light deck.

**Piloting — the #1 lever — resists every method we have.** Scouting the top exposed
where the gap lives: the #3 player runs our *exact* deck yet sits +200 LB above us
(mirror 0.68 vs our 0.40), and the #2 player's Mega-Starmie deck beats our non-ex
**0.825** even under our generic policy. So the gap is *piloting*, not deck. We tried
to capture one top pilot's play six ways — replay heuristics; behavior cloning (0.49
action-match but error-accumulates *below* the floor); k-NN retrieval (0.42 — states
identical in our features had *different* expert moves 58% of the time); richer
features (pure overfit); value-free self-imitation; and self-play MCTS (whose official
sample fills the opponent with placeholders, the §3 flaw) — **all underperform the
generic policy.** A model-free check then *seals* it: on real ladder games, **when a
card is a legal play we take it at the top pilot's own rate** (Night Stretcher 19% vs
23%, Poké Pad 22% vs 26%); the entire usage gap is *exposure* — the expert sees those
options 5–6× more often, an artifact of longer, better-developed games. Our *decision
quality already matches the top*; the residual is game-length throughput, a consequence
of board outcomes rather than a patchable choice. Imitation here is
*information-bounded, not effort-bounded*. *(Figure 11: six methods vs the floor;
take-when-legal parity.)*

Together these experiments close every lever above the heuristic — learning, search,
deck design, setup discipline, and direct imitation of a top pilot. A weighted
analysis over the live field (ex 39%, non-ex 26%, wall 11%, Alakazam 11%) puts our
final agent at ≈**0.66**. The one structural counter is a well-piloted spread deck (a
public Dragapult ex beats us **0.78**) but it is meta-contained today (0.47 field —
it loses to ex 0.40 and to the wall 0.00). We *hold and monitor* rather than chase
it — a call our replay pipeline makes, not intuition.

## 9. Conclusion

Strength in this game is reading the *rotating meta*, not just the board. Our
contributions — a controlled proof that opponent modeling sets the value of search,
a data-driven pipeline that tracks and counters a real three-way rotation, and a
rigorous demonstration that *every* lever above a well-piloted heuristic
(learning, exact search, deck design, setup discipline, and six attempts at imitating
a top pilot) is empirically bounded at our resource level — together form an honest,
reproducible account of *why* a mid-compute team should invest in meta-tracking and
piloting rather than ever-bigger models. The deepest finding is that **piloting is the
sport's #1 lever yet information-bounded for us**: a top player out-scores us by 200
rating with our *exact* deck, but their move is only ~50% predictable from the
observable state at our data scale, so imitation and self-play both fall below a
generic policy. Future work: automatic archetype inference for production-time belief,
and — the one path that might crack piloting — a far larger multi-expert imitation
corpus with the official transformer, beyond our compute.

*Code, decklists, per-experiment notes, and the numeric ledger backing every
figure are in the project repository (exp001–exp022, `report_evidence.md`).*
