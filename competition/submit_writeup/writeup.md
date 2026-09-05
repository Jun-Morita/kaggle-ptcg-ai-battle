# Playtesting Against Ourselves
### Our offline win rates never matched the ladder. Here is the part we could not fix.

*Strategy Writeup — Pokémon TCG AI Battle Challenge · Team Morita*

---

## Abstract

Our agent plays **Marnie's Grimmsnarl ex (マリィのオーロンゲex)** by imitating strong human pilots: a gradient-boosted ranker scores the legal options at each decision and we take the top one. It finished at rank 276 of 6,807, the top 4.1%, when the leaderboard stopped moving on 2026-09-01, 16 rating points inside the silver band. Sixteen points is less than the spread between byte-identical submissions (§3.1), so the rank is closer to a single sample than to a measurement of strength.

This report is mostly about how we tested, because that decided where we finished. Offline testing against a live ladder goes wrong in three ways that do not behave alike: draw variance, which we removed with paired shuffle seeds (4.66× less variance); bias in the practice opponents, which finished us, because they were clones we had built ourselves; and drift, which moved a frozen agent 60 rating points in six days. More games fix the first and nothing else.

---

## 1. The deck: one Ability pays for the whole engine

We played **Marnie's Grimmsnarl ex (マリィのオーロンゲex)**, the most-played archetype on the ladder when we chose it in July. A Stage 2 deck normally pays for its power twice, once in setup and again in Energy. This one only pays for setup.

**Punk Up (パンクアップ)** covers the Energy half. When Marnie's Grimmsnarl ex evolves, you search out up to 5 Basic Darkness Energy and attach them to your Marnie's Pokémon, so the turn you complete the line you are already powered up, and the board keeps that Energy through a Knock Out. Hence 10 Energy and no other acceleration.

**Shadow Bullet (シャドーバレット)** is the attack: {D}{D} for 180 damage, plus 30 to one of your opponent's Benched Pokémon. The 180 takes down almost anything in two hits. The 30 turns the game into an arithmetic problem.

Two Abilities finish that arithmetic. **Freezing Shroud** on **Froslass (ユキメノコ)** puts a damage counter on every Pokémon with an Ability during Pokémon Checkup, on both sides of the board. **Adrena-Brain** on **Munkidori (マシマシラ)** then moves up to 3 of those counters onto a Benched Pokémon that Shadow Bullet has already hit for 30.

The Energy budget is what ties the two Abilities together (Figure 4). Adrena-Brain needs a {D} Energy on Munkidori, and Punk Up cannot supply it, because it attaches only to *Marnie's* Pokémon. But Punk Up has already paid for the attacker out of the deck, so your one attachment for the turn is free to go on Munkidori. Strong players treat this as compulsory: across 145 winning games with our exact 60 cards, Munkidori was benched and given Energy in all 145, at a median of turn 2. Twelve slots exist only to find that line: 4 Spikemuth Gym (スパイクタウンジム), 4 Team Rocket's Petrel (ロケット団のラムダ), 3 Rare Candy (ふしぎなアメ), 1 Dawn (ヒカリ). Grimmsnarl ex gives up two Prize cards when it falls, so the plan is three Knock Outs from behind a 320 HP attacker the format needs two turns to remove.

**Where the engine becomes a liability.** Marnie's Grimmsnarl ex is {D} with Weakness to {G}, and **Teal Mask Ogerpon ex (オーガポン みどりのめんex)** attacks with Myriad Leaf Shower, 30 damage plus 30 for each Energy attached to *both* Active Pokémon. Five Energy between them is 180, and Weakness doubles that to 360 against our 320 HP. Shadow Bullet supplies two of those five itself, so the counter only has to bring three. The acceleration that makes our deck fast is what puts it inside a one-shot. We never spotted it. Two independent measurements agree on the size of the hole: [kiyomiya-k](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/737125), who built the deck that punishes it, went 95% over 222 games, and a [post-deadline survey](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/737107) of 23,313 ladder games puts Ogerpon at 87% against us over 69. The pilot fixes decisions, but only the deck fixes arithmetic.

---

## 2. The agent: imitate the right teachers, then bend the sample

The submission runs as pure Python with no numpy, so a large neural policy was never an option, and the ladder is live, so the opponents you tune against are not the ones you are scored against. We chose imitation learning: the daily episode dumps hold thousands of games by players rated above 1000, and a model of which option they chose is cheap to train, cheap to run, and deterministic.

**Corpus.** We keep only the winning side of games whose 60 cards match our list exactly. A corpus that accepted any Grimmsnarl variant reached higher held-out accuracy (top-k 0.684 → 0.798) but lost head-to-head against our shipped build (0.510 → 0.315). It had learned, faithfully, to pilot somebody else's deck.

**Model.** A gradient-boosted ranker scores every legal option, with a separate model per decision context. Features are written in a player's vocabulary rather than as card indices: Prize cards left on each side, Knock Outs still needed to close, Energy attached against Energy required, and the Prize cards our own Bench is offering.

**What we tested.** Figure 5 is the ledger: eight corpus sizes, five feature sets, five rival decks, two search variants, and one change that cleared our own bar. What worked was not more data, more features or a bigger model, but reweighting the training rows by the opponent archetype each decision was played against, which lifts the matchups we lose. The weighting has an interior optimum: past about a 15% effective share, that matchup keeps improving while the overall score falls. We shipped the interior point. The ladder cannot confirm the gain either — our two eligible submissions differ only in these weights and sit 99 points apart (§3.1).

---

## 3. Why testing lies: three error terms, and we removed the wrong one

Every offline decision went through one instrument, a weighted win rate against a fixed pool of six opponents, and it never predicted the ladder. Taking it apart gives three error terms.

**3.1 Variance: draws and mulligans.** Results here are dominated by opening hands, so a gauntlet number moves when nothing has changed. We patched one engine function so the shuffle seed can be set from outside, then gave both seat orderings of a matchup the same seed. Over six repeats the variance of the estimate fell 4.66×, buying the power of 1,000 games from about 220. The same term sits on the leaderboard, where nobody can touch it: kiyomiya-k submitted a byte-identical tarball seven times and scored between 687 and 856, an sd of 51. Every rank there, ours included, is a sample from a distribution that wide.

**3.2 Bias: the practice partners are not the opponents.** Three days of ladder replays, 6,292 games, let us measure the matchups the gauntlet claimed to cover using our exact 60 cards (Figure 1). Every one was overstated. Dragapult ex (ドラパルトex): 0.865 predicted against 0.341 actual (n=264). Alakazam-type (フーディン): 0.864 against 0.421 (n=183). ex-beatdown had no cell in the gauntlet at all, was 27.3% of the field, and held us to 0.193. Weighted by what we faced, our win rate was 0.33.

The cause is structural. Those opponents were clones we had built, and a deck piloted by the person who copied it is weaker than the same deck in the hands of someone who plays it. That error does not shrink as you add games, and it lands on every candidate about equally, so the ranking stays stable and the instrument never signals that it is wrong. The one signal that could have caught it gave us n=4–14.

Our other internal metric was no better: held-out imitation accuracy selected a different model than the gauntlet did (Figure 2), and the smallest corpus scored almost as well as one six times its size.

**3.3 Drift: the format rotates underneath the instrument.** Holding our agent fixed and changing only the composition of the metagame between 2026-08-09 and 08-15, its expected win rate falls from 0.415 to 0.334, about 60 rating points (Figure 3). An evaluation result without a date on it does not reproduce.

**3.4 A better gauntlet was never the answer.** Technique can remove the variance. Nothing removes the bias except opponents you did not choose yourself: a growing pool of other people's bots, scored by relative rating, which is what the teams above us built. [Abhyuday](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/735649) could estimate his true ladder rating to within ±30 in the half hour after submitting. We built a careful version of the wrong measurement.

---

## 4. Consistency, and what the agent does not lean on

An agent can be fragile here in three ways: needing a good opening hand, being tuned until it only beats one archetype, or playing the same position differently on different days.

**The opening hand.** The line the deck needs — Munkidori benched with a Darkness Energy — is not a lucky draw; it is what the twelve search slots are for. Our agent completes it in 40 games of 40, at the same median turn as the 145 winning human seats.

**One matchup.** The row weighting in §2 stops at its interior optimum, not at the peak of the matchup it was aimed at: we took the smaller total gain deliberately.

**The agent itself.** The ranker takes the argmax, so the same position always plays the same way and repeated matches differ only in the deal. That is also what made the paired-seed measurement in §3.1 possible.

A stable *rank* is another matter, and we cannot claim one: ours moved 99 points between two builds that differ only in training weights, and identical tarballs span 687 to 856. Nobody here can promise a repeatable rank — only a deterministic agent, and an honest account of how wide the spread around its score is.

**Failing loudly.** The failure that hurts most is the one that looks like an ordinary loss. Our agent catches every exception and falls back to a legal move, so a broken model plays a full, quiet, losing game and reports no errors. That caught us out six times. The guards are cheap: assert the model loaded, require zero fallbacks in the smoke test, require a minimum smoke win rate. Every experiment records its seed, git SHA and config hash, and the shipped artifact makes about 197 decisions per game, worst move 1.28 s, with no validation errors on the ladder.

---

## 5. What it cost, and what the top did differently

We considered changing decks three times and rejected it three times, each time through an instrument built around the deck we already had.

There was another way to decide, and we had used it once. In July the #1 player abandoned his archetype for this one, so we read 1,000 of his replays and followed him. [Anil Ozturk](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/736121) did the same in August, switching after he saw 9 of the top 12 teams on Dragapult ex (ドラパルトex). No local evaluation was involved. We had the same observation and ran it through the broken instrument instead.

The deck was not the whole problem. Restricted to opponents within 50 rating points, that post-deadline survey puts Grimmsnarl at 48.0% — more survivable than our 0.33 suggested. But the same #1 player beat Dragapult ex 0.92 of the time with our exact 60 cards, where we managed 0.341. The deck had one structural hole we never saw, and the rest of the gap was piloting.

We also told ourselves that PPO plateaus in this game. It plateaus at our throughput: [rick](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle/discussion/738158) reached 1132 with a 12M-parameter transformer on one RTX 3090, having rebuilt the environment in C++ to run 30 games a second where we drove the binary one game at a time. Ozturk's value-head numbers also explain our two failed search experiments: a head trained by imitation has only seen expert positions, and search asks it to judge positions that are not (−20 to −30 rating cloned, +50 to +70 on-policy).

---

## Conclusion

We tuned the policy carefully and measured it carelessly, and the measurement decided where we finished. Given the same two months again we would spend the first week building the evaluation instead of the agent: an arena of every bot we and other people have produced, scored by relative rating, so that a candidate is always ranked against opponents we did not pick.
