# PA 2：AI_画像座標更新（既存画像転送PA連携版）

Copilot Studioが生成した目印JSONを検証し、`AI_エージェント可視化` の同じ案件行へ保存します。
Power Appsから画像をCopilot Studioへ渡す既存PAが先に `ConversationId` と `ImageToken` を保存し、
本PAはその2値で行を検索します。画像バイナリは本PAへ送りません。

## 1. フローを作る

1. インスタント クラウド フローを新規作成します。
2. 名前を `AI_画像座標更新` にします。
3. トリガーは「エージェントがフローを呼び出したとき」です。

## 2. トリガー入力

次の順番で追加します。

|順番|表示名|種類|コード上の名前|
|---:|---|---|---|
|1|record_id（表示名は変えない）|テキスト|`text`|
|2|image_token|テキスト|`text_1`|
|3|overlay_json|テキスト|`text_2`|
|4|analysis_note|テキスト|`text_3`|
|5|analysis_status|テキスト|`text_4`|

> 注意：登録済みツールのスキーマを変えないため、1番目の表示名 `record_id` はそのまま残します。
> 実際に渡す値は `System.Conversation.Id` です。名前変更や入力の追加はしません。

## 3. 変数

|変数|種類|初期値|
|---|---|---|
|varSuccess|ブール|`false`|
|varErrorCode|文字列|空|
|varSafeJson|文字列|`{"version":1,"show":false,"reason":"検証前","markers":[]}`|

## 4. 入力チェック

次のどれかなら更新しません。

```text
@or(
  empty(triggerBody()?['text']),
  empty(triggerBody()?['text_1']),
  empty(triggerBody()?['text_2'])
)
```

エラーコード：`INVALID_UPDATE_INPUT`

## 5. ConversationIdと画像トークンで対象行を取得

「SharePoint－複数の項目の取得」を使います。

- リスト：`AI_エージェント可視化`
- フィルタークエリ：式タブから次を入力
- 上から順に取得：`Modified desc`
- 上から順に取得する件数：`1`

```text
@concat(
  'ConversationId eq ''',
  replace(triggerBody()?['text'],'''',''''''),
  ''' and ImageToken eq ''',
  replace(triggerBody()?['text_1'],'''',''''''),
  ''''
)
```

取得件数が0なら `IMAGE_ROW_NOT_FOUND` を返し、更新しません。
行IDは以下で取得します。

```text
@int(first(body('複数の項目の取得')?['value'])?['ID'])
```

ConversationIdとImageTokenの両方が一致した最新行だけを更新するため、別画像の分析結果を誤保存しません。

## 6. JSONを解析

「JSONの解析」を追加します。

- コンテンツ：`triggerBody()?['text_2']`
- スキーマ：次を使用

```json
{
  "type": "object",
  "required": ["version", "show", "reason", "markers"],
  "properties": {
    "version": { "type": "integer", "enum": [1] },
    "show": { "type": "boolean" },
    "reason": { "type": "string", "maxLength": 500 },
    "markers": {
      "type": "array",
      "maxItems": 8,
      "items": {
        "type": "object",
        "required": ["id", "type", "color", "target", "msId", "label", "x1", "y1", "x2", "y2", "confidence", "basis", "message"],
        "properties": {
          "id": { "type": "string", "maxLength": 20 },
          "type": { "type": "string", "enum": ["observed", "uncertain", "candidate"] },
          "color": { "type": "string", "enum": ["green", "yellow", "blue"] },
          "target": { "type": "string", "maxLength": 100 },
          "msId": { "type": "string", "maxLength": 20 },
          "label": { "type": "string", "maxLength": 120 },
          "x1": { "type": "integer", "minimum": 0, "maximum": 1000 },
          "y1": { "type": "integer", "minimum": 0, "maximum": 1000 },
          "x2": { "type": "integer", "minimum": 0, "maximum": 1000 },
          "y2": { "type": "integer", "minimum": 0, "maximum": 1000 },
          "confidence": { "type": "string", "enum": ["high", "medium"] },
          "basis": { "type": "string", "maxLength": 500 },
          "message": { "type": "string", "maxLength": 1000 }
        }
      }
    }
  }
}
```

## 7. 各座標の関係を検証

JSONスキーマだけでは `x2 > x1` と `y2 > y1` を確認できないため、「配列のフィルター処理」を追加します。

- From：JSONの解析の `markers`
- 詳細モード：

```text
@and(
  greater(int(item()?['x2']), int(item()?['x1'])),
  greater(int(item()?['y2']), int(item()?['y1'])),
  or(
    and(equals(item()?['type'], 'observed'), equals(item()?['color'], 'green')),
    and(equals(item()?['type'], 'uncertain'), equals(item()?['color'], 'yellow')),
    and(equals(item()?['type'], 'candidate'), equals(item()?['color'], 'blue'))
  )
)
```

条件：元のmarkers件数とフィルター後件数が同じであること。

```text
@equals(
  length(body('JSONの解析')?['markers']),
  length(body('配列のフィルター処理'))
)
```

異なる場合：

- `varErrorCode`：`INVALID_MARKER_COORDINATES`
- `varSafeJson`：`{"version":1,"show":false,"reason":"座標検証エラー","markers":[]}`
- Listsには安全な空JSONを保存
- 現場回答や優先度は変更しない

## 8. showとmarkersの整合

次の条件も確認します。

```text
@or(
  and(
    equals(body('JSONの解析')?['show'], false),
    equals(length(body('JSONの解析')?['markers']), 0)
  ),
  and(
    equals(body('JSONの解析')?['show'], true),
    greater(length(body('JSONの解析')?['markers']), 0)
  )
)
```

不整合なら `INVALID_SHOW_FLAG` とし、安全な空JSONを保存します。

すべて合格した場合：

```text
varSafeJson = triggerBody()?['text_2']
```

## 9. Listsを更新

「SharePoint－項目の更新」で、取得した行を更新します。IDは上記の `first(...)?['ID']` を使います。

|列|値|
|---|---|
|ImageOverlayJson|`varSafeJson`|
|ImageAnalysisNote|トリガー `analysis_note`|
|ImageAnalysisStatus|入力が許可値ならその値。それ以外は `ANALYZED`|
|ImageVersion|既存の `ImageVersion + 1`|
|ImageExpiresAt|`addHours(utcNow(),24)`|
|ImageErrorCode|`varErrorCode`|

状態の許可値は `TEMP_SAVED`、`ANALYZED`、`NEEDS_REVIEW`、`VISUAL_OK`、`ERROR` だけです。今回のCopilot Studioコードは通常 `ANALYZED` を渡します。

更新後、`varSuccess=true` にします。座標が不正で空JSONへ置換した場合も、Lists更新自体が成功したら `varSuccess=true` ですが、`error_code` は残します。

## 10. 応答

「エージェントに応答する」を1個だけ置きます。

|出力名|種類|値|
|---|---|---|
|success|はい/いいえ|`varSuccess`|
|error_code|テキスト|`varErrorCode`|

JSON解析そのものが失敗した場合は、失敗処理スコープで次を行います。

1. `varSafeJson` を空マーカーJSONにする
2. `varErrorCode=INVALID_OVERLAY_JSON`
3. 対象案件行の `ImageOverlayJson` へ空マーカーJSON、`ImageErrorCode` へエラーを保存
4. `varSuccess=true`（安全な非表示状態の保存に成功したため）
5. 応答

## 11. 単体テスト

1. greenのマーカー1件：保存成功
2. green・yellow・blueを含む複数措置8件：保存成功
3. 9件：空JSONへ置換、エラー記録
4. x2がx1以下：空JSONへ置換
5. observedなのにblue：空JSONへ置換
6. message欠落：空JSONへ置換
7. 別ConversationIdまたは別トークン：Listsを更新せず `IMAGE_ROW_NOT_FOUND`
8. 壊れたJSON：現場処理を止めず空JSONを保存

