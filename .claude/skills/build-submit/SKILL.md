---
name: build-submit
description: Build a PTCG Simulation submission (.tar.gz) from a deck + policy, validate its structure, smoke-test the built artifact vs the meta gauntlet, then (after user approval) submit and record it. Use to build/package/submit an agent or ship a counter deck. Triggers — "提出物をビルド", "これを提出", "build a submission", "submit this deck/agent".
---

# Build, validate, smoke-test, submit

Codifies the CLAUDE.md submission checklist end-to-end. Pairs with `/extract-deck`
(copy a deck) and `/meta-watch` (decide what to counter).

## Steps

1. **Gather inputs:**
   - `--deck` : a 60-card JSON (e.g. from `/extract-deck`, like `workspace/exp012_nonex/charmq_deck.json`).
   - `--policy` : a base policy `.py` (default `workspace/exp002_baselines/policies/lucario_v2.py`,
     which has piloted foreign decks well — Crustle, non-ex).
   - `--patch` (optional) : a `.py` exposing `PATCH_SRC` (text appended after the class
     to override methods, e.g. `workspace/exp012_nonex/nonex_policy.py` for the non-ex
     attack model) — use when the deck needs dedicated piloting (mirror, etc.).

2. **Build + validate + smoke-test** (one command):
   ```
   uv run python scripts/build_submission.py \
       --deck <deck.json> --policy <policy.py> --out workspace/expNNN/build_vNNN [--patch <patch.py>]
   ```
   It writes `main.py` (top-level) + `deck.csv` + `cg/` into `submission.tar.gz`,
   asserts the tar structure, and **smoke-tests the BUILT artifact** (the real main.py,
   not the dev policy) vs lucario_v2 / Crustle / dragapult with the exp001 harness.

3. **Check the smoke output.** Require **0 errors** (crash-safety must hold). Sanity-check
   the winrates against expectation (e.g. a non-ex deck should beat ex/Crustle, lose to
   dragapult). If errors appear or winrates look wrong, fix before submitting. For a
   deeper read, run the relevant `workspace/exp012_nonex/test_*.py` matchup eval.

4. **Decide the eligible pair.** Submitting makes this the newest; **eligible = latest 2
   by time**. Confirm which existing submission gets evicted and that the resulting pair
   is the intended hedge. Check current state: `kaggle competitions submissions pokemon-tcg-ai-battle`.

5. **Get explicit user approval** (real Kaggle uploads need it — CLAUDE.md). Then submit:
   ```
   kaggle competitions submit -c pokemon-tcg-ai-battle -f <build_dir>/submission.tar.gz -m "<vNNN: concise what+why>"
   ```

6. **Record** (always, after submitting):
   - `uv run python scripts/record_submission.py --version vNNN --source-experiment expNNN ...`
   - add a human row to `submit/SUBMISSIONS.md`
   - update [[meta-and-leaderboard]] memory if the meta/strategy state changed.

## Notes
- **Env-gated patch flags are baked at BUILD time.** The current chain
  (`exp023_revenge/revenge_policy.py`, wrapped by `exp035_turnbeam` = v014) assembles
  `PATCH_SRC` at import from env vars (`REVENGE_BONUS`, `BENCH_DISC`, ...). Set them
  on the build command line (e.g. `REVENGE_BONUS=50 uv run python scripts/build_submission.py ...`)
  and record the flag values in `submit/SUBMISSIONS.md`; a build with defaults silently
  omits the tuned behavior.
- A persistent per-experiment `build_vNNN.py` is optional; this generic builder covers
  base-policy / patched-policy / arbitrary-deck cases. Keep heavy `.tar.gz` out of git.
- The generic `lucario_v2` policy is a strong default pilot; only add `--patch` when a
  matchup (esp. the mirror) needs dedicated knowledge. A targeted patch beats a full
  rewrite (the from-scratch v005 Crustle policy lost to the generic-piloted v004).
