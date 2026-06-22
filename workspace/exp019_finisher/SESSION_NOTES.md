# exp019_finisher — SESSION NOTES

仮説: exp015(検証リーサル探索)の NO-GO 真因＝偽リーサル(サイド落ち札を山札と誤認)。公開 Gold(1250) Starmie の
**prize tracking**([[prize-tracking-starmie]] / `references/knowledge/prize_tracking_starmie_0622.md`)で
forward-search に正しい山札を渡せば、検証済みリーサルが v009 に上乗せできるのでは。

## 実装
- `prize_tracker.py`: 公開 Starmie の PrizeTracker を本 API に移植（保守的＝曖昧なら unknown）。
  デッキ可視時(サーチ効果中 `obs.select.deck`)に prized = decklist − 全可視 を推定・キャッシュ。in-flight 札は `obs.select.effect` で減算。
  `deck_contents(obs)` = decklist − 可視 − prized（探索に渡す正しい山札, 不明なら None）。
- `finisher_policy.py`: base = **v009 discipline**。自手番 single-pick・自プライズ≤2・**prized 既知**のとき、
  正しい deck_contents で **K=5 決定化** → 各手を自ターン rollout(base 方策で完了) → **全Kで勝つ手のみ**採用（検証済みリーサル）。
  v009 が勝てる/曖昧/未検出なら v009 に委譲。クラッシュ安全。

## 結果（finisher vs v009, 先後入替, n=200）
- **winrate 0.530（106-92-2）＝有意でない**（p≈0.16, 95%CI が 0.50 を含む）。
- STATS: searched 3851 / **known 2103(55%)** / **base_wins 305** / fired **23**(0.12/game) / any_opt_checked 1798。
- 速度: max_move **1.9s**（v009 0.04s の ~50倍。10分/試合予算内だが重い）。err 0。

## 結論（誠実な切り分け）
1. **prize tracking は正しく機能**: known 55%・base_wins 305＝探索が**実際の勝ちを検出**。exp015 の偽リーサルを除去。
   → exp015(prize-blind)＝**有害**(ミラー≤0.47) に対し、exp019(prize-aware)＝**無害・中立**(0.53)。**害の原因は決定化の誤りだった**と確定。
2. **だが我々の非ex単サイドデッキでは上積みが小さい**: v009 が既にリーサルを取り切る(base_wins≫fired)。
   1ターン1KOのデッキなので「1ターンで複数サイド取る検証探索」が活きる局面が稀(fired 0.12/game)。
3. **非提出**: 0.53(非有意)の上積みに 50倍の速度コストは見合わない。eligible は {v009, v008} 維持。
   v010 として出しても v008 を押し出すだけで実利なし。

## 価値 / 申し送り
- **rl-status の探索系統の結論を精緻化**: 「探索はヒューリスティックを超えない」は正しいが、exp015 の*有害さ*は
  prize tracking で解消できる＝**探索は『無害だが我々のデッキには不要』**が正確。別デッキ(複数KO/ターン, ダメージ誤認の多い線)では prize-aware 検証リーサルが効く可能性。
- **再利用資産**: `prize_tracker.py`(任意デッキのサイド落ち推定), `finisher_policy.py`(prize-aware 検証リーサル枠組み)。
- レポート素材: 「公開知見(prize tracking)で過去の負(exp015)の原因を切り分け、誠実に再評価」。
