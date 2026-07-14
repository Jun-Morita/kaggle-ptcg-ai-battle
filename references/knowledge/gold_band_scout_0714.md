# gold帯（LBトップ8, 1150-1283）の戦略構造 — 2026-07-14スカウト

- 取得: episode traversal（Yushin sub 54360530経由）→ top_meta.py で majkel_0714 / budew_0714 をキャッシュ
- 対象: Majkel1337(#1, 1283.1, sub 54618168)、Budew(#7, 1180.3, sub 54554421)、
  ほかtop8のsub_id特定済み: Rmy 54641202 / LiamK 54634530 / bono 54589656 /
  懒惰的金枪鱼 54663417 / vibechu 54662628 / hpp sak 54553970 / WinDecks 54330985

## デッキと戦績

| 順位 | プレイヤー | デッキ | 特徴・戦績 |
|---|---|---|---|
| #1 | Majkel1337 1283 | **Alakazam＋重妨害** | Enhanced Hammer×4・Xerosic×3・Nighttime Mine×2。対壁17-10(0.63)、対非ex 0.89、ミラー0.54 |
| #2 | Rmy 1190 | **Mega Kangaskhan純壁** | band_pure_wall.jsonの同系（Crushing Hammer型） |
| #7 | Budew 1180 | **Mega Kangaskhan純壁**（最頻リストそのもの） | 壁ミラー11-6(0.65)、mixed_ex3 0.90。**弱点: ex_beatdown 0.38、非ex 0.20、TR Spidops 0-3(0.00)** |
| #4 | Yushin Ito 1173 | Grimmsnarl(mixed_ex5) | **対crustle系 40-112(0.26)＝壁に養分化** |

## 構造的発見

1. **gold帯はきれいな三すくみ**: Alakazam(＋妨害) → 壁に0.63 ／ 壁 → LOに~0.88 ／
   LO → Alakazamに0.83-0.92（我々のローカル・実戦一致）。トップ8は各頂点に分かれて陣取る。
2. **LOは1100超に存在しない**: Majkel 72試合＋Budew 82試合の対戦相手にLO型ゼロ。
   LO勢はsilver帯(923-983)に滞留＝**LOの実測プラトー≒950-1000**。
   → v023のsilver(926)到達は壁に阻まれない（silver帯の壁シェア~2-3%）が、
   **gold(1078)は壁密集帯を抜く必要があり別問題**。
3. **非exアグロ(TR Spidops)はSafeguard系全部のキラー**: 我々のLOに3-0、Budewの壁にも3-0。
   ex攻撃無効(Safeguard/Zone/Kangaskhanのミスト系)を全て素通りする構造。現シェア4%。
   伸びればgold帯の壁勢も沈む＝メタ回転の起点候補として最重要監視。
4. Majkel(#1)の勝ち筋は「Alakazamに妨害を積んで壁を割る」: Enhanced Hammer×4が壁の
   特殊エネ(Mist/Spiky/Grow Grass 12枚)を剥がす＝壁キラーとしてのAlakazam。

## 我々への含意
- **silver押し切り路線は不変**（v023の敵はsilver帯にはいない）。
- gold挑戦する場合の教科書は Majkel型「Alakazam＋Hammer妨害」だが、我々のLOはそれに勝つ
  ＝三すくみの外に出る単独最強は存在しない。best-of-2でも補完不可のため、gold挑戦は
  「壁もAlakazamも同時に上回る別次元」が必要（現有資産では未達）。
- Strategy レポート素材: 三すくみの実測エッジ（0.63/0.88/0.87）とLOプラトーの実在。
