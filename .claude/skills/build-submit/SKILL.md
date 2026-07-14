---
name: build-submit
description: Build a PTCG Simulation submission (.tar.gz) from a deck + policy, validate its structure, smoke-test the built artifact vs the meta gauntlet, then (after user approval) submit and record it. Use to build/package/submit an agent or ship a counter deck. Triggers — "提出物をビルド", "これを提出", "build a submission", "submit this deck/agent".
---

# Build, validate, smoke-test, submit

Codifies the CLAUDE.md submission checklist end-to-end. Pairs with `/extract-deck`
(copy a deck) and `/meta-watch` (decide what to counter).

## Current strongest build (07-14, v023 line) — start here for LO rebuilds/rerolls

```
uv run python scripts/build_submission.py \
  --deck workspace/exp054_upperband/lo_deck.json \
  --policy workspace/exp053_bandpool/lo_opp/main.py \
  --patch workspace/exp054_upperband/patch_koff.txt \
  --out workspace/exp054_upperband/build_koff --smoke 30
```
(patch_koff.txt = `my_deck = read_deck_csv()` + the KO_OFF `should_ko_mode -> False`
override; tail redefinition works because main.py calls the predicate by global name.)
A byte-identical reroll needs NO rebuild — resubmit the existing
`build_koff/submission.tar.gz`. Gate results on record: silver-band 0.792 / our-band
0.648 (n=300 CRN), smoke 0 err, bare-exec replica 92 acts 0 err.

## Pilot-patch gate (standard pipeline, established exp054-B)

Any change to a tuned pilot must pass, in order:
1. **Instrument + counterfactual probe** (probe_arch.py pattern): measure the predicate's
   firing rate, then FORCE it on/off on shared CRN seeds. No counterfactual win = NO-GO
   (structural-void rule; probe_wall precedent).
2. **Both-band side-effect eval** (eval_ko_off.py pattern): n=300/matchup, CRN, all 9
   opponents, BOTH band weightings. Require: target matchup up with z≳3, no regression
   beyond noise, silver-band weighted up. (Trustworthy signals = ranking + deltas, NOT
   absolute Elo — pool opponents use our proxy pilots.)
3. **Built-artifact independent recheck** (n=200 CRN vs the 2 most-affected opponents) —
   confirms the patch survives the ship path.
4. Smoke + bare-exec replica (below), then user approval.

## Steps

1. **Gather inputs:**
   - `--deck` : a 60-card JSON (e.g. from `/extract-deck`, like `workspace/exp012_nonex/charmq_deck.json`).
   - `--policy` : a base policy `.py` (default `workspace/exp002_baselines/policies/lucario_v2.py`,
     which has piloted foreign decks well — Crustle, non-ex).
   - `--patch` (optional) : a `.py` exposing `PATCH_SRC` (text appended after the class
     to override methods, e.g. `workspace/exp012_nonex/nonex_policy.py` for the non-ex
     attack model) — or a `.txt` of raw source appended to main.py (patch_koff.txt style).

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

3b. **Sandbox-replica gate (v015 lesson, 2026-07-09/10 — 4 straight silent failures).**
   The harness smoke's win/error counts do NOT guarantee sandbox validation passes.
   Two distinct failure classes were found ONLY by replicating the real Kaggle loader
   exactly, not by the harness smoke:
   - **Per-act time**: all historically successful subs act in milliseconds; ~2.3s/act
     (pure-python MCTS sc16) failed validation (`Validation Episode failed` at ~125s).
   - **`__file__` is never defined** (the actual root cause of 4 straight ERRORs):
     `kaggle_environments.agent.get_last_callable` loads `main.py` via
     `exec(code_object, env)` on the raw SOURCE TEXT — this does NOT set `__file__`,
     unlike a normal `import` or `importlib.spec_from_file_location`. Any module-level
     code using `__file__` (e.g. to locate a bundled weights file) crashes at import,
     before `agent()` exists — invisible to any try/except inside `agent()`. Locate
     any bundled non-deck/non-cg file the same relative-path(+`/kaggle_simulations/agent/`
     fallback) way `deck.csv` already does; never touch `__file__` in `main.py`.
   For ANY agent beyond a trivial hand-written policy (esp. anything with extra bundled
   files or non-ms-per-act inference), run the sandbox replica before asking for approval:
   ```
   uv run python workspace/exp041_pilotnet/sandbox_replica.py <build_dir>/submission.tar.gz
   ```
   (extracts the tar, execs `main.py`'s source text in a bare namespace exactly like the
   real loader — no `__file__` — uses ONLY the shipped cg, full mirror self-play = the
   validation condition, prints per-act times). Require: import succeeds, game completes,
   max act well under 1s. If it still errors on Kaggle after this passes, download the
   failing episode's agent stderr logs before guessing again:
   ```python
   from kaggle.api.kaggle_api_extended import KaggleApi
   api = KaggleApi(); api.authenticate()
   api.competition_episode_agent_logs(episode_id, agent_index, path="/tmp", quiet=False)
   ```
   (find `episode_id` via `api.competition_list_episodes(submission_ref)`) — the actual
   traceback is far faster than another round of hypothesis-and-resubmit.

4. **Decide the eligible pair.** Submitting makes this the newest; **eligible = latest 2
   by time**. Confirm which existing submission gets evicted. **LB = max of the pair's
   INDEPENDENT ratings — matchup complementarity between the two slots is IMPOSSIBLE**
   (established 07-13), so "hedge pairs" are meaningless; the correct pair is two copies
   of the strongest single agent (reroll ops — see /meta-watch step 3c), or strongest +
   next candidate under live A/B. Check state: `kaggle competitions submissions pokemon-tcg-ai-battle`.

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
