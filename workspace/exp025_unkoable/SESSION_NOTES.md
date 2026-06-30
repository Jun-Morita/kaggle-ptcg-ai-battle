# exp025 — 操縦高度化（軸3: un-KOable active redirect）→ 小幅プラスだが Archaludon は構造カウンター

## 動機（ユーザーの5軸監査より）
pilot 5軸を監査: 軸1(カード別)=手厚い / 軸2(進化9000)=既に最適 / 軸4(逃げ)=crude だが低価値 /
軸5(サーチ)=exp024 で再調整は退行＝天井 / **軸3(相手状況で使い分け)=最大 gap、特に新メタ Archaludon 未対応**。
→ 軸3「**倒せない active に殴り続けず、育成中のベンチを叩く**」汎用ルールを試作。

## メタ背景
新 LB #1 ShumpeiNomura(1465) = **Archaludon ex(Metal)**、#2 Takaaki Matsuda(1349) も Metal。
公開ノート「A Sample Archaludon」のアーキタイプが LB を制覇。Metal Defender 220 が我々(140-150HP)を OHKO、
Archaludon HP300(+Full Metal Lab/Hero's Cape で 400)＝**我々の最大打点(Snorlax140/window Revenge130)で倒せない**。

## 実装（`unkoable_policy.py`, revenge/v011 基盤）
`_plan_attack` を拡張: 相手 active HP≥200(=un-KOable)かつ KO 不能時、(a) active 狙いに −400(壁を削り続けない)、
(b) 最低HPのベンチ脅威に +250(進化前 Duraludon 等を Boss で引きずり denial)。**HP<200 のマッチでは発火せず=no-op**。

## 測定（charmq deck, league vs Archaludon/mirror/ex/Crustle）
| matchup | revenge(v011) | unkoable | Δ | 備考 |
|---|---|---|---|---|
| **archaludon** | 0.120 | **0.160** | +0.04 | n=150 |
| **crustle** | 0.667 | **0.727** | +0.06 | Hero's Cape Crustle(250HP)で発火 |
| ex | 0.733 | 0.733 | 0.00 | no-op(HP<200) |
| mirror | 0.547 | 0.473 | −0.07* | *構造上 no-op(mirror 最大150HP)＝run間ノイズ |

- **ルールは設計通り tank 限定で発火**（Archaludon 300 / caped Crustle 250）。mirror/ex は HP<200 で不発＝不変（mirror の −0.07 はノイズ）。
- **効果は小幅**: Archaludon +0.04(0.12→0.16)、Crustle +0.06。**no-regression な safe superset**（tank 全般を底上げ）。

## 結論（誠実）
- **操縦(軸3)は Archaludon を改善するが反転しない**（0.12→0.16＝なお ~84% 負け）。**Archaludon は構造カウンター**（向こうが毎ターン OHKO、Duraludon×4＋回収、我々の打点では HP300+ を割れない）＝piloting では解けない（Mega Starmie を操縦で倒せなかったのと同型）。
- **副産物として Crustle +0.06** は既存マッチの底上げで有用。un-KOable ルールは**将来 build に含める価値ある safe な小改善**だが、単独で提出枠を使うほどではない。
- **Archaludon メタへの本当の答え = Crustle の Safeguard（ex ダメージ0→Archaludon を構造封殺）**。次は v004 Crustle vs Archaludon を測定して meta-timing カウンターを判断すべき。

## 資産
- `load_archaludon.py`（公開 Archaludon を opponent 化, reviewed-safe）/ `archaludon_opp/{main.py,deck.csv}` / `eval_arch.py` / `unkoable_policy.py`。
- ShumpeiNomura(#1) 実デッキは `references/raw/replays` 由来で別途確認可（Duraludon→Archaludon ex×4, Metal×14, Judge/Carmine 手札破壊）。
