---
name: extract-deck
description: Replicate a Pokémon TCG player's exact 60-card decklist from their Kaggle ladder replays. Use when the user wants to copy/clone/mimic a top-ranker's or opponent's deck, build a counter to a specific player, or turn a submission_id into a ready-to-use deck.csv. Triggers on requests like "copy charmq's deck", "リプレイから60枚を複製", "extract the top player's decklist", "clone sub <id>".
---

# Extract a deck from replays

Given a Kaggle **submission_id**, this skill downloads that submission's ladder
replays and reconstructs the owning player's exact 60-card decklist (their MAIN
deck = the most frequent 60-card list across their games), ready to drop into a
`deck.csv` / build script. Works for any submission_id — ours or a rival's that
we reached by traversing episodes.

## Steps

1. **Get the target submission_id.** If the user gave one, use it. Otherwise find
   it: it appears as an opponent's `submission_id` in any episode you can list.
   - From our submissions / a player we faced:
     ```
     uv run python -c "from kaggle.api.kaggle_api_extended import KaggleApi; a=KaggleApi(); a.authenticate(); \
       [print(x.submission_id, x.team_name) for e in a.competition_list_episodes(OUR_SUB_ID) for x in e.agents]"
     ```
   - To reach a higher-rated player, list one of *their* episodes (their
     `submission_id` from the step above) and read off their opponents. See
     `workspace/exp011_meta_watch/top_meta.py` for the traversal pattern.
   - Cross-reference team names with `kaggle competitions leaderboard pokemon-tcg-ai-battle --show`.

2. **Run the extractor** (replays are cached under `references/raw/replays/`, gitignored):
   ```
   cd workspace/exp011_meta_watch
   uv run python extract_deck.py <submission_id> [out.json]
   ```
   - Omit `out.json` to just print the decklist + archetype.
   - Pass an output path (e.g. `../exp012_nonex/<name>_deck.json`) to save the
     60-card-id JSON list for a build script.

3. **Report** the archetype label, ex-card count, and the Pokémon/Trainer/Energy
   breakdown. Sanity-check it sums to 60 (the script asserts this).

4. **(Optional) build a submission** from it: copy `workspace/exp012_nonex/build_v006.py`
   (generic-policy + crash-safety + deck.csv + cg/ → submission.tar.gz), point it
   at the saved deck JSON, smoke-test the built artifact vs the meta with the
   exp001 harness, then submit only after user approval (per CLAUDE.md).

## Notes
- Needs Kaggle API auth (already configured) and the cabt engine (`load_engine`
  from `workspace/exp001_harness`); run via `uv run`.
- The generic `lucario_v2` policy has piloted foreign decks well twice (Crustle
  v004, non-ex v006) — try it first; build a dedicated policy only if it fails.
- A copied deck is only as good as its pilot; always validate with the harness
  before trusting it, and check the archetype matches expectations.
