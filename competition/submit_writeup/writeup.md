# Playtesting Against Ourselves
### Our offline win rates never matched the ladder. Here is the part we could not fix.

*Strategy Writeup — Pokémon TCG AI Battle Challenge · Team Morita*


---

## Abstract

Our agent plays **Marnie's Grimmsnarl ex** by imitating strong human pilots, using
a gradient-boosted ranker over the legal options at each decision. It stood at rank
276 of 6,807 on 2026-09-01, inside the silver band by 16 rating points, with the
final evaluation still running — and that number is one draw rather than a
measurement. This report is mostly about the thing that
set it, which was not the policy but the way we tested it.

Offline testing in a live-ladder card game goes wrong in three ways that can be
measured separately, and we measured all three: draw variance, which we removed by
seeding both halves of a paired match identically (4.66× less variance); bias in
the opponents, which finished us, because our practice partners were clones we had
built and they overstated every matchup, one by 0.52; and drift, which moved a
frozen agent 60 rating points in six days. More games fix the first and do nothing
for the second, which is how a gauntlet that looks stable stays wrong for a week
without saying so.


---

## 1. What we built

The submission runs as pure Python with no numpy, which rules out a large neural
policy, and the leaderboard is live, so the opponents you tuned against are not the
opponents you are scored against. We chose imitation: the daily episode dumps hold
thousands of games by players rated above 1000, and a model that learns which option
those players took is cheap to train, cheap to run, and deterministic, taking the
argmax so the same position always plays the same way.

---

## 2. The deck: one Ability pays for the whole engine

We played **Marnie's Grimmsnarl ex (マリィのオーロンゲex)**, the most-played
archetype on the ladder. A Stage 2 deck usually pays for its power twice, in setup
and in Energy. This one pays only for setup.

**Punk Up (パンクアップ)** does the second half. When Grimmsnarl ex evolves it
searches out up to 5 Basic Darkness Energy and attaches them across your Marnie's
Pokémon, so the turn you finish the line you are already powered, and the board
keeps that Energy through a Knock Out. Hence 10 Energy and no other acceleration.

**Shadow Bullet (シャドーバレット)** is the attack: {D}{D} for 180, plus 30 to one of
your opponent's Benched Pokémon. The 180 covers almost everything in two
hits; the 30 makes it an arithmetic problem.

Two Abilities finish the arithmetic. **Freezing Shroud** on **Froslass (ユキメノコ)**
puts a damage counter on every Pokémon with an Ability during Pokémon Checkup, both
sides included, and **Adrena-Brain** on **Munkidori (マシマシラ)** moves up to 3 of
those counters onto a Benched Pokémon that Shadow Bullet has already hit for 30.

The Energy budget joins the two Abilities (Figure 4). Adrena-Brain only works while
Munkidori has {D} Energy attached, and Punk Up cannot supply it, because it
attaches only to *Marnie's* Pokémon. But Punk Up has already paid for the attacker
out of the deck, so your one Energy attachment for the turn is free to go on
Munkidori. Winning players treat this as mandatory. Across 145 winning games played
with our exact 60 cards, Munkidori was benched and given Energy in all 145, at a
median of turn 2, and players rated 1001 did it as consistently as players rated
1120. Our agent reproduces it in 40 games of 40, so the deck does not lean on a good
opening hand. It leans on twelve slots whose only job is to find the line:
4 Spikemuth Gym, 4 Team Rocket's Petrel, 3 Rare Candy, 1 Dawn. Grimmsnarl ex gives
up two Prize cards when it falls, so the plan is three Knock Outs from behind a
320-HP attacker the format needs two turns to remove.

**Where the engine becomes the liability.** Grimmsnarl ex is {D} and weak to {G},
and Teal Mask Ogerpon ex (オーガポン みどりのめんex) has Myriad Leaf Shower, which
does 30 plus 30 for each Energy on
*both* Active Pokémon. Five Energy between them makes 180, doubled by weakness to
360 against our 320. Shadow Bullet already pays two of those five, so the counter
needs three of its own: the acceleration that makes our deck fast is what puts it
inside a one-shot. We never noticed; kiyomiya-k built the deck
that reads it, went 95% against Grimmsnarl over 222 games, and put the lesson
plainly — the pilot fixes decisions, only the deck fixes arithmetic.

---

## 3. Method: imitate the right teachers, then bend the sample

**Corpus.** We keep only the winning side of games whose 60 cards match our list
exactly. A corpus that accepted any Grimmsnarl
variant reached a higher held-out accuracy (top-k 0.684 → 0.798) while losing
head-to-head against our own shipped build (0.510 → 0.315): it had faithfully
learned to pilot somebody else's deck. Fidelity to the wrong teacher is worse than
having less data.

**Model.** A gradient-boosted ranker scores every legal option, with a separate
model per decision context. Features are written in a player's vocabulary rather
than as card indices: Prize cards left on each side, how many Knock Outs still close
the game, Energy attached against Energy required, whether an attack is lethal this
turn, how many Prize cards our own Bench is offering to the opponent.

**What we tested.** Figure 5 is the ledger: eight corpus sizes, five feature sets,
five rival decks, two search variants, and one intervention that cleared our own
bar. The winner was not more data, more features or a bigger model, but reweighting
the training rows by the opponent archetype each decision was played against, which
lifts the matchups we lose. It has an interior optimum: past roughly a 15% effective
share the boosted matchup keeps improving while the overall score falls. The ladder
cannot confirm it either. Our two eligible submissions differ only in these weights
and have since drifted 99 rating points apart, which is well inside the spread that
identical submissions produce (§4.1).

---

## 4. Why testing lies: three error terms, and we removed the wrong one

Every offline judgement we made ran through one instrument, a weighted win rate
against a fixed pool of six opponents. It never predicted the ladder. Pulling it
apart gives three error terms that behave differently.

**4.1 Variance — draws and mulligans.** Outcomes are dominated by opening hands, so
a gauntlet result moves when nothing has changed. We patched one engine function so
the shuffle seed could be set from outside, then gave both seat orderings of a
matchup the same seed. Across six repeats the variance of the
estimate fell 4.66×, buying the power of 1,000 games from about 220. This term
rewards effort, and we spent it. The same term sits on the
leaderboard itself, where nobody can touch it:
[kiyomiya-k](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/737125)
submitted a byte-identical tarball seven times and scored 687 to 856, sd 51. Every
rank here, ours included, is a sample from something that wide.

**4.2 Bias — the practice partners are not the opponents.** Three days of ladder
replays, 6,292 games, let us measure the matchups the gauntlet claimed to cover
using our exact 60 cards (Figure 1). Every one was overstated: Dragapult
(ドラパルトex) 0.865 predicted against 0.341 actual (n=264), Alakazam-type
(フーディン) 0.864 against 0.421 (n=183).
ex-beatdown had no cell in the gauntlet at all, was 27.3% of the metagame, and held
us to 0.193. Weighted by what we faced, our win rate was 0.33.

The cause is structural: those opponents were clones we had built, and a deck
piloted by its copier is weaker than the same deck in the hands of someone who
plays it. That error does not shrink as you add games, and it lands on every
candidate equally, so the ranking stays stable and the instrument never announces
that it is wrong. The one signal that could have caught it gave us n=4–14.

Our other internal metric did no better. Held-out imitation accuracy picked a
different model than the gauntlet did (Figure 2), and the smallest corpus scored
nearly as well as one six times its size, because a smaller corpus draws its
held-out set from a narrower distribution. Two self-referential metrics disagreeing,
with nothing outside to settle it.

**4.3 Drift — the format rotates underneath the instrument.** Hold the agent fixed
and change only the composition of the metagame between 2026-08-09 and 08-15 and
its expected win rate falls from 0.415 to 0.334, about 60 rating points (Figure 3).
An evaluation result without a date does not reproduce.

**4.4 A better gauntlet was never the answer.** Variance yields to technique; bias
only yields to opponents you did not choose. The instrument we needed was a growing
pool of bots scored by relative rating, which is what the competitors above us built:
[Abhyuday](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735649),
top 30, estimated his true ladder rating to ±30 in the half hour after submitting.
We built the statistically careful version of the wrong measurement.

---

## 5. What that cost: the deck decision

We considered changing decks three times and rejected it three times, each time
through an instrument that favoured the deck we already had: its opponents were our
own clones, its weights described the metagame as seen from our deck, its features
were built around our deck. A rival archetype was measured with our handicap bolted
on.

The alternative was available, and we had used it once: in July the #1 player
abandoned his archetype for this one, we checked 1,000 of his replays, and followed
him. [Anil Ozturk](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/736121)
did the same in August, starting on Grimmsnarl for the reason we did and switching
after seeing 9 of the top 12 teams on Dragapult (ドラパルトex). No local evaluation was
involved.

We had the same observation in front of us and put it through the broken instrument
instead. We still cannot say whether the answer was a different deck or a better
pilot: that same #1 player beat Dragapult 0.92 of the time with our exact 60 cards
where we managed 0.341, and our instrument could not tell those two apart.

---

## 6. What the top of the ladder did differently

We told ourselves that PPO plateaus in this game. It does not; it plateaus at our
throughput.
[Team Preferred](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735867)
ran behaviour cloning then PPO at 117M parameters over 1.68 billion environment
steps, which is easy to dismiss as a hardware gap. Harder to dismiss is
[rick](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/738158),
who reached 1132 with a 12M-parameter transformer on one RTX 3090, because he had
rebuilt the environment in vectorised C++ and ran 30 games a second where we drove
the sequential binary one game at a time. The constraint was never model size.

His curriculum ran multi-deck, then archetype-specific, then deck-specific, the same
shape as Ozturk's portfolio model fine-tuned into specialists. Three teams reached it
independently; we lacked it, and trained every clone from scratch on a thin corpus,
which is why none could pilot anything. Ozturk's value-head numbers
also explain why lookahead made our agent weaker twice: a value head trained by
imitation has only seen expert positions, and search asks it to judge positions
outside them (−20 to −30 with a cloned value head, +50 to +70 with an on-policy one).

---

## 7. Robustness and operations

The dangerous failure in an agent competition is the one that looks like an
ordinary loss. Our agent catches every exception and falls back to a legal move, so
a broken model plays a full, quiet, losing game and reports no errors. It caught us
out six times. The guards that worked are cheap: assert the model object loaded,
require zero fallbacks, and require a minimum smoke win rate, since a build losing
0–25 to a weak opponent is broken rather than weak. The policy is deterministic, so
repeated matches differ only in the deal; every experiment records its seed, git SHA
and config hash; and the artifact makes about 197 decisions per game, worst observed
move 1.28 s, with no validation errors on the ladder.

---

## Conclusion

We tuned a policy carefully and measured it carelessly, and the measurement decided
where we finished. Given the same two months again we would spend the first week
building the evaluation rather than the agent: an arena of every bot we and other
people have produced, scored by relative rating, so a candidate is always ranked
against opponents we did not choose. Everything else on our list was answered by
that instrument long before the game could answer it.
