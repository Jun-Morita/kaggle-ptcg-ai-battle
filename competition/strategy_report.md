# Sparring Partners
### Why our offline testing never predicted the ladder — and the one error term we could not remove

*Strategy Writeup — Pokémon TCG AI Battle Challenge · Team Morita*

---

## Abstract

Our agent imitates strong play of **Marnie's Grimmsnarl ex** with a gradient-boosted
ranker over legal options, finishing the Simulation track around **rank 430 of
6,809** (top 7%). This report is about what decided that number: **our testing.** Offline evaluation in a live-ladder card game fails
in three separable ways, and we measured all three. We removed the one that
responds to effort — draw variance, cut **4.66x** by seeding both halves of a
paired match identically — and then shipped for a week against the one that does
not: a pool of sparring partners we had built ourselves, which overstated **every**
matchup, by up to 0.52, and had no entry for 27% of the field. A third term,
metagame drift, moved a frozen agent **60 rating points** in six days. The
conclusion is not a better gauntlet: a fixed opponent pool applies the same bias to
every candidate, so the ranking stays stable and the instrument never reports that
it is wrong.

---

## 1. What we built

Two constraints shape everything. The submission runs as **pure Python with no
numpy**, which rules out a large neural policy at inference time; and the
leaderboard is **live**, so the field you tuned against is not the field you are
scored against.

We therefore chose imitation over reinforcement learning. The official daily
episode dumps hold thousands of games by players rated above 1000, and a ranker
that learns which option those players took is cheap to train, cheap to run and
deterministic. We logged 78 submissions; the last two differ only in how the
training rows were weighted.

---

## 2. The Deck: one ability solves both Stage-2 problems

We played **Marnie's Grimmsnarl ex (マリィのオーロンゲex)**, the most-played
archetype on the ladder. Stage 2 decks normally pay twice: slow to assemble, slow
to power up. This one pays once, because a single ability answers the second
problem outright.

**Punk Up (パンクアップ).** On evolving, Grimmsnarl ex searches the deck for up to
**5 Basic Darkness Energy** and attaches them across your Marnie's Pokémon. The
turn you complete the line you are also fully powered, and the board keeps that
energy through a knockout. This is why a Stage 2 attacker runs 10 Energy.

**Shadow Bullet (シャドーバレット)**, {D}{D} for **180 plus 30 to a Benched
Pokémon**, is the other half. 180 answers almost everything in two hits; the 30 is
what turns a beatdown into a math problem for the opponent.

**Damage relocation is the real engine.** *Freezing Shroud* on **Froslass
(ユキメノコ)** puts a damage counter on every Pokémon with an Ability during
Checkup, both sides; *Adrena-Brain* on **Munkidori (マシマシラ)** then moves up to
3 counters from one of our Pokémon to one of theirs. Froslass damages our own
board too, Grimmsnarl ex included, and Munkidori exports exactly that back onto
the bench where Shadow Bullet already left 30.

**The energy budget links the two abilities** (Figure 4). Adrena-Brain needs {D} Energy on
Munkidori, and Punk Up cannot supply it — it attaches only to *Marnie's* Pokémon.
But because Punk Up pays the attacker out of the deck, the one manual attachment
per turn is freed entirely for Munkidori. That is not a flex slot, it is the line:
across **145 winning seats on our exact 60 cards**, Munkidori was benched and
energised in **145 of 145**, median **turn 2** — identically for teachers rated
1001 and 1120. Our agent reproduces it in 40 of 40 games.

**Consistency is bought, not hoped for.** Twelve slots exist only to assemble the
line: 4 Spikemuth Gym (スパイクタウンジム, tutors a Marnie's Pokémon every turn),
4 Team Rocket's Petrel (any Trainer), 3 Rare Candy, 1 Dawn (Basic, Stage 1 and
Stage 2 in one card). Grimmsnarl ex gives up 2 prizes, so the plan is three
knockouts behind a 320 HP body the field needs two turns to remove.

---

## 3. Method: imitate the right teachers, then bend the sample

**Corpus.** From the official daily episode dumps we keep only *winning* seats
whose 60 cards match our list exactly. The exactness filter matters more than
volume: an earlier corpus that accepted any Grimmsnarl variant reached a higher
held-out accuracy (top-k 0.684 -> 0.798) while losing head-to-head against our own
shipped build (0.510 -> 0.315). It had faithfully learned to pilot somebody else's
deck. Fidelity to the wrong teacher is worse than less data.

**Model.** A gradient-boosted ranker scores every legal option, with a separate
model per decision context (playing cards, choosing search targets, picking attack
targets). Features are written in a player's vocabulary rather than card indices:
prizes remaining on each side, how many knockouts still close the game, energy
attached versus required, whether an attack is lethal now, bench liability (prizes
our own bench is offering), and counts of the opponent's cards not yet seen. It
ships as inlined pure Python, 5.1 MB, no numpy in the sandbox.

**The one intervention that worked.** Not more data, not more features, not a
bigger model; all of those failed repeatedly. What beat our own bar was
*reweighting rows by the opponent archetype they were played against*, lifting the
matchups we lose. It has an interior optimum: past roughly a 15% effective share,
the boosted matchup keeps improving while the overall score falls.

---

## 4. Why testing lies: three error terms, and we killed the wrong one

Every offline judgement we made ran through one instrument: a weighted win rate
against a fixed pool of six opponents. It never predicted the ladder. Taking it
apart gives three separable error terms, and we had measured only one.

**4.1 Variance — draws and mulligans. Solved, cheaply.**
Outcomes are dominated by opening hands, so a gauntlet result moves when nothing
changed. We patched one engine function so the shuffle seed could be set from
outside, then paired every swapped-seat game to the same seed: both orderings of a
matchup see the same deal. Over six repeats the variance of the estimate fell
**4.66×** — the power of n≈1000 games from n≈220. This term responds to effort.

**4.2 Systematic error — the sparring partners are not the opponents. Fatal.**
Three days of ladder replays (6,292 games) let us measure the same matchups our
gate claimed to cover, using our exact 60 cards. **Figure 1** puts the two side by
side. The gate overstated **every** matchup — Dragapult 0.865 against a real
**0.341** (n=264), Alakazam-type 0.864 against **0.421** (n=183) — and had no cell
at all for ex-beatdown, 27.3% of the field, where we win **0.193**. Field-weighted,
our true win rate was **0.33**.

The cause is structural. Those opponents were clones we built ourselves, and a deck
piloted by its copier is weaker than the same deck in the hands of someone who
plays it. **This error does not shrink with more games.** Worse, a fixed pool
applies the same bias to every candidate, so the ranking looks stable and never
reports that it is wrong. Our only calibration signal, real ladder games per
candidate, was n=4–14. We shipped against this gate for a week.

A second symptom followed. Our other internal metric — held-out imitation accuracy
— **selected a different model than the gate did** (Figure 2): across four corpus
sizes, the most accurate imitator was not the highest-scoring agent, and the
smallest corpus scored nearly as well on accuracy as one six times its size. A
smaller corpus also draws its held-out set from a narrower distribution, so it is
simply easier to predict. Two self-referential metrics that disagree, and nothing
external to adjudicate.

**4.3 Drift — the format rotates under the instrument.**
Hold the agent fixed and change only the field composition between 2026-08-09 and
08-15: expected win rate moves 0.415 → 0.334, about **60 rating points from the
metagame alone** (Figure 3). An evaluation result without a date does not reproduce.

**4.4 The fix is not a better gate.**
Variance yields to technique; bias only yields to opponents you did not choose. The
right instrument is a growing pool scored by relative rating — a top-30 competitor
reported estimating true ladder ELO to ±30 within 30 minutes of submitting, by
running every bot he had against every other. We built the statistically careful
version of the wrong measurement.

---

## 5. What that cost: the deck decision

We considered changing decks three times and rejected it three times, always
through an instrument biased toward the deck we already had: its opponents were our
own clones, its weights described the field as seen from our deck, its 361 features
were designed around our deck. A rival deck was measured with our handicap attached.

The alternative was available, and we had used it once already. In July we watched
the #1 player abandon his archetype for this one, confirmed it across 1,000 of his
replays, and followed him. A competitor who finished in silver did the same in
August: he had also started on Grimmsnarl because it has the most replay data, then
looked at the top 12 teams, found 9 on Dragapult, and switched — no local
evaluation involved.

We had the same observation and fed it into the broken instrument instead. What we
still cannot say is whether the answer was a different deck or a better pilot: that
same #1 player beat Dragapult 0.92 with *our exact 60 cards* while we managed
0.341. Our instrument could not separate the two, which is the point.

---

## 6. What the top of the ladder did differently

Post-deadline write-ups make the gap concrete.

**Compute.** The winning-tier pipeline was behaviour cloning then PPO with
per-deck specialists, at **117M parameters over 1.68 billion environment steps**.
We had one desktop GPU. Skipping reinforcement learning was right for our budget,
but our stated reason — that PPO plateaus here — was wrong. It plateaus at our
scale.

**Transfer.** Our clones of other decks were all weak, and we correctly diagnosed
that as representation rather than data volume. We missed the fix: the
silver-finishing competitor trained **one portfolio model across ten archetypes**
and fine-tuned each specialist off it. We trained every clone from scratch on its
own thin corpus.

**Why our search experiments failed.** We twice measured that lookahead made the
agent *worse* and closed the lane. The published reason: a value head trained by
imitation has only seen expert states, and search is exactly the request to
evaluate states outside that distribution — **-20 to -30 rating with a cloned value
head, +50 to +70 with an on-policy one.** Search was gated on the reinforcement
learning we could not afford, not on search.

---

## 7. Robustness and operations

The dangerous failure in an agent competition is not a crash but a crash that
looks like a loss. Our agent catches every exception and falls back to a legal
move, so a broken model plays a full, quiet, losing game and reports zero errors.
This bit us **six times**. The guards that caught it belong on day one: assert the
model object loaded, require zero fallbacks, and — after a build shipped a stale
model and still passed — require a **minimum smoke win rate**, since a build losing
0–25 to a weak opponent is broken, not weak. It is not a beginner's problem: one
top team found after the deadline that their eight-checkpoint specialist had
shipped with the wrong decklist.

The artifact makes ~197 decisions per game, worst observed move 1.28 s, and
finished its ladder games with no validation errors.

---

## Conclusion

We tuned a policy carefully and measured it carelessly, and the second one
decided the outcome. Given the same two months again, we would spend the first
week building the evaluation instead of the agent: an arena of every bot we and
others have produced, scored by relative rating, so that a new candidate is
ranked against opponents we did not choose. Everything else we tried — more data,
more features, a bigger model, deeper search — was answered by that instrument
before it was answered by the game.

---

## Figures

1. `fig1_gate_vs_ladder.png` — what the gate predicted vs the real ladder, per archetype, ordered by field share.
2. `fig2_metrics_disagree.png` — held-out imitation accuracy and gate score select different models.
3. `fig3_drift.png` — the field rotates in one week; a frozen agent loses 60 rating points.
4. `fig4_deck_plan.png` — the deck's game plan as a mechanism: one ability pays the energy, two do the math.
