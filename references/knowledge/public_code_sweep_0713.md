# Public Kaggle Code sweep (0713, via nvidia-kaggle-skill kernel_ingest/query/read/archive)

Ingested 100 kernels for `pokemon-tcg-ai-battle` (sorted by voteCount), cross-checked
against what we already knew (Alakazam 5th place, "A Sample Archaludon" = our v020
source, "Prize Card Tracking Starmie", "en-replay-archetype-analysis" = our
fine_classify.py source, "I have one REAR card" = our lo_mill_notebook_0702.md).
Read the highest-value NEW ones below.

## pilkwang/pok-mon-tcg-ai-battle-meta-snapshot-* (147 votes, recurring daily series)
An independent, large-sample (thousands of games/day from official replay dumps,
much bigger N than our own per-submission `/meta-watch`) daily meta-tracker +
candidate-agent-builder notebook, re-run/re-titled almost daily (fetched the
latest version as of 07-09, window 07-01→07-08; an earlier archived version
covered 06-29→07-03).

Key independently-observed facts:
- **Archetype shares genuinely oscillate week to week**: Marnie/Munkidori went
  from ~1% (06-29) to ~18-21% (07-01→07-03) then faded; **Archaludon was the
  dominant field mass through 07-01→07-03, then "collapsed... fell from the
  largest archetype to a small slice by 07-03."** Our own 07-12 meta-watch shows
  Archaludon/mixed_ex4 back at 16% share and beating everyone — so between this
  notebook's window (07-08) and our 07-12 read, Archaludon **resurged**. This is
  independent, large-N confirmation that the meta genuinely rotates on a ~1-week
  cadence (consistent with CLAUDE.md's framing), not just noise in our smaller
  samples — reinforces continued `/meta-watch` cadence rather than assuming any
  snapshot (including our own) is stable for long.
- **Alakazam: large population share, but "size is not strength" — score rate
  stays modest.** Consistent with our own read (Alakazam is not a top threat to
  either v019 or v020).
- **Crustle-type walls have a sharp, repeatable counter: Starmie.** "Starmie
  beats Crustle hard in the latest log slice" and is called out as "the main
  warning sign for polarized control complements" in both snapshot versions we
  read. Also **Cynthia/Gible "crushes Crustle."** Relevant context (not new
  action) since we no longer run a Crustle/wall deck (v016 dropped 07-12), but
  useful vocabulary/citation for the Strategy report's meta-rotation section,
  and a reason NOT to reintroduce a pure wall deck as a hedge.
- Their own methodology explicitly flags the same CRN gap PokéForge (disc724187)
  raised: "The public engine is effectively unseeded through its exposed API,
  so the complement view is an opponent-slice proxy rather than
  common-random-number paired evidence" — a second independent team naming the
  same missing tool, worth weighting the CRN-spike idea a bit higher.
- Practical framing worth borrowing for our own daily reports: they explicitly
  caveat "a low live result is a calibration warning, not a permanent verdict"
  — i.e. don't overreact to one submission's early LB swing (same lesson as
  disc712621, independently arrived at from the builder's side this time).

## dashimaki360/beating-the-day-1-1-crustle-bot (81 votes)
Reveals the actual source of the original day-1 #1 Crustle-wall agent: a
**trivial flat action-type-priority scorer** (ATTACH 1000 > EVOLVE 800 > PLAY
600 > ABILITY 400 > ATTACK 100 > RETREAT -1) with only ~4 card-specific special
cases (Hero's Cape always-attach-to-active +2100; heal cards gated on
"actually damaged"; Cheren draw; Battle Cage stadium). No search, no per-matchup
logic. The deck (Safeguard wall) did the real work; the pilot just had to not
waste turns. **Direct corroboration of our own 06-24 finding** ("simpler pilot
> sophisticated pilot" — v006 generic beat v007-v009's added sophistication on
the live ladder) and of disc724187's "local patches to already-tuned/simple
policies rarely help" pattern — a third independent data point for the
Strategy report's "piloting complexity has diminishing/negative returns past a
point" thread.

## soutasakurai/max-elo-1208-libraryout-w-crustle-great-tusk (7 votes)
A rougher, self-admittedly-unfinished variant of the SAME archetype family as
our already-known `lo_mill_notebook_0702.md` ("I have one REAR card", 1083.6,
Great Tusk mill + Crustle wall + Terrakion backup + Explorer's Guidance mill
acceleration). Author flags the same weaknesses we already know (loses to a
fully-set-up Lucario, self-deck-out risk) plus, per the pilkwang snapshot
above, this whole archetype family is checked hard by Starmie. Low marginal
new information — logged for completeness, no action.

## busyaprime/what-actually-wins-on-the-ladder (3 votes)
A well-built from-scratch episode-log parser (labels each side by its highest-
HP ex "ace", builds a Wilson-bounded tier list + matchup grid straight from raw
JSON, no pasted numbers). Methodologically clean and matches the spirit of our
own `fine_classify.py`/`top_meta.py`/`analyze_adaptation.py` tooling; didn't
surface a technique or finding beyond what our own tools already give us, but
confirms our archetype-by-ace-Pokemon labeling approach is a reasonable,
independently-converged-upon convention.

## Not read in depth (lower expected value given time budget)
`aristophanivan/multiply-agent-best-940-lb`, `aristophanivan/probability-agent`,
`kokinnwakashuu/ptcg-lucario-public-lab-anti-crustle-log` (+ `ptcg-diary-day4`),
`romanrozen/strong-start-baseline-agent-v10-lb-950`, `niiino/card2vec-learning-
dense-card-embeddings`, `avikdas567/ptcg-ai-battle-heuristic-agent-data-
pipeline`, `nursrijan/pok-mon-tcg-advanced-heuristic-planning-agent`,
`takusid/pok-mon-tcg-ai-battle-top-50-deck-database`, `zoli800/top-dragapult-
ex-tempo-control-agent`. Revisit if a specific need arises (e.g. card2vec if we
ever redo the encoder; top-50 deck database if the local eval pool needs more
variety again).
