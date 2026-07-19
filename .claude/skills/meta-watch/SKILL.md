---
name: meta-watch
description: Weekly PTCG ladder meta check — analyze our latest submission's replays for opponent-archetype W-L and meta share, flag rotations vs the last snapshot, show the LB top. Use to check the meta, our submission's record, or whether the meta rotated. Triggers — "メタ確認", "メタ回転した?", "今の戦績", "weekly meta check", "what are we facing".
---

# Weekly meta-watch

One command for the operational loop: *check the meta → if it rotated, counter (`/build-submit`); else hold.*

## Steps

1. **Run the watcher** (auto-detects our latest scored submission; downloads its
   ladder replays — cached under `references/raw/replays/`, gitignored):
   ```
   cd workspace/exp011_meta_watch
   uv run python meta_watch.py            # or: meta_watch.py <submission_id>
   ```
   It prints: opponent-archetype W-L + meta share, a **rotation diff vs the previous
   snapshot** (flags any archetype whose share moved ≥15%), and the LB top 8.

2. **Mind the sample size.** If the latest submission has < ~15 games it says so —
   rotation flags are unreliable on a fresh (μ600, few-game) submission. Re-run later,
   or pass a more-converged `submission_id` (see `kaggle competitions submissions
   pokemon-tcg-ai-battle`). Our **eligible pair = latest 2 submissions by time**.

3. **Interpret & decide:**
   - **No rotation (< 15% share change):** hold / monitor. Note our W-L per archetype
     (are our eligible agents still favored vs the field?).
   - **Rotation detected — first ask: temporal rotation, or ALTITUDE?** (learned 07-14)
     The opponent mix changes with OUR rating: a submission that climbs 700→940 sees a
     different band (e.g. crustle 20%→0%, archaludon 9%→45%) with zero temporal rotation.
     If our rating moved a lot between snapshots, read the "rotation" as band change and
     compare against the matching band pool (exp053/054), not the previous snapshot.
   - **Real rotation:** identify the rising archetype and whether our agents beat it.
     The meta is a rock-paper-scissors (ex-beatdown → anti-ex wall → non-ex attackers →…);
     see [[meta-and-leaderboard]].

3b. **Contingency triggers (for the LO line, v021+; set 07-14).** Check these shares at
   OUR altitude every run; below threshold = hold:
   - **non-ex aggro (e.g. Team Rocket's Spidops) > 20-25%** (raised 07-19 by exp062;
     was 10-15%, and 11% was REACHED on 07-19 with koff 0/6 live) — LO's structural
     weakness class: non-ex attackers bypass BOTH Crustle Safeguard and Neutralization
     Zone (each blocks only ex attacks) and win the prize race. Below the raised
     threshold the v020 swap is EV-NEGATIVE: v020 fixes the TR lane (floor 0.955) but
     bleeds the 53% mainstream (archaludon mirror 0.500 / alakazam_dun 0.610, silver
     weighted 0.634 vs koff 0.786; each +10% Spidops share closes ~0.09 of that gap).
   - **crustle/LO bucket > 20%** (was ~7%) — mirror saturation / anti-LO rising.
   - **Starmie-type any clear rise** (was ~0%) — flagged wall/LO killer (pilkwang).
   Ready fallback if triggered: v020 Archaludon — REBUILD with the updated cg first
     (disc727094 engine fix, 07-17; old build bundles the pre-fix engine).
   Counter-deck pre-building was measured and declined (dragapult 0.567 / wall 0.438
   silver-band as solo candidates vs v023's 0.792).

3c. **Reroll check (best-of-2 ops; set 07-14, CONSTRAINT found 07-15).** LB = max of the
   2 eligible submissions' INDEPENDENT ratings (complementarity is impossible), and
   byte-identical agents settle up to ~400 pts apart (disc712621; our own live demo:
   identical koff builds at 927 vs 709). Keep TWO copies of the strongest build eligible;
   when a slot settled clearly below the other (≥100 pts, ≥~30-50 games), reroll it by
   resubmitting the strongest build. **HARD CONSTRAINT: a new submission always evicts
   the OLDER eligible slot (latest-2-by-time), so you can only ever reroll the older one.
   If the older slot currently holds the HIGH rating, submitting ANYTHING sacrifices it —
   do not submit; wait until the newer slot overtakes the older.** Repeat until the
   final-submission target (8/2). Also: the silver cut DRIFTS over time (930.2→919.4
   over 07-15→07-17; direction varies with team influx) — aim for margin above the cut,
   not touching it.
   **Matchmaker mechanics are now OFFICIAL (staff, disc726690 — full notes in
   references/knowledge/matchmaker_mechanics_0717.md): scheduling priority = sigma +
   staleness, SCALED by rating (up to ~8x vs mu600) and new submissions heavily
   prioritized; opponents sampled from a Gaussian window around own rating (band meta
   confirmed). Consequence: a ticket's draw quality LOCKS IN early (path-dependent
   loop: early wins at high sigma → 8x more games → fast sigma shrink at the high
   rating). JUDGE REROLLS AT DAY 1-2 (<~800 = lagging, redraw when the eviction
   constraint allows) instead of waiting 2-3 days. Also: the FINAL evaluation phase
   keeps generating episodes (sigma-reduction goal) — lucky-high slots may partially
   wash out, so for the FINAL pair prefer true build strength over a lucky draw.**
   Medal-cut recheck when top compresses:
   `kaggle competitions leaderboard pokemon-tcg-ai-battle --download` → silver = score at
   rank ceil(0.05·N), bronze at ceil(0.10·N).

4. **(Optional) scout the top** to see what new top decks look like:
   ```
   uv run python top_meta.py <top_player_submission_id> <tag>
   ```
   Find a top player's submission_id by traversing episodes (their `submission_id`
   appears as an opponent in our / another player's episodes; cross-ref names with
   `kaggle competitions leaderboard pokemon-tcg-ai-battle --show`). To copy a top
   deck, use the `/extract-deck` skill; to build+submit a counter, use `/build-submit`.

4b. **(Optional) scout a top PILOT's decisions** (piloting is the #1 lever; same deck,
   +200 LB). After caching a pilot's replays (step 4 / `top_meta.py`), find where their
   play differs from ours:
   ```
   cd workspace/exp022_megastarmie
   uv run python pilot_gap_scan.py <replay_dir> <name_substring> [extra_card_ids...]
   # e.g. pilot_gap_scan.py top_mogja_j_0624 Mogja      (our non-ex deck pilot)
   #      pilot_gap_scan.py 0625_54022035 Morita        (our own agent, for comparison)
   ```
   It prints per-decision (length-normalized) action rates split W/L, plus a
   **take-when-legal** table. **Interpretation rule (learned exp022):** compare the top
   pilot to *our own* scan.
   - **Big exposure gap + matching take-when-legal rate** = a *draw/throughput/game-length*
     gap, NOT a patchable decision — single-card rules won't help (don't build one).
   - **Normal exposure but we take it far less when legal** = a real *gated decision leak*
     — the gust template (Boss's Orders, gated by `plan.target>=1`). Worth a single fix.
   - The single-card-leak class is currently **exhausted** for our non-ex deck (take-when-
     legal matches Mogja); see [[meta-and-leaderboard]]. Re-scan only after the deck/meta
     shifts.

5. **Report** the meta table, rotation verdict, and a recommendation (hold vs build a
   counter). Don't submit anything here — that's `/build-submit`, after user approval.

## Notes
- Needs Kaggle API auth + the cabt engine (via `uv run`).
- Snapshots accumulate in `workspace/exp011_meta_watch/results/meta_*.json`; the diff
  uses the most recent prior one.
