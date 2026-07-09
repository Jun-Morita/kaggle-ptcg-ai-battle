---
name: scout-top
description: Scout a top player's PLAYSTYLE (not just their deck) to find concrete policy-tuning targets — per opponent-archetype W-L / bench (prize-liability) / attack tempo, plus decoded decisions where OUR current policy diverges from theirs. Use to tune a policy, find why we lose a matchup, or learn what top players do that we don't. Triggers — "トップの打ち方を分析", "方策のチューニング標的", "なぜミラーで負ける", "scout a top player", "where does our policy diverge".
---

# Scout top playstyle → policy-tuning targets

The behavioral counterpart to `/meta-watch` (which finds *what* decks are played).
This finds *how* top players play and *where our policy differs* — the front-end that
produced the v009 discipline patch. Feeds `/build-submit` (test + ship the tweak).

Loop: `/meta-watch` (what) → **`/scout-top`** (how + our gap) → patch → `/build-submit` (test+ship).

## Steps

1. **Ensure the top player's replays are cached** (gitignored under
   `references/raw/replays/`). If not cached, download them:
   ```
   cd workspace/exp011_meta_watch
   uv run python top_meta.py <top_submission_id> <tag>     # -> top_<tag>/
   ```
   (Find a top sub_id via `/meta-watch`'s LB + traversing episodes; or reuse a
   cached tag: `diff_53858964`, `top_debauchery`, `top_tk`, `top_charmq`, ...)

2. **Behavioral gap, by opponent archetype** — does the top player adapt, and where
   do WE diverge? Pass OUR CURRENT policy to compare the right baseline:
   ```
   cd workspace/exp018_adaptive
   uv run python analyze_adaptation.py <sub_id> <deck.json> <cache_tag> [policy.py]
   # policy.py exposes make_agent(deck): exp013_router/router_policy.py = v008 (default),
   #                                     exp018_adaptive/discipline_policy.py = v009
   ```
   Prints per opponent-archetype: their W-L, avg bench (prize-liability), attack/turn
   (tempo), and **decision-match vs our policy**. Read it as:
   - A matchup where they win but we'd match them *least* = our biggest gap there.
   - bench/tempo shifts vs an archetype = an opponent-adaptive trigger worth copying.
   - **Uniformly low match across all matchups = a consistent style gap** (e.g. they
     bench fewer / hold resources), not opponent-switching — fix it globally.

3. **Decoded decisions** (what cards/choices differ), for the concrete patch.
   **Use policy_diff2 — it takes OUR CURRENT policy as the baseline.** The old
   `exp013_router/policy_diff.py` hardcodes v008 (router) as the comparison policy;
   in exp042 this nearly produced a wrong conclusion ("discipline is missing" when
   it was already in the v010+ chain). Env flags select the chain version:
   ```
   cd workspace/exp042_benchdisc
   REVENGE_BONUS=50 [BENCH_DISC=1] uv run python policy_diff2.py \
       <sub_id> <deck.json> <max_eps> ../exp023_revenge/revenge_policy.py
   ```
   Lists TO_HAND search targets they fetch vs we fetch, and top divergence examples
   decoded to card names, by SelectContext. **Read the sem-rate column, not the raw
   match rate**: index-based comparison counts same-card-different-copy picks as
   mismatches (measurement artifact found in exp042). Interpret with the
   6 lenses in `references/knowledge/ptcg_strategy.md` (prize / tempo / search /
   sequence / disruption / prize-liability).
   A low-match SelectContext is only actionable after checking the BASE `choose()`:
   e.g. TO_BENCH/SETUP_BENCH had NO scoring branch at all (always `ranked[:maxCount]`),
   so the gap was structural, not a tuning constant.

4. **Turn findings into tuning targets**, then patch the policy (a small monkeypatch
   in a `*_policy.py` exposing `PATCH_SRC` / `make_agent`, like discipline_policy.py).
   **Preferred pattern (established, exp023/exp042): add an env-gated block to
   `exp023_revenge/revenge_policy.py`** (default 0 = byte-identical to shipped
   behavior; turnbeam/v014 imports revenge_policy so the flag propagates to the
   whole current chain with zero code duplication).
   Prefer **indicator-triggered rules** (bench-free, line counts, prize diff, energy,
   opponent wall) over blanket changes; gate a tweak by opponent when it helps one
   matchup but hurts another (e.g. discipline ON vs mirror/aggro, OFF vs Crustle wall).

5. **Validate (critical): small-n gauntlets are NOISE-dominated (±0.05-0.10 at n≤60).**
   For deltas this size use **n≥200 + a paired same-opponent comparison** of BUILT
   artifacts (independent exec, no module contamination):
   ```
   uv run python workspace/exp018_adaptive/eval_mirror.py 200 <buildA> <buildB>
   uv run python workspace/exp018_adaptive/eval_compare.py 80   # vs ex/Crustle/dragapult
   ```
   For the CURRENT chain (v014/turnbeam), the directly comparable field eval is
   `exp035_turnbeam/eval_tb.py` in resumable 20-game chunks (template:
   `exp042_benchdisc/run_benchdisc.sh`); v014 n=200 reference: crustle .905 /
   ex_lucario .77 / dragapult .17 / archaludon .195 / mirror .585, total 2.67.
   MATCH=field is safe with env flags set process-wide (no field opponent imports
   revenge_policy); a paired candidate-vs-v014 run needs SEPARATE BUILDS (build the
   candidate with the SAME `--policy`/`--patch`/`--deck` as v014's actual build --
   e.g. `tb_patch.py` + `v_trev.json` -- and diff the two `main.py`s to confirm only
   the intended lines changed; reuse `exp035_turnbeam/build_v014/` as-is for the
   v014 side, no rebuild needed).
   Require: target matchup up (past ship bar: total +0.10), **no regression
   elsewhere, 0 crash errors**. Then `/build-submit` and (after approval) submit.
   **A behavioral match improvement is NOT a strength improvement** — exp042 raised
   TO_BENCH sem-rate 0.23→0.69 yet showed no winrate gain; always run the n≥200
   strength eval before shipping.
   **A field-eval total improvement is NOT a paired-strength improvement either**
   — exp043's SEARCH_PRI patch showed total 2.760 (+0.09) vs the 5-matchup field,
   driven by a mirror gain against the field's non-turnbeam `gust_policy` mirror
   reference, but scored a dead-even 0.505 (101-97-2, n=200) head-to-head against
   the ACTUAL v014 (which has the same full turn-beam search that can partly
   route around a search-priority gap the simpler field opponent can't). For any
   turn-beam-chain patch, **the paired vs-v014 eval is the deciding gate, run it
   even when the field total already clears +0.10** — don't ship on field numbers
   alone.

## Notes
- Needs the cabt engine (`uv run`) + cached replays. Behavioral signals from small
  caches (20-65 games) are directional, not significant — confirm with the n≥200 eval.
- Top players' edge is often CONSISTENCY/discipline (prize-liability, resource
  conservation), not opponent-archetype switching — see [[meta-and-leaderboard]].
- Reusable assets: `analyze_adaptation.py` (behavior by opponent),
  `exp042_benchdisc/policy_diff2.py` (decoded decision diff vs a SELECTABLE policy,
  with sem-rate), `eval_mirror.py` / `eval_compare.py` and
  `exp035_turnbeam/eval_tb.py` (noise-safe validation).
- A top player's cached replays are also **BC / fine-tune material** for the exp041
  pretraining pipeline (Plan B2: Mogja J mirror games) — scouting output is dual-use,
  keep the decoded-decision caches.
