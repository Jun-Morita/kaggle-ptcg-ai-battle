# Playtesting Against Ourselves
### Our offline win rates never matched the ladder. Here is the part we could not fix.

*Strategy Writeup — Pokémon TCG AI Battle Challenge · Team Morita*

<!-- RANK LINE: updated 2026-09-02 (ladder frozen 09-01, no host finalization post yet). Re-check before submitting. -->
 ---

## Abstract

Our agent plays **Marnie's Grimmsnarl ex (マリィのオーロンゲex)** by imitating strong
human pilots: a gradient-boosted ranker scores the legal options at each
decision and we take the top one. It finished at rank 276 of 6,807, the top
4.1%, when the leaderboard stopped moving on 2026-09-01, which puts it 16 rating
points inside the silver band. Sixteen points is less than the spread we
measured between byte-identical submissions (§4.1), so that rank is closer to a
single sample than to a measurement of strength.

Most of this report is about how we tested, because that is what decided where
we finished. Offline testing in a live-ladder card game goes wrong in three
ways, and each one can be measured on its own. Draw variance we removed, by
giving both halves of a paired match the same shuffle seed (4.66× less
variance). Bias in the practice opponents is what finished us: our sparring
partners were clones we had built ourselves, and they overstated every matchup,
one of them by 0.52. Drift moved a frozen agent 60 rating points in six days.
Playing more games fixes the first and nothing else, which is how a gauntlet can
look stable and stay wrong for a week.

---

## 1. What we built

The submission runs as pure Python with no numpy, so a large neural policy was
never an option, and the ladder is live, so the opponents you tune against are
not the opponents you are scored against. We chose imitation learning. The daily
episode dumps contain thousands of games played by people rated above 1000, and
a model that learns which option those players chose is cheap to train, cheap to
run, and deterministic: we take the argmax, so the same position is always
played the same way.

---

## 2. The deck: one Ability pays for the whole engine

We played **Marnie's Grimmsnarl ex (マリィのオーロンゲex)**, the most-played archetype on
the ladder. A Stage 2 deck normally pays for its power twice, once in setup and
again in Energy. This one only pays for setup.

**Punk Up (パンクアップ)** covers the Energy half. When Marnie's Grimmsnarl ex
evolves, you search your deck for up to 5 Basic Darkness Energy and attach them
to your Marnie's Pokémon, so the turn you complete the line you are already
powered up, and the board keeps that Energy even after a Knock Out. That is why
the list runs 10 Energy and no other acceleration.

**Shadow Bullet (シャドーバレット)** is the attack: {D}{D} for 180 damage, plus 30 to
one of your opponent's Benched Pokémon. The 180 takes down almost anything in
two hits. The 30 is what turns the game into an arithmetic problem.

Two Abilities finish that arithmetic. **Freezing Shroud** on **Froslass
(ユキメノコ)** puts a damage counter on every Pokémon that has an Ability during
Pokémon Checkup, on both sides of the board. **Adrena-Brain** on **Munkidori
(マシマシラ)** then moves up to 3 of those counters onto a Benched Pokémon that
Shadow Bullet has already hit for 30.

The Energy budget is what ties the two Abilities together (Figure 4).
Adrena-Brain only works while Munkidori has a {D} Energy attached, and Punk Up
cannot supply it, because Punk Up attaches only to *Marnie's* Pokémon. But Punk
Up has already paid for the attacker out of the deck, which leaves your one
Energy attachment for the turn free to go on Munkidori. Strong players treat
this as compulsory: across 145 winning games played with our exact 60 cards,
Munkidori was benched and given Energy in all 145, at a median of turn 2, and
players rated 1001 did it as reliably as players rated 1120. Our agent does the
same in 40 games out of 40, so it does not depend on a good opening hand. It
depends instead on the twelve slots whose only job is to find the line: 4
Spikemuth Gym (スパイクタウンジム), 4 Team Rocket's Petrel (ロケット団のラムダ), 3 Rare Candy
(ふしぎなアメ), 1 Dawn (ヒカリ). Marnie's Grimmsnarl ex gives up two Prize cards when it
falls, so the plan is to take three Knock Outs from behind a 320 HP attacker
that the format needs two turns to remove.

**Where the engine becomes a liability.** Marnie's Grimmsnarl ex is a {D} Pokémon
with Weakness to {G}, and **Teal Mask Ogerpon ex (オーガポン みどりのめんex)** attacks
with Myriad Leaf Shower, which does 30 damage plus 30 for each Energy attached to
*both* Active Pokémon. Five Energy across the two of them is 180, and Weakness
doubles that to 360 against our 320 HP. Shadow Bullet supplies two of those five
Energy itself, so the counter only has to bring three. The acceleration that makes
our deck fast is the same thing that brings it inside range of a one-shot. We never
spotted this.
[kiyomiya-k](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/737125)
built the deck that punishes it, went 95% against Grimmsnarl over 222 games, and
summed it up: the pilot fixes decisions, but only the deck fixes arithmetic.

---

## 3. Method: imitate the right teachers, then bend the sample

**Corpus.** We keep only the winning side of games whose 60 cards match our list
exactly. A corpus that accepted any Grimmsnarl variant reached higher held-out
accuracy (top-k 0.684 → 0.798) but lost head-to-head against our own shipped
build (0.510 → 0.315). It had learned, faithfully, to pilot somebody else's
deck. Having less data cost us less than learning from the wrong teacher.

**Model.** A gradient-boosted ranker scores every legal option, with a separate
model for each decision context. The features are written in a player's
vocabulary rather than as card indices: Prize cards left on each side, how many
Knock Outs still close the game, Energy attached against Energy required,
whether an attack is lethal this turn, and how many Prize cards our own Bench is
offering the opponent.

**What we tested.** Figure 5 is the ledger: eight corpus sizes, five feature
sets, five rival decks, two search variants, and one change that cleared our own
bar. What worked was not more data, more features or a bigger model, but
reweighting the training rows by the opponent archetype each decision was played
against, which lifts the matchups we lose. The weighting has an interior
optimum: past an effective share of roughly 15%, the boosted matchup keeps
improving while the overall score falls. We cannot confirm the gain on the
ladder either. Our two eligible submissions differ only in these weights, and
they have drifted 99 rating points apart, which is well inside the spread that
identical submissions produce (§4.1).

---

## 4. Why testing lies: three error terms, and we removed the wrong one

Every offline decision we made went through one instrument, a weighted win rate
against a fixed pool of six opponents, and it never predicted the ladder. Taking
it apart gives three error terms, and they do not behave the same way.

**4.1 Variance: draws and mulligans.** Results here are dominated by opening
hands, so a gauntlet number moves even when nothing has changed. We patched a
single engine function so that the shuffle seed can be set from outside, then
gave both seat orderings of a matchup the same seed. Over six repeats the
variance of the estimate fell by 4.66×, which buys the statistical power of
1,000 games from about 220. This is the term that rewards effort, and we spent
it. The same term also sits on the leaderboard, where nobody can do anything
about it: kiyomiya-k submitted a byte-identical tarball seven times and scored
between 687 and 856, an sd of 51. Every rank on that board, ours included, is a
sample from a distribution that wide.

**4.2 Bias: the practice partners are not the opponents.** Three days of ladder
replays, 6,292 games, let us measure the matchups our gauntlet claimed to cover,
using our exact 60 cards (Figure 1). Every one of them was overstated. Dragapult
ex (ドラパルトex): 0.865 predicted against 0.341 actual (n=264). Alakazam-type
(フーディン): 0.864 against 0.421 (n=183). ex-beatdown had no entry in the gauntlet
at all, made up 27.3% of the field, and held us to 0.193. Weighted by what we
actually faced, our win rate was 0.33.

The cause is structural. Those opponents were clones we had built, and a deck
piloted by the person who copied it is weaker than the same deck in the hands of
someone who plays it. This error does not shrink when you add games, and it
applies to every candidate about equally, so the ranking between candidates
stays stable and the instrument never signals that it is wrong. The one signal
that could have caught it early gave us samples of n=4 to 14.

Our other internal metric was no better. Held-out imitation accuracy selected a
different model than the gauntlet did (Figure 2), and the smallest corpus scored
almost as well as one six times its size, because a smaller corpus also draws
its held-out set from a narrower distribution. That left us with two
self-referential metrics that disagreed, and nothing outside them to settle the
disagreement.

**4.3 Drift: the format rotates underneath the instrument.** Holding our agent
fixed and changing only the composition of the metagame between 2026-08-09 and
08-15, its expected win rate falls from 0.415 to 0.334, which is about 60 rating
points (Figure 3). An evaluation result without a date on it does not reproduce.

**4.4 A better gauntlet was never the answer.** Variance gives way to technique;
bias only gives way to opponents you did not choose yourself. What we needed was a
growing pool of other people's bots scored by relative rating, which is what the
teams above us built.
[Abhyuday](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735649),
in the top 30, could estimate his true ladder rating to within ±30 in the half hour
after submitting. We built a statistically careful version of the wrong measurement.

---

## 5. What that cost: the deck decision

We considered changing decks three times and rejected it three times. Each time
the decision went through an instrument that favoured the deck we already had:
the opponents in it were our own clones, its weights described the metagame as
seen from our deck, and its features were built around our deck. Any rival
archetype was measured with our handicap attached to it.

There was another way to decide, and we had used it once already. In July the #1
player abandoned his archetype for this one; we read 1,000 of his replays and
followed him.
[Anil Ozturk](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/736121)
did the same thing in August, starting on Grimmsnarl for the reasons we did and
switching after he saw 9 of the top 12 teams on Dragapult ex (ドラパルトex). No local
evaluation was involved in either decision.

We had the same observation available and ran it through the broken instrument
instead. We still cannot say whether the right answer was a different deck or a
better pilot: that same #1 player beat Dragapult ex 0.92 of the time with our
exact 60 cards, where we managed 0.341, and our instrument could not tell those
two explanations apart.

---

## 6. What the top of the ladder did differently

We told ourselves that PPO plateaus in this game. It does not. It plateaus at our
throughput.
[Team Preferred](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735867)
ran behaviour cloning followed by PPO, at 117M parameters over 1.68 billion
environment steps, which is easy to write off as a hardware gap. Harder to write off
is [rick](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/738158),
who reached 1132 with a 12M-parameter transformer on a single RTX 3090, because he
had rebuilt the environment in vectorised C++ and ran 30 games a second where we
drove the sequential binary one game at a time. The constraint was never model size.

His curriculum went multi-deck, then archetype-specific, then deck-specific,
which is the same shape as Ozturk's portfolio model fine-tuned into specialists.
Three teams arrived at it independently. We had nothing like it, and trained
every clone from scratch on a thin corpus, which is why none of them could pilot
anything. Ozturk's value-head numbers also explain why adding lookahead made our
agent weaker on both attempts: a value head trained by imitation has only ever
seen expert positions, and search asks it to judge positions that are not (−20
to −30 rating with a cloned value head, against +50 to +70 with an on-policy
one).

---

## 7. Robustness and operations

The dangerous failure in an agent competition is the one that looks like an
ordinary loss. Our agent catches every exception and falls back to a legal move,
which means a broken model plays a full, quiet, losing game and reports no
errors at all. That caught us out six times. The guards that fixed it are cheap:
assert that the model object actually loaded, require zero fallbacks in the
smoke test, and require a minimum smoke win rate, since a build that loses 0-25
to a weak opponent is broken rather than weak. The policy is deterministic, so
repeated matches differ only in the deal; every experiment records its seed, git
SHA and config hash; and the shipped artifact makes about 197 decisions per
game, with a worst observed move time of 1.28 s and no validation errors on the
ladder.

---

## Conclusion

We tuned the policy carefully and measured it carelessly, and the measurement is
what decided where we finished. Given the same two months again, we would spend
the first week building the evaluation instead of the agent: an arena holding
every bot we and other people have produced, scored by relative rating, so that
a candidate is always ranked against opponents we did not pick. Almost
everything else on our list was settled by that instrument long before the game
itself had a chance to settle it.