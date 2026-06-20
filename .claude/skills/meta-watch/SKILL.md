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
   - **Rotation detected:** identify the rising archetype and whether our agents beat
     it. The meta is a rock-paper-scissors (ex-beatdown → anti-ex wall → non-ex
     attackers → …) that converges; see [[meta-and-leaderboard]].

4. **(Optional) scout the top** to see what new top decks look like:
   ```
   uv run python top_meta.py <top_player_submission_id> <tag>
   ```
   Find a top player's submission_id by traversing episodes (their `submission_id`
   appears as an opponent in our / another player's episodes; cross-ref names with
   `kaggle competitions leaderboard pokemon-tcg-ai-battle --show`). To copy a top
   deck, use the `/extract-deck` skill; to build+submit a counter, use `/build-submit`.

5. **Report** the meta table, rotation verdict, and a recommendation (hold vs build a
   counter). Don't submit anything here — that's `/build-submit`, after user approval.

## Notes
- Needs Kaggle API auth + the cabt engine (via `uv run`).
- Snapshots accumulate in `workspace/exp011_meta_watch/results/meta_*.json`; the diff
  uses the most recent prior one.
