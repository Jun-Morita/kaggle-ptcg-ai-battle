---
name: extract-deck
description: Reconstruct a player's exact 60-card PTCG decklist from their Kaggle ladder replays (any submission_id → deck JSON). Use to copy/clone/mimic a top-ranker's or opponent's deck, or seed a counter. Triggers — "copy charmq's deck", "リプレイから60枚を複製", "clone sub <id>", "extract the top player's decklist".
---

# Extract a deck from replays

Given a Kaggle **submission_id**, download that submission's ladder replays and
reconstruct the owner's MAIN deck (= the most frequent exact 60-card list across
their games) as a JSON ready for a build. Works for any submission_id — ours or a
rival's reached by traversing episodes.

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
   breakdown (the script asserts it sums to 60).

4. **(Optional) turn it into a submission** with the `/build-submit` skill (deck JSON
   → tar.gz → smoke-test → submit after approval).

## Notes
- Needs Kaggle API auth + the cabt engine; run via `uv run`.
- The generic `lucario_v2` policy has piloted foreign decks well (Crustle v004, non-ex
  v006) — try it first; add a dedicated policy patch only if the mirror/a matchup needs it.
- A copied deck is only as good as its pilot — validate with `/build-submit`'s smoke test
  before trusting it.
