# exp024 — TR-engine 操縦 feasibility 調査 → ★誠実なネガティブ（deck⊗pilot 6回目）

## 背景
新 #1 Yushin Ito (1387) は**我々と同じ非ex Hop's Trevenant**だが、ドローエンジンが
**tutor 型**（Team Rocket's Transceiver→Petrel→任意Trainer / Hilda=進化+エネ / Telepath Psychic=基本2体 / Xerosic 妨害 / Mist=効果防御）。
我々は **draw 型**（Dunsparce→Dudunsparce ドロー3）。take-when-legal で測った「exposure/throughput ギャップ」の正体＝この**エンジン差（デッキレベル）**。
仮説: tutor チェーンを操縦できれば #1 build に届く。

## データ
- `yushin_deck.json`（#1 の60枚, cached リプレイから復元）。Debauchery(#1系, 65試合 cached)も同 TR エンジン（engine 14枚, Dunsparce 0）。
- Debauchery の tutor PLAY/game（`decode_tutor.py`）: Lillie 2.0 / Transceiver 1.98 / HopsBag 1.54 / Pokegear 1.32 / Hilda 0.91 / Xerosic 0.77 / Petrel 0.68 / SecretBox 0.03。＝**確定サーチで毎ターン必要札を引っ張る**。

## 測定（我々の best 方策で TR デッキを操縦, league vs mirror v010/ex/Crustle/dragapult）
| deck × policy | mirror | ex | Crustle | dragapult | field概算 |
|---|---|---|---|---|---|
| **charmq × v011(revenge)** (基準, n200) | 0.505 | 0.755 | 0.780 | 0.140 | **0.609** |
| yushin(TR) × revenge (n80) | 0.325 | 0.537 | 0.787 | 0.138 | **~0.46** |
| yushin(TR) × **TR-fetch prototype** (n80) | 0.338 | **0.400** | 0.725 | 0.138 | ~0.43（退行）|

- **TR デッキは我々の best 方策で field ~0.46 ＝ charmq v011(0.61) を大きく下回る**（ex 0.54 vs 0.755, mirror 0.33 vs 0.505）。全方位で劣る。0 crash error（ハードブリックではない）。
- **setup 速度は問題でない**（`diag.py`: TR 初撃 turn 3.6 ＜ charmq 3.8）。ギャップは**中盤のエンジン活用**＝情報境界の領域。
- **`_score_to_hand` の phase-aware fetch prototype（早期=draw/chain/setup 優先, 後期=Boss/Choice Band）は退行**（ex 0.537→0.400）。tutor の fetch 優先度を弄ると tools/妨害が引けず悪化＝**我々は tutor エンジンを操縦できない**ことを確証。

## 結論（feasibility = ネガティブ）
- **TR エンジン非ex は我々の枠組みでは操縦不能**（#1 で 1387 = expert 操縦, 我々 ~0.46）。**deck⊗pilot 6回目の確証**。
- take-when-legal の解釈を**デッキレベルでも裏付け**: 頂点との throughput 差は **tutor エンジン**にあるが、そのエンジンは**我々が操縦できない**＝throughput ギャップは pilot 修正でも deck 採用でも**閉じられない（情報境界）**。
- **我々の pilotable 最適は charmq + v011(revenge)**（field 0.61, ラダー 871 上昇中, mirror 0.70）。TR への乗り換えは**負け**。
- レポート材料: 「頂点の優位は操縦できない tutor エンジン throughput。我々は draw エンジン＋実機構修正(gust/revenge)で pilotable 最適に到達」＝ deck⊗pilot ＋ 情報境界の最終確証。

## 資産
- `yushin_deck.json` / `decode_tutor.py`（tutor PLAY・fetch 集計）/ `floor.py`（任意 deck×policy をリーグ評価）/ `diag.py`（setup 速度）/ `tr_policy.py`（TR-fetch prototype, 退行）。
