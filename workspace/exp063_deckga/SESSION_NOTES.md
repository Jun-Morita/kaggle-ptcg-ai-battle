# exp063 — koff自由枠のデッキGA（コア固定・トレーナーズ進化）

日付: 2026-07-18〜

## 位置づけ（ユーザー方針: 複数デッキの方策/構成改善でsilver確実化）
- koffの穴は構造起因（exp054-G: アビリティ打点素通し、操縦リークなし）で、
  残る改善軸は**リスト**＝離散空間＝GAの本領。
- exp059のdeck⊗pilot教訓への対処: パイロット前提のコア26枚
  （Tusk×4/Dwebble×4/Crustle×4/Rock Fighting×4/Mist×4/Fighting Gong×4/NZ×1/Terrakion×1）
  を固定し、**自由枠34枚（トレーナーズ）のみ**進化。パイロットはdeck.csvを読むので
  コード変更なしでリストが変わる。
- 共進化はやらない（LB=max()で自己相性は無価値＋自己参照プールの病理はexp040/041で実証済み）。

## 事前登録
- 適応度: SILVER帯加重勝率（EB.SILVER_BANDプール）、n=120/個体、世代内共通CRNシード、
  stockを毎世代同条件で並走評価（ベースライン）。
- GA: pop16（gen0にstock注入）、エリート2（毎世代再評価）、トーナメント2、一様交叉＋1-2スワップ変異。
  遺伝子プール: 既存自由枠11種＋新カード10種（Crushing/Enhanced Hammer, Night Stretcher,
  Hero's Cape, Handheld Fan, **Battle Cage**, Lillie's, Hilda, Dawn, Harlequin。
  ACE SPEC追加なし・TR専用なし・スタジアムはBattle Cageのみ意図的に許可）。
- **ゲート**: 最良個体 vs stock、新シードn=600で加重勝率**+0.03以上**かつ
  単一マッチアップ退行>0.05なし → 副作用（starmie_real/grimm_froslass/pure_wall）→ 出荷検討。
- **キル**: 20世代でstock+2SE超えの個体なし → 21件目のネガティブでclose
  （exp036の小n GAの罠はCRN＋n=600確認ゲートで対処。世代best値は選択バイアス込み、結論に使わない）。

## 実行記録
- スモーク（1世代 pop4 n20）: 8秒、エラー0（新カード挿入でパイロット無事故）。
- 本走: `--gens 20 --pop 16 --n 120 --workers 2`（exp060と並走のためworkers=2）、~1時間。
  ログrun1.log、resume可（results/state.json）。

## run1（07-18）: クラッシュ遺伝子で汚染 → 診断 → run2
- 20世代完走もerrs=126の倍数が頻発（126=1個体の全評価試合数）。
- 単カード差し替え診断で**Hero's Cape(1159)がLOパイロットを全試合クラッシュ**させると特定
  （他の新カード9種はerrs=0）。クラッシュ安全は出荷の絶対要件なので遺伝子プールから恒久除外。
- run1はbest 0.77-0.88で振動、stock+2SE(0.092)超えなし——ただしクラッシュ個体が
  個体群予算を浪費した汚染ランなので判定に使わない（事前登録のキル判定はrun2で行う）。
- run2: 同一設定でクリーン再走（~1時間）。

## run2（クリーン）＋n=600ゲート → NO-GO（20件目のネガティブ）
- run2は全世代errs=0。gen3/5/6/8/9でbest≧stock+2SE(0.092)→キル不発火、ゲートへ。
- 最良個体=gen9（+E.Hammer/+Harlequin×2/+Dawn/+B.Cage、サーチ系-3枚等。世代best出現1回のみ）。
- **n=600新シード同条件: 候補0.7394 vs stock 0.7863（-0.047）→ NO-GO**
  （要求+0.03。pure_wall 0.50→0.21、archaludon 0.835→0.738、alakazam 0.921→0.842と広範退行）。
- 結論: n=120適応度のGAはstock+2SE超えを5世代で出したが全て選択ノイズ（exp036と同型、
  ゲートが設計どおり捕捉）。**stockの自由枠はこの探索予算で改善不能な局所最適**。
  テック挿しはサーチ密度（Pokégear/Pad/Switch）を削る対価に見合わない
  ——公開LOリストの完成度の傍証（deck軸でもexp059と対になる結果）。
- 資産: クラッシュ診断法（単カード差し替え×n=12）、Hero's Cape=パイロット非互換の知見、
  GA+CRN+ゲートの汎用ハーネス（ga_deck.py、他デッキに転用可）。
