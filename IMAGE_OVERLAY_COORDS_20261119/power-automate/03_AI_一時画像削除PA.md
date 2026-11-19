# PA 3：AI_一時画像削除（案件行を残す版）

期限切れの一時画像ファイルを削除し、既存案件行の `Image...` 列だけを空にします。`AI_エージェント可視化` の案件行そのものは絶対に削除しません。

## 1. フロー作成

1. 「スケジュール済みクラウド フロー」を作成します。
2. 名前を `AI_一時画像削除` にします。
3. 1時間ごとに実行します。
4. タイムゾーンは `(UTC+09:00) 大阪、札幌、東京` を選びます。

## 2. 期限切れ案件を取得

「SharePoint－複数の項目の取得」を追加します。

- リスト：`AI_エージェント可視化`
- フィルタークエリ：

```text
ImageExpiresAt lt '@{utcNow()}' and ImageUrl ne null
```

- ページネーション：オン
- しきい値：5000

## 3. 各案件を処理

Apply to eachで次を実行します。

1. `ImageFileIdentifier` が空でなければ「SharePoint－ファイルの削除」
2. ファイル削除の成功・失敗・スキップ・タイムアウトのすべてから「項目の更新」へ進む
3. 項目の更新で、対象案件の画像列だけをクリア

項目の更新：

- リスト：`AI_エージェント可視化`
- ID：現在の項目の `ID`
- Titleが必須の場合：現在の項目の `Title` をそのまま設定

|列|クリア後の値|
|---|---|
|ImageToken|空|
|ImageUrl|空|
|ImageFileIdentifier|空|
|ImagePixelWidth|`0`|
|ImagePixelHeight|`0`|
|ImageOverlayJson|`{"version":1,"show":false,"reason":"画像保存期限切れ","markers":[]}`|
|ImageAnalysisNote|空|
|ImageAnalysisStatus|`EXPIRED`|
|ImageVersion|既存値+1|
|ImageUserText|空|
|ImageExpiresAt|空|
|ImageErrorCode|空|

優先度、現場回答、CaseId、ConversationId、Statusなど既存の案件列は変更しません。

## 4. 保存期間

画像一時保存PAと座標更新PAは標準で `addHours(utcNow(),24)` を設定します。必要なら両方を同じ時間へ変更してください。

## 5. テスト

1. テスト案件の `ImageExpiresAt` を過去時刻にする
2. フローを手動実行する
3. 一時画像ファイルが削除される
4. 案件行は残り、画像列だけがクリアされる
5. 優先度、回答、Status、CaseIdが変わっていない
6. ファイルを先に削除してから再実行しても、案件行が削除されない
