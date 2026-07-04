# exp034 — 対 Dragapult ゲート付きベンチ規律 → 無効（機構特定が成果）

## 背景（v013 敗因解読, 2026-07-04）
v013 ラダー 84 試合: 44-40。**負け40の53% = Dragapult(1-12, 0.08) + Archaludon(1-9, 0.10)**。
dragapult シェア 6%→15% に倍増。リプレイ解読: 消滅の主体はベンチの低HP基本
（Dunsparce/Phantump）＝ Phantom Dive のばら撒きが餌にしている、と見えた。

## 仮説と実装
v009 規律（ベンチ配給制限）を **Dreepy line 検出時のみ**発動（exp018 の Crustle 退行をゲートで回避）。
`antispread_policy.py`（revenge チェーンに合成、guard_policy に GUARD_BASE=antispread 追加）。

## 結果 → 無効
guard+antispread vs dragapult: n=20 0.05 / **n=80 0.200**（v013 基準 0.205 と同値）。0エラー。

## 機構（なぜ効かない）— レース算術で確定
- Dragapult ex **HP320 / Phantom Dive 200（2エネ）** → Trevenant 140 を毎ターン確殺。
- Trevenant revenge 130 → 320 に **3発**。ベンチ狙撃を絞っても本線のレースで負けている。
- **勝ち筋は +30 補正**: 130+30(Choice Band or Postwick) = **160×2 = 320 ちょうど2発**。
  現デッキは Band×1 / Postwick×2 = 細すぎて再現性がない。

## 帰結（重要な戦略判断）
- **床マッチ2つ（負けの53%）は piloting では救えない（デッキ構造）**。
  - dragapult: +30 の増量（Band 1→3等, exp035 候補）＋「攻撃前に Band/Postwick を確実に張る」順序付け。
  - archaludon: exp025/026 で対策全滅済み（構造的）。
- piloting の残り伸び代は「ターン内スループット/順序付け」（turn-beam）と中位マッチ
  （Starmie/Grimmsnarl 0.25, n=4 と小さいが）に限定される。
