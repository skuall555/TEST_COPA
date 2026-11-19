# SharePoint準備

既存の `AI_エージェント可視化` は変更しません。画像専用のリストとドキュメントライブラリを1つずつ追加します。

## Excelから作る場合（簡単）

[AI_ImageOverlay_Listsインポート用_v2.xlsx](../AI_ImageOverlay_Listsインポート用_v2.xlsx) を使用できます。Excelの「導入手順」と「列の種類と用途」シートを先に確認してください。旧版は使用しないでください。

Excelからの取込は既存リストへ列を追加する機能ではなく、新しいリストを作る機能です。すでに作った `AI_ImageOverlay` が空の場合は、Excelから一度 `AI_ImageOverlay_Import` という名前で作成し、列確認後に名前を入れ替える手順をExcelへ記載しています。

`Title` はLists標準列です。1行テキストのままでよく、型変更は不要です。

## 1. 画像ファイル用ライブラリ

対象サイト：現在 `AI_エージェント可視化` があるSharePointサイト

1. SharePointの「サイトコンテンツ」を開きます。
2. 「新規」→「ドキュメント ライブラリ」を選びます。
3. 名前を `AI_TemporaryImages` にします。
4. バージョン履歴は不要です。ライブラリ設定から、必要に応じてメジャーバージョン数を最小にします。
5. このアプリを使う利用者へ「読み取り」、PAの接続ユーザーへ「編集」を付与します。

画像はPAがGUIDのファイル名で保存します。同じURLの上書きを行わないため、Power Appsの画像キャッシュによる取り違えを避けられます。

## 2. 座標情報用リスト

1. 「サイトコンテンツ」→「新規」→「リスト」→「空白のリスト」を選びます。
2. 名前を `AI_ImageOverlay` にします。
3. 次の列を追加します。列名は数式で使用するため、表記を変えないでください。

|列名|種類|必須|用途|
|---|---|---:|---|
|Title|1行テキスト|いいえ|`IMG-会話IDの末尾`|
|ConversationId|1行テキスト|はい|案件リストとの関連付け|
|ChannelId|1行テキスト|いいえ|チャネル確認|
|UserId|1行テキスト|いいえ|利用者確認|
|CaseId|1行テキスト|いいえ|取得できる場合だけ保存|
|ImageToken|1行テキスト|はい|古い分析結果の上書き防止|
|ImageUrl|複数行テキスト・プレーン|はい|Power Appsで表示するURL|
|FileIdentifier|複数行テキスト・プレーン|はい|前画像削除用|
|FileName|1行テキスト|はい|保存ファイル名|
|MimeType|1行テキスト|いいえ|PNG/JPEG確認|
|PixelWidth|数値・小数0桁|いいえ|座標位置計算|
|PixelHeight|数値・小数0桁|いいえ|座標位置計算|
|OverlayJson|複数行テキスト・プレーン|いいえ|最大8個の目印座標とタップ時メッセージ|
|AnalysisNote|複数行テキスト・プレーン|いいえ|画像分析結果の説明|
|AnalysisStatus|1行テキスト|いいえ|状態。Excel取込を簡単にするため選択肢列にしない|
|ImageVersion|数値・小数0桁|はい|Power Appsの再読込判定|
|UserText|複数行テキスト・プレーン|いいえ|画像と同時の質問|
|ExpiresAt|日時|はい|自動削除日時|
|ErrorCode|1行テキスト|いいえ|切り分け用|

`AnalysisStatus` にPAが保存する値：

- `TEMP_SAVED`
- `ANALYZED`
- `NEEDS_REVIEW`
- `VISUAL_OK`
- `ERROR`

選択肢列にしなくても動作します。PAが上記の文字列を書き込みます。

## 3. 画像ごとに一時行を作る理由

`ConversationId` は一意にしません。画像1枚につき一時行を1つ作り、Power Appsは同じ会話の最新行だけを表示します。

この方式にすると、画像を短時間に2枚送った場合でも、1枚目の遅い分析結果が2枚目のURLや座標を上書きしません。古い行と画像は定期削除PAが自動削除します。

## 4. インデックス

リスト設定→インデックス付きの列から、次を追加します。

- `ConversationId`
- `ExpiresAt`
- `CaseId`（過去案件をCaseIdで参照する場合）

## 5. 権限

- PAの接続ユーザー：`AI_TemporaryImages` と `AI_ImageOverlay` の編集権限
- Power Apps利用者：両方の読み取り権限
- 一般利用者へ一時画像ライブラリの編集権限は不要

権限が不足すると、ListsにはURLがあってもPower Appsの画像が空白になります。

## 6. 完了確認

- `AI_TemporaryImages` をブラウザーで開ける
- `AI_ImageOverlay` に上記の列がすべてある
- `ConversationId` がインデックス済み（「一意の値」はオフ）
- Power Apps利用者がライブラリのファイルを読み取れる

