# Media Gallery — upload order and captions

Upload in this order. Captions are written to stand alone, because a reader may
open the gallery before the text.

## 01_gate_vs_ladder.png
**Every matchup our gauntlet claimed to cover was overstated.**
Predicted win rate against measured win rate, per opponent archetype (Japanese card
names included), ordered by
share of the metagame. 6,292 ladder games (2026-08-13..15), restricted to seats
running our exact 60 cards. ex-beatdown had no entry in the gauntlet at all and
was 27.3% of the field. Field-weighted true win rate: 0.33.

## 02_metrics_disagree.png
**Our two internal metrics select different models.**
Held-out imitation accuracy against gauntlet score across four corpus sizes. The
most accurate imitator (2.4M decisions) is not the highest-scoring agent (1.4M),
and neither metric is checked against anything outside our own machine.

## 03_metagame_drift.png
**An evaluation result without a date on it does not reproduce.**
Upper panel: share of the field by archetype over one week; the two decks we lose
to went from 23.5% to 61.5% while our own archetype fell from 25.6% to 6.1%. Lower
panel: our measured per-matchup win rates applied to each day's composition, with
the agent held completely fixed — 0.415 to 0.334, about 60 rating points.

## 04_deck_plan.png
**Marnie's Grimmsnarl ex: one Ability pays the Energy, two do the arithmetic.**
Punk Up settles the attacker's Energy out of the deck, which frees the single
Energy attachment per turn for Munkidori, whose Adrena-Brain needs {D} attached.
Across 145 winning games on our exact list, Munkidori was benched and given Energy
in all 145, at a median of turn 2.

## 05_ledger.png
**Ten lanes tested, one clean pass on our own gauntlet.**
What we changed, how many times, and how it scored. Every lane but the last was
judged by the instrument in Figure 1, which is the argument of the report.
