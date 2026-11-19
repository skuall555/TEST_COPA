# PA 1：AI_画像一時保存（既存案件行更新版）

> **使用停止（2026-11-19）**
>
> このPAをCopilot Studioのツールとして呼び出さないでください。現在のテナントではツールにファイル入力が公開されず、
> 画像のBase64文字列化が必要になるため、採用しません。
>
> 正しい導入は [00_Base64なし_既存画像転送PAへ統合.md](00_Base64なし_既存画像転送PAへ統合.md) を使います。

画像をSharePointライブラリへ一時保存し、既存の `AI_エージェント可視化` の案件行へ最新画像情報を書き込みます。新しいリスト行は作りません。

## 1. フローとトリガー

インスタントクラウドフロー `AI_画像一時保存` を作り、トリガーを「エージェントがフローを呼び出したとき」にします。

入力は次の順番です。

|順番|表示名|種類|コード上の名前|
|---:|---|---|---|
|1|conversation_id|テキスト|`text`|
|2|channel_id|テキスト|`text_1`|
|3|user_id|テキスト|`text_2`|
|4|user_text|テキスト|`text_3`|
|5|mime_type|テキスト|`text_4`|
|6|image_file|ファイル|`file`|

既存YAMLとの入出力を変えないため、順番も変更しません。

## 2. 変数

|変数|種類|初期値|
|---|---|---|
|varImageToken|文字列|`guid()`|
|varRecordId|整数|`0`|
|varImageUrl|文字列|空|
|varFileIdentifier|文字列|空|
|varOldFileIdentifier|文字列|空|
|varWidth|整数|`0`|
|varHeight|整数|`0`|
|varImageVersion|整数|`1`|
|varErrorCode|文字列|空|
|varSuccess|ブール|`false`|
|varDimensionRetry|整数|`0`|

## 3. 入力チェック

次の条件がtrueなら、ファイルを作らず `INVALID_IMAGE_INPUT` を返します。

```text
@or(
  empty(triggerBody()?['text']),
  empty(triggerBody()?['file']?['contentBytes']),
  not(
    or(
      equals(toLower(triggerBody()?['text_4']), 'image/png'),
      equals(toLower(triggerBody()?['text_4']), 'image/jpeg'),
      equals(toLower(triggerBody()?['text_4']), 'image/jpg')
    )
  )
)
```

## 4. 既存案件行を先に検索

「SharePoint－複数の項目の取得」を追加します。

- リスト：`AI_エージェント可視化`
- フィルタークエリは、式タブから次を指定
- 上から順に取得：`Modified desc`
- 上から順に取得する件数：`1`

```text
@concat(
  'ConversationId eq ''',
  replace(triggerBody()?['text'],'''',''''''),
  ''''
)
```

取得件数が0なら、`varErrorCode=CASE_ROW_NOT_FOUND` として応答へ進みます。画像分析はCopilot Studio側で継続します。空の案件行を画像PAから作成してはいけません。

1件見つかった場合、次を設定します。

```text
varRecordId:
@int(first(body('複数の項目の取得')?['value'])?['ID'])

varOldFileIdentifier:
@coalesce(first(body('複数の項目の取得')?['value'])?['ImageFileIdentifier'], '')

varImageVersion:
@add(int(coalesce(first(body('複数の項目の取得')?['value'])?['ImageVersion'], 0)), 1)
```

## 5. ファイル名と画像保存

「作成」`Compose_FileName`：

```text
@concat(
  variables('varImageToken'),
  if(equals(toLower(triggerBody()?['text_4']), 'image/png'), '.png', '.jpg')
)
```

「SharePoint－ファイルの作成」：

- ライブラリ：`AI_TemporaryImages`
- ファイル名：`Compose_FileName`
- ファイルコンテンツ：`image_file contentBytes`

動的コンテンツを直接指定して画像が壊れる場合だけ、次を使用します。正常に開く環境では二重変換しません。

```text
@base64ToBinary(triggerBody()?['file']?['contentBytes'])
```

作成後に設定します。

- `varFileIdentifier`：ファイル作成結果の `Id` または `Identifier`
- `varImageUrl`：ファイルのプロパティから得た「アイテムへのリンク」

リンクで画像表示できない場合は、サイトURLとPathを結合します。

```text
@concat(
  'https://tokyogasgroup.sharepoint.com',
  replace(outputs('ファイルの作成')?['body/Path'], ' ', '%20')
)
```

## 6. 画像の幅・高さ

既存版と同じく「SharePointへのHTTP要求を送信」で取得します。

```text
@concat(
  '_api/web/GetFileById(guid''',
  outputs('ファイルの作成')?['body/UniqueId'],
  ''')/ListItemAllFields?$select=ImageWidth,ImageHeight'
)
```

```text
varWidth:
@int(coalesce(body('SharePointへのHTTP要求を送信')?['ImageWidth'], body('SharePointへのHTTP要求を送信')?['d']?['ImageWidth'], 0))

varHeight:
@int(coalesce(body('SharePointへのHTTP要求を送信')?['ImageHeight'], body('SharePointへのHTTP要求を送信')?['d']?['ImageHeight'], 0))
```

幅・高さが0の場合だけ1秒待って再取得し、最大3回で終了します。3回とも0なら `IMAGE_DIMENSION_UNAVAILABLE` を残し、画像は保存しますがPower Appsの枠を非表示にします。

## 7. 既存案件行を更新

「SharePoint－項目の更新」を追加します。

- リスト：`AI_エージェント可視化`
- ID：`varRecordId`
- Titleが必須表示される場合：検索結果の既存 `Title` をそのまま設定

画像列だけを次の値で更新します。既存の優先度・回答・CaseId・Status等はマッピングし直したり空文字で上書きしたりしないでください。

|列|値|
|---|---|
|ImageToken|`varImageToken`|
|ImageUrl|`varImageUrl`|
|ImageFileIdentifier|`varFileIdentifier`|
|ImagePixelWidth|`varWidth`|
|ImagePixelHeight|`varHeight`|
|ImageOverlayJson|`{"version":1,"show":false,"reason":"分析中","markers":[]}`|
|ImageAnalysisNote|`画像分析中`|
|ImageAnalysisStatus|`TEMP_SAVED`|
|ImageVersion|`varImageVersion`|
|ImageUserText|トリガー `user_text`|
|ImageExpiresAt|`addHours(utcNow(),24)`|
|ImageErrorCode|`varErrorCode`|

更新成功後、`varSuccess=true` にします。

## 8. 前画像を削除

案件行の更新が成功してから、`varOldFileIdentifier` が空でない場合だけ前画像を削除します。

削除失敗は今回の画像保存成功を取り消しません。定期削除で再処理できるよう、必要ならフロー実行履歴へ警告だけ残します。

新しい画像ファイルは、案件行更新前に削除しないでください。

## 9. 失敗時の後始末

新画像ファイル作成後、案件行更新が失敗した場合は、新しく作った `varFileIdentifier` のファイルだけ削除します。前画像と既存案件行は変更しません。

- `varErrorCode=TEMP_SAVE_FAILED`
- `varSuccess=false`

## 10. エージェントへ応答

最後に「エージェントに応答する」を1個だけ置きます。

|出力名|種類|値|
|---|---|---|
|success|はい/いいえ|`varSuccess`|
|record_id|テキスト|`string(varRecordId)`|
|image_token|テキスト|`varImageToken`|
|image_url|テキスト|`varImageUrl`|
|image_width|数値|`varWidth`|
|image_height|数値|`varHeight`|
|image_version|数値|`varImageVersion`|
|error_code|テキスト|`varErrorCode`|

## 11. 単体テスト

1. 既存案件でPNG：同じ案件行のImage列だけ更新される
2. 既存案件でJPEG：同上
3. 案件行がない会話：`CASE_ROW_NOT_FOUND`、新規行なし
4. PDF：`INVALID_IMAGE_INPUT`、ファイル作成なし
5. 画像寸法取得失敗：URLは保存、枠は非表示
6. 2枚目：同じ案件行が更新され、1枚目のファイルが削除される
7. 既存の優先度・現場回答・Status・CaseIdが変化していない
