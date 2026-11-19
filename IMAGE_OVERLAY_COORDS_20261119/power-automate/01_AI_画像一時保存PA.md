# PA 1：AI_画像一時保存

画像をAIへ渡す前に、受信した同じ画像をSharePointへ一時保存します。画像1枚につきListsへ1行作ります。既存案件保存PAは変更しません。

## 1. フローを作る

1. Power Automateを開きます。
2. 「新しいフロー」→「インスタント クラウド フロー」を選びます。
3. 名前を `AI_画像一時保存` にします。
4. トリガーは「エージェントがフローを呼び出したとき」を選びます。

## 2. トリガー入力

次の順番で追加します。順番が重要です。

|順番|表示名|種類|コード上の名前|
|---:|---|---|---|
|1|conversation_id|テキスト|`text`|
|2|channel_id|テキスト|`text_1`|
|3|user_id|テキスト|`text_2`|
|4|user_text|テキスト|`text_3`|
|5|mime_type|テキスト|`text_4`|
|6|image_file|ファイル|`file`|

Copilot StudioのYAMLは、この内部名へ値を渡します。入力を削除して作り直すと番号が変わる場合があるため、その場合はYAML側も合わせてください。

## 3. 変数を初期化

以下の変数を追加します。

|変数|種類|初期値|
|---|---|---|
|varImageToken|文字列|式 `guid()`|
|varRecordId|整数|`0`|
|varImageUrl|文字列|空|
|varFileIdentifier|文字列|空|
|varWidth|整数|`0`|
|varHeight|整数|`0`|
|varImageVersion|整数|`1`|
|varErrorCode|文字列|空|
|varSuccess|ブール|`false`|
|varDimensionRetry|整数|`0`|

## 4. 入力チェック

条件を追加し、次のいずれかならエラー応答へ進めます。

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

エラー時は `varErrorCode` を `INVALID_IMAGE_INPUT` にし、最後の応答へ移動します。ファイル作成は行いません。

## 5. ファイル名を作る

「作成」アクションを追加し、名前を `Compose_FileName` にします。

```text
@concat(
  variables('varImageToken'),
  if(equals(toLower(triggerBody()?['text_4']), 'image/png'), '.png', '.jpg')
)
```

利用者が送ったファイル名を保存先名に使わずGUIDにすることで、同名上書き・禁止文字・個人情報の混入を避けます。

## 6. SharePointへ画像を作成

「SharePoint－ファイルの作成」を追加します。

- サイトのアドレス：`AI_TemporaryImages` を作ったサイト
- フォルダーのパス：`AI_TemporaryImages`
- ファイル名：`Compose_FileName` の出力
- ファイルコンテンツ：トリガーの `image_file contentBytes`

ファイルコンテンツが文字列として扱われる環境では次の式を使用します。

```text
@base64ToBinary(triggerBody()?['file']?['contentBytes'])
```

動的コンテンツを直接指定してファイルが正常に開ける場合は、上の変換式を重ねないでください。二重変換すると画像が壊れます。

作成後、次を変数へ保存します。

- `varFileIdentifier`：ファイルの作成の `Id` または `Identifier`
- `varImageUrl`：ファイルの作成後に「ファイルのプロパティの取得」で得た `アイテムへのリンク`

`アイテムへのリンク` が画像コントロールで表示できない環境では、サーバー相対パスを使い、次の形にします。

```text
@concat(
  'https://tokyogasgroup.sharepoint.com',
  replace(outputs('ファイルの作成')?['body/Path'], ' ', '%20')
)
```

## 7. 元画像の幅・高さを取得

Power Appsで縦横比を保ったまま正確に枠を置くため、ピクセル幅と高さが必要です。

「SharePoint－SharePointへのHTTP要求を送信」を追加します。

- サイトのアドレス：同じサイト
- 方法：`GET`
- URI：

```text
_api/web/GetFileById(guid'ファイルのUniqueId')/ListItemAllFields?$select=ImageWidth,ImageHeight
```

`ファイルのUniqueId` には「ファイルの作成」の `UniqueId` を動的コンテンツで入れます。画面上では次のような形になります。

```text
@concat(
  '_api/web/GetFileById(guid''',
  outputs('ファイルの作成')?['body/UniqueId'],
  ''')/ListItemAllFields?$select=ImageWidth,ImageHeight'
)
```

応答から次を設定します。

```text
varWidth:
@int(coalesce(body('SharePointへのHTTP要求を送信')?['ImageWidth'], body('SharePointへのHTTP要求を送信')?['d']?['ImageWidth'], 0))

varHeight:
@int(coalesce(body('SharePointへのHTTP要求を送信')?['ImageHeight'], body('SharePointへのHTTP要求を送信')?['d']?['ImageHeight'], 0))
```

SharePoint側の画像メタデータ生成が遅れる場合があります。HTTP要求を「Do until」に入れ、次のいずれかで終了させます。

- `varWidth > 0` かつ `varHeight > 0`
- `varDimensionRetry >= 3`

幅・高さが0なら1秒待って `varDimensionRetry` を1増やします。最大3回で終了します。無限ループにしないでください。

3回とも取得できない場合：

- `varErrorCode`：`IMAGE_DIMENSION_UNAVAILABLE`
- 画像とLists行は保存する
- Power Appsは画像だけ表示し、枠は非表示にする

## 8. Listsへ一時行を作る

「SharePoint－項目の作成」を追加します。

- リスト：`AI_ImageOverlay`

|列|値|
|---|---|
|Title|`IMG-` と `varImageToken` の先頭8文字|
|ConversationId|トリガー `conversation_id`|
|ChannelId|トリガー `channel_id`|
|UserId|トリガー `user_id`|
|CaseId|空欄（任意で既存案件を検索して入れてもよい）|
|ImageToken|`varImageToken`|
|ImageUrl|`varImageUrl`|
|FileIdentifier|`varFileIdentifier`|
|FileName|`Compose_FileName`|
|MimeType|トリガー `mime_type`|
|PixelWidth|`varWidth`|
|PixelHeight|`varHeight`|
|OverlayJson|`{"version":1,"show":false,"reason":"分析中","markers":[]}`|
|AnalysisNote|`画像分析中`|
|AnalysisStatus|`TEMP_SAVED`|
|ImageVersion|`1`|
|UserText|トリガー `user_text`|
|ExpiresAt|式 `addHours(utcNow(),24)`|
|ErrorCode|`varErrorCode`|

項目作成後：

- `varRecordId`：作成した項目の `ID`
- `varSuccess`：`true`

一時保存期間を変更する場合は `addHours(utcNow(),24)` の24だけを変更します。

## 9. 途中失敗時の後始末

ファイル作成後にLists項目作成が失敗した場合だけ、作ったファイルを削除します。孤立ファイルを残さないためです。

「スコープ－失敗処理」を用意し、正常処理スコープが失敗・タイムアウトした場合に実行します。

1. `varFileIdentifier` が空でなければ「ファイルの削除」
2. `varErrorCode` が空なら `TEMP_SAVE_FAILED`
3. `varSuccess` を `false`
4. 応答へ進む

## 10. エージェントへ応答

最後に「エージェントに応答する」を置きます。次の出力名・種類を正確に作ります。

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

「応答」アクションは成功・失敗のどちらからも必ず到達する位置に1個だけ置きます。

## 11. フロー設定

- タイムアウトを短くしすぎない
- 非同期応答を使用しない
- 所有者のSharePoint接続を使用する場合、利用者へ接続の利用権限を付与する
- 保存後にCopilot Studioの「ツール」からこのフローを追加する

## 12. 単体テスト

フロー単体ではエージェントから呼び、次を確認します。

1. PNG：`success=true`、URL、幅、高さ、record_idが返る
2. JPEG：同上
3. PDF：`success=false`、`INVALID_IMAGE_INPUT`
4. 幅・高さが取れない画像：URLは返るが `IMAGE_DIMENSION_UNAVAILABLE`
5. SharePoint権限を外したテスト接続：`TEMP_SAVE_FAILED`、孤立ファイルなし

