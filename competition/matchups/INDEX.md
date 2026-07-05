# マッチアップ別知見インデックス

デッキ（相手アーキタイプ）ごとに、構造的な強み弱み・我々の対応履歴・現在の判定/ゲート状況を蓄積する。
アーキタイプ名は `workspace/exp011_meta_watch/fine_classify.py`（`classify()`）の返り値と一致させる。
新しい実験でマッチアップ固有の知見が出たら、該当ファイルを更新する（重複記録ではなく1箇所に集約）。

各ファイルの構成: 構造的事実（HP/主要技/レース算術）→ 我々の勝率履歴（版ごと）→ 適用済みルール/ゲート→ 未解決の論点。

| アーキタイプ (fine_classify キー) | 分類 | ファイル | 現状の一言 |
|---|---|---|---|
| Crustle | 壁(ex耐性) | [crustle.md](crustle.md) | 我々の主戦場。非ex攻撃で貫通、v011-v014で継続改善（0.73→0.90+） |
| Dragapult ex | レース(バースト) | [dragapult.md](dragapult.md) | **構造的劣勢**（HP320/Phantom Dive確殺）。+30補正でも僅差、piloting限界 |
| Archaludon ex | 壁(高HP) | [archaludon.md](archaludon.md) | **構造カウンター**（HP300+、220確殺、非exバイパス）。exp039でゲート導入 |
| Mega Lucario ex + Solrock/Lunatone | ex主力 | [ex_lucario.md](ex_lucario.md) | 好相性。v013の応手ガードが最も効いた相手 |
| Marnie's Grimmsnarl ex | ex主力(高速) | [grimmsnarl.md](grimmsnarl.md) | v012が複製に0.68で対策不要と判定済み |
| Great Tusk LO (mill) | mill/壁 | [great_tusk_lo.md](great_tusk_lo.md) | 0.82で非脅威（Safeguard/NZはex攻撃のみ無効） |
| Hop (non-ex Trevenant) | ミラー | [mirror_nonex.md](mirror_nonex.md) | 自分自身のデッキ。操縦の差が勝敗を分ける |
