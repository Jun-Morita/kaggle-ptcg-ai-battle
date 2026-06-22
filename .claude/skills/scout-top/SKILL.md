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

3. **Decoded decisions** (what cards/choices differ), for the concrete patch:
   ```
   cd workspace/exp013_router
   uv run python policy_diff.py <sub_id> <deck.json> [max_episodes]
   ```
   Lists TO_HAND search targets they fetch vs we fetch, and top divergence examples
   (their choice vs ours) decoded to card names, by SelectContext. Interpret with the
   6 lenses in `references/knowledge/ptcg_strategy.md` (prize / tempo / search /
   sequence / disruption / prize-liability).

4. **Turn findings into tuning targets**, then patch the policy (a small monkeypatch
   in a `*_policy.py` exposing `PATCH_SRC` / `make_agent`, like discipline_policy.py).
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
   Require: target matchup up, **no regression elsewhere, 0 crash errors**. Then
   `/build-submit` and (after approval) submit.

## Notes
- Needs the cabt engine (`uv run`) + cached replays. Behavioral signals from small
  caches (20-65 games) are directional, not significant — confirm with the n≥200 eval.
- Top players' edge is often CONSISTENCY/discipline (prize-liability, resource
  conservation), not opponent-archetype switching — see [[meta-and-leaderboard]].
- Reusable assets: `analyze_adaptation.py` (behavior by opponent), `policy_diff.py`
  (decoded decision diff), `eval_mirror.py` / `eval_compare.py` (noise-safe validation).
