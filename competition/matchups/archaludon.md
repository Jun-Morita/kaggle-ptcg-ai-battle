# Archaludon ex（壁・高HP）

fine_classify キー: `"Archaludon ex"` / 3rd-party実装: `workspace/exp025_unkoable/archaludon_opp/`
(public notebook "a-sample-archaludon-75-wr-vs-my-1300-starmie")

## 構造的事実
- Archaludon ex **HP300**（Full Metal Lab/Hero's Cape で400まで伸びる）。
- **Metal Defender 220** が我々の非exアタッカー（HP140-150）を確定OHKO。
- 我々の最大打点（Snorlax140 / revenge-window Trevenant130）では **HP300+ を割れない** = 構造カウンター。
- Duraludon×4 + 回収でアタッカーが枯渇しにくい。

## 我々の勝率履歴
| 版/施策 | 対Archaludon勝率 | 出典 |
|---|---:|---|
| v012 (施策前) | 0.13→0.175 (n=200) | exp027 |
| v013 (応手ガード) | 0.165 (flat) | submissions.csv |
| v014 (turn-beam) | 0.195 | submissions.csv |
| exp025 un-KOable redirect (単独) | 0.12→0.16 | exp025 SESSION_NOTES（**なお~84%負け、反転せず**） |
| exp038 depth=2 (n=100) | 0.05 | exp038 SESSION_NOTES（悪化） |
| exp039 archetype模倣ガード (n=100, ゲート前) | **0.10**（v014比 -0.095, 明確な悪化） | exp039 SESSION_NOTES |
| exp039 + archaludon検出時ガード無効化 (n=20 speed-check) | 0.20 | 2026-07-05 |
| exp039 + archaludon検出時ガード無効化 (n=100 本検証) | **0.19**（v014の0.195と同水準、ゲート狙い通り機能） | exp039 SESSION_NOTES 2026-07-05 |

## 適用済みルール
- **exp039 `guard_opp_policy.py`**: `opp_model._archetype == "Archaludon ex"` を検出したら応手ガードを完全に無効化し、v014単体の判断に委ねる（`GO_GATE_ARCH` env で切替可）。
  理由: 既に構造的に負けているレースでは、doom-veto の「破滅判定」がほぼ常に真になりがちで、ノイズで誤発火する。

## 実ラダーでの確認（2026-07-05, meta_watch）
- 我々の最新提出（n=82試合）の粗分類バケット `mixed_ex4`（**現メタの約20%を占める最大級のバケット**）の中身を
  リプレイの`opp_deck_top`で直接確認したところ、**大半がArchaludon ex**（Duraludon×4/Archaludon ex×4/Cinderace×4/
  Full Metal Lab×4/Relicanth/Poké Pad/Ultra Ball/Pokégear 3.0/Night Stretcher/Jumbo Ice Cream/Hero's Cape/
  Boss's Orders/Explorer's Guidance という構成）で占められていた。
- 該当バケットでの我々の実戦績: **4勝12敗（勝率25%）**＝現在の実ラダーで最も負けている相手。
- 我々の`archaludon_opp/deck.csv`（exp025で構築, exp038/039のOpponentModelが使用）は上記の実デッキと**カード構成が高い精度で一致**
  （Duraludon/Archaludon ex/Cinderace/Full Metal Lab/Relicanth/Poké Pad/Ultra Ball/Pokégear3.0/Night Stretcher/
  Jumbo Ice Cream/Hero's Cape/Boss's Orders/Explorer's Guidance が全て一致）＝相手モデルの精度は担保されている。
  **問題はモデルの不正確さではなく、レース算術そのもの**（既知の構造カウンター）。
- **結論**: Archaludon exは「5マッチのうちの1つ」という以上に、**現メタで最も頻出かつ最も負けている実在の脅威**。
  優先度を上げて再検討する価値がある（deck-side の対策、あるいは win-rate 25%を底上げする局所ルールなど）。

## 未解決の論点
- un-KOable redirect（exp025, +0.03-0.04程度）は単独では割に合わないが、他の改善と重ねれば safe な底上げ候補。
- 根本的な解決（Archaludonを互角以上にする）は piloting では困難というのが複数実験の一致した結論（Mega Starmie を操縦で倒せなかったのと同型の壁）。
- メタシェアが下がれば自然減衰するタイプの脅威（exp025-026の記録）。`/meta-watch` で継続監視。
- **実ラダーでの実際のシェアが20%・勝率25%と判明した以上（上記2026-07-05確認）、経過観察だけでなく、
  次にこのマッチアップに手を入れる際は具体的な優先課題として扱う価値がある**（exp039のようなグローバル施策ではなく、
  archaludon専用のライン、例えばun-KOable redirectの本格投入や、デッキ側の対策を再検討）。
