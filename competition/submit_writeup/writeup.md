# Playtesting Against Ourselves
### Our offline win rates never matched the ladder. Here is the part we could not fix.

*Strategy Writeup — Pokémon TCG AI Battle Challenge · Team Morita*


---

## Abstract

Our agent plays **Marnie's Grimmsnarl ex** by imitating strong human pilots, using
a gradient-boosted ranker over the legal options at each decision. It stood at
rank 430 of 6,809 on 2026-08-22, partway through the evaluation period. This report
is mostly about the thing that set that number, which was not the policy but the
way we tested it.

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
opponents you are scored against. We chose imitation over reinforcement learning:
the official daily episode dumps hold thousands of games by players rated above
1000, and a model that learns which option those players took is cheap to train,
cheap to run, and deterministic, taking the argmax so that the same position always
plays the same way.

---

## 2. The deck: one Ability pays for the whole engine

We played **Marnie's Grimmsnarl ex (マリィのオーロンゲex)**, the most-played
archetype on the ladder. A Stage 2 deck usually pays for its power twice, in setup
and in Energy. This one only pays for setup.

**Punk Up (パンクアップ)** does the second half. When Grimmsnarl ex evolves it
searches out up to 5 Basic Darkness Energy and attaches them across your Marnie's
Pokémon, so the turn you finish the line you are already powered, and the board
keeps that Energy through a Knock Out. That is why the list runs 10 Energy and no
other acceleration.

**Shadow Bullet (シャドーバレット)** is the attack: {D}{D} for 180, plus 30 to one
of your opponent's Benched Pokémon. The 180 covers almost everything in two hits.
The 30 turns a beatdown deck into an arithmetic problem.

Two Abilities finish the arithmetic. **Freezing Shroud** on **Froslass (ユキメノコ)**
puts a damage counter on every Pokémon with an Ability during Pokémon Checkup, both
sides of the table included. **Adrena-Brain** on **Munkidori (マシマシラ)** moves up
to 3 damage counters from one of our Pokémon to one of theirs. Freezing Shroud
damages our own board too, Grimmsnarl ex included, and Adrena-Brain exports that
damage onto a Benched Pokémon Shadow Bullet has already hit for 30.

The Energy budget joins the two Abilities (Figure 4). Adrena-Brain only works while
Munkidori has {D} Energy attached, and Punk Up cannot supply it, because it
attaches only to *Marnie's* Pokémon. But Punk Up has already paid for the attacker
out of the deck, so your one Energy attachment for the turn is free to go on
Munkidori. Winning players treat this as mandatory. Across 145 winning games played
with our exact 60 cards, Munkidori was benched and given Energy in all 145, at a
median of turn 2, and players rated 1001 did it as consistently as players rated
1120. Our agent reproduces it in 40 games out of 40, so the deck does not lean on a
good opening hand. It leans on twelve slots whose only job is to find the line:
4 Spikemuth Gym (スパイクタウンジム, each player may search out a Marnie's Pokémon
once per turn), 4 Team Rocket's Petrel, 3 Rare Candy, 1 Dawn. Grimmsnarl ex gives
up two Prize cards when it falls, so the plan is three Knock Outs from behind a
320-HP attacker the format needs two turns to remove.

---

## 3. Method: imitate the right teachers, then bend the sample

**Corpus.** We keep only the winning side of games whose 60 cards match our list
exactly. That filter mattered more than volume. An earlier corpus that accepted any
Grimmsnarl variant reached a higher held-out accuracy (top-k 0.684 → 0.798) and
simultaneously lost head-to-head against our own shipped build (0.510 → 0.315). It
had faithfully learned to pilot somebody else's deck. Fidelity to the wrong teacher
is worse than having less data.

**Model.** A gradient-boosted ranker scores every legal option, with a separate
model per decision context. The features are written in the vocabulary a player
uses rather than as card indices: Prize cards left on each side, how many Knock
Outs still close the game, Energy attached against Energy required, whether an
attack is lethal this turn, how many Prize cards our own Bench is offering.

**What we tested.** Figure 5 is the ledger: eight corpus sizes, five feature sets,
five rival decks, two search variants, and one intervention that cleared our own
bar. The winner was not more data, more features or a bigger model, but reweighting
the training rows by the opponent archetype each decision was played against, which
lifts the matchups we lose. It has an interior optimum: past roughly a 15% effective
share the boosted matchup keeps improving while the overall score falls.

---

## 4. Why testing lies: three error terms, and we removed the wrong one

Every offline judgement we made ran through one instrument, a weighted win rate
against a fixed pool of six opponents. It never predicted the ladder. Pulling it
apart gives three error terms that behave differently.

**4.1 Variance — draws and mulligans.** Outcomes here are dominated by opening
hands, so a gauntlet result moves when nothing has changed. We patched one engine
function so the shuffle seed could be set from outside, then gave both seat
orderings of a matchup the same seed. Across six repeats the variance of the
estimate fell 4.66×, buying the power of 1,000 games from about 220. This is the
term that rewards effort, and we spent the effort.

**4.2 Bias — the sparring partners are not the opponents.** Three days of ladder
replays, 6,292 games, let us measure the matchups the gauntlet claimed to cover
using our exact 60 cards (Figure 1). Every one was overstated: Dragapult 0.865
predicted against 0.341 actual (n=264), Alakazam-type 0.864 against 0.421 (n=183).
ex-beatdown had no cell in the gauntlet at all, was 27.3% of the metagame, and beat
us to 0.193. Weighted by what we actually faced, our true win rate was 0.33.

The cause is structural. Those opponents were clones we had built, and a deck
piloted by its copier is weaker than the same deck in the hands of someone who
plays it. That error does not shrink as you add games, and it lands on every
candidate equally, so the ranking stays stable and the instrument never announces
that it is wrong. The one signal that could have caught it, real ladder games per
candidate, gave us n=4–14.

Our other internal metric did no better. Held-out imitation accuracy picked a
different model than the gauntlet did (Figure 2): the most accurate imitator was
not the strongest agent, and the smallest corpus scored nearly as well as one six
times its size, because a smaller corpus draws its held-out set from a narrower
distribution. Two self-referential metrics that disagreed, with nothing outside to
settle it.

**4.3 Drift — the format rotates underneath the instrument.** Hold the agent fixed
and change only the composition of the metagame between 2026-08-09 and 08-15:
expected win rate falls from 0.415 to 0.334, about 60 rating points (Figure 3). An
evaluation result without a date does not reproduce.

**4.4 A better gauntlet was never the answer.** Variance yields to technique; bias
only yields to opponents you did not choose. The instrument we needed was a growing pool
of bots scored by relative rating, which is what the competitors above us built.
[Abhyuday](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735649),
who finished in the top 30, estimated his true ladder rating to within ±30 in the
half hour after submitting. We built the statistically careful version of the wrong
measurement.

---

## 5. What that cost: the deck decision

We considered changing decks three times and rejected it three times, each time
through an instrument that favoured the deck we already had: its opponents were our
own clones, its weights described the metagame as seen from our deck, its 361
features were built around our deck. A rival archetype was measured with our
handicap bolted on.

The alternative was available, and we had used it once already: in July we noticed
the #1 player abandon his archetype for this one, confirmed it across 1,000 of his
replays, and followed him. [Anil Ozturk](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/736121)
did the same in August, starting on Grimmsnarl for the reason we did and then
switching after seeing 9 of the top 12 teams on Dragapult. No local evaluation was
involved.

We had the same observation in front of us and put it through the broken instrument
instead. We still cannot say whether the answer was a different deck or a better
pilot: that same #1 player beat Dragapult 0.92 of the time with our exact 60 cards,
where we managed 0.341, and our instrument had no way to tell those two
explanations apart.

---

## 6. What the top of the ladder did differently

Three things, from the post-deadline write-ups.
[Team Preferred](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735867)
ran behaviour cloning then PPO with per-deck specialists at 117M parameters over
1.68 billion environment steps; we had one desktop GPU, so skipping reinforcement
learning was right for our budget, but our stated reason — that PPO plateaus in
this game — was wrong. It plateaus at our scale. Ozturk trained one portfolio model
across ten archetypes and fine-tuned each specialist out of it, where we trained
every clone from scratch on its own thin corpus, which is why our clones could not
pilot anything. And his value-head numbers explain why lookahead made our agent
weaker twice: a value head trained by imitation has only seen expert positions, and
search asks it to judge positions outside them (−20 to −30 rating with a cloned
value head, +50 to +70 with an on-policy one).

---

## 7. Robustness and operations

The dangerous failure in an agent competition is the one that looks like an
ordinary loss. Our agent catches every exception and falls back to a legal move, so
a broken model plays a full, quiet, losing game and reports no errors. It caught us
out six times. The guards that finally worked are cheap: assert the model object
loaded, require zero fallbacks in the smoke test, and require a minimum smoke win
rate, because a build losing 0–25 to a weak opponent is broken rather than weak.
One top team found after the deadline that their eight-checkpoint specialist had
shipped with the wrong decklist, so the failure mode survives all the way up.

The policy itself is deterministic, so repeated matches differ only in the deal,
and every experiment records its seed, git SHA and config hash. The shipped
artifact makes about 197 decisions per game, worst observed move 1.28 s, and
completed its ladder games with no validation errors.

---

## Conclusion

We tuned a policy carefully and measured it carelessly, and the measurement decided
where we finished. Given the same two months again we would spend the first week
building the evaluation rather than the agent: an arena of every bot we and other
people have produced, scored by relative rating, so that a candidate is always
ranked against opponents we did not choose. Everything else on the list was
answered by that instrument long before the game had a chance to answer it.

---

*Figures 1–5 are in the Media Gallery.*
