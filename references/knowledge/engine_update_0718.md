# エンジン更新（disc727094）と07-18メタ（pilkwang 152票）

- 取得日: 2026-07-18
- URL: disc727094（staff告知）/ pilkwang「Meta Snapshot: 18 July」

## エンジン更新（07-17告知）
- 修正内容を実diffで確認: **EffectProc.h ToolCountProcの3行のみ**（内側ループ変数iのシャドウイング
  →TR専用エネルギーが非TRポケモンに付いた際の捨て札処理で誤ったプレイヤーindexにMoveCard
  →**敗勢側が故意にクラッシュを誘発できた**）。kawattataido報告（disc717141#3495412）。
- 影響: 我々のデッキ（LO/Alakazam）はTR専用エネ不使用＝挙動影響ゼロ。クラッシュ悪用の穴が
  塞がれた分プラス。sim.pyはmac/arm対応追加のみ。
- 対応済み: data/sim_sample/cg/ を新版に更新（旧版は cg_pre0717backup に保管）、
  build_koff2 を新cgで再ビルド→スモーク30戦0err→bare-execレプリカ87手0err。
  **v029以降は build_koff2/submission.tar.gz を使う**。ローカルCRNパッチ.soは旧ソース由来だが
  修正パスは我々のプールで不達＝再ビルド不急。

## pilkwang 07-18スナップショット（field全帯域、07-10〜16）
- **TR Spidops急伸: シェア1.4%→12.3%、score rate 52.3%**。Alakazamに54.3%(510試合)、
  Crustleに~61%勝つ「両柱キラー」。**我々のコンティンジェンシートリガー
  （非exアグロ>10-15%）に到達——ただしfield全帯域値。900-1000帯のシェアは次回band-metaで確認**。
- Crustle壁は退潮（28%→19.5%、score 46.7%）。Alakazam中心は不変（39.7%、50.1%）。
- Starmie: exact-list最強シグナル（+198.7）だがAlakazamに40.5%で負け。彼らの再現パイロットは
  参照Lucario未満（81.1% vs 86.5%）＝**deck≠agentの独立確認（我々のdeck⊗pilot則と同一結論）**。
- Marnie/Grimmsnarl 1.6%まで縮小（我々のチップ穴には追い風）。Festivalという新レーン出現（4-7%）。
- 選択効果の教訓も明記（p005 89.2%→78.1%）＝我々のn=600規律と同じ話。

## 我々への含意
- koffの逆風候補はSpidops（Safeguard/NZが効かない非ex主体）。**次回/meta-watchで
  自帯域のSpidopsシェアを必ず確認**。>15%なら対抗札の検討（v020はfloor-TRを0.95で轢く実測あり）。
