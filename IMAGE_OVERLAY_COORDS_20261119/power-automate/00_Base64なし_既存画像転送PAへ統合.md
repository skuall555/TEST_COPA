# Base64を使わない修正手順

## 結論

画像ファイルをCopilot StudioからPower Automateへ送り返しません。

Power Appsから画像をCopilot Studioへ渡している既存PA内で、同じ受信ファイルを次の2か所へ直接マップします。

1. SharePointの「ファイルの作成」
2. 既存の「Copilot Studioへ画像を渡す」アクション

`base64()`、`base64ToBinary()`、`JSONFormat.IncludeBinaryData` は追加しません。
既存PAが受け取ったファイル動的コンテンツをそのまま再利用します。

## 残すもの・使わないもの

| 対象 | 扱い |
|---|---|
| 既存のPower Apps→Copilot Studio画像転送PA | これを修正して使う |
| `AI_画像座標更新_v3` | 残す。JSONなどのテキストだけを受け取る |
| `AI_画像一時保存_v3` | Copilot Studioツールからは呼ばない。公開テスト完了まで削除せずオフで保持 |
| `AI_エージェント可視化` | 既存リストと追加済12列をそのまま使う |
| 4-9画像分析 | 画像は従来どおり `First(System.Activity.Attachments).Content` をAI Builderへ直接渡す |

## 1. 既存画像転送PAの最初に3つの作成を追加

画像ファイルを受け取るトリガーの直後、Copilot Studioを呼び出す前に追加します。

### Compose_ImageToken

```text
@concat('aio_', guid())
```

### Compose_ImageExtension

`mime_type` は既存PAが受け取っているMIMEタイプの動的コンテンツを選びます。

```text
@if(
  contains(toLower(coalesce(triggerBody()?['mime_type'], '')), 'png'),
  '.png',
  '.jpg'
)
```

実際のトリガー内部名が `mime_type` でない場合、式を手打ちせずMIMEタイプの動的コンテンツを挿入します。

### Compose_ImageFileName

```text
@concat(outputs('Compose_ImageToken'), outputs('Compose_ImageExtension'))
```

## 2. 既存案件行を検索

「SharePoint－複数の項目の取得」を追加します。

- リスト：`AI_エージェント可視化`
- 上から順に取得：`Modified desc`
- 取得数：`1`

```text
@concat(
  'ConversationId eq ''',
  replace(<既存PAのconversation_id動的コンテンツ>,'''',''''''),
  ''''
)
```

`<...>` は文字として貼らず、既存PAの `conversation_id` 動的コンテンツを挿入します。
行が0件の場合は画像分析だけ続行し、画像ファイルと目印は保存しません。空の案件行は作りません。

## 3. SharePointへ同じ画像ファイルを保存

行が1件見つかった場合だけ「SharePoint－ファイルの作成」を実行します。

- ライブラリ：作成済みの一時画像ライブラリ
- ファイル名：`Compose_ImageFileName`
- ファイルコンテンツ：Power Appsトリガーで受け取った既存の画像ファイルの動的コンテンツ

この欄に式は入れません。`base64ToBinary(...)` も入れません。

## 4. 幅・高さとURLを取得

現在の `AI_画像一時保存_v3` で作成済みの次のアクションは、削除せず既存画像転送PAへコピーして再利用できます。

- ファイルのプロパティ取得
- SharePointへのHTTP要求
- ImageWidth / ImageHeightの作成
- 画像URLの作成

コピー後は参照元を「今回追加したファイルの作成」へ結び直します。

## 5. `AI_エージェント可視化` の同じ行を更新

次の画像列だけを更新します。優先度、CaseId、Status、ユーザー回答は変更しません。

| 列 | 値 |
|---|---|
| ImageToken | `Compose_ImageToken` |
| ImageUrl | 作成した画像のURL |
| ImageFileIdentifier | ファイルのIdentifier |
| ImagePixelWidth | 取得した幅 |
| ImagePixelHeight | 取得した高さ |
| ImageOverlayJson | `{"version":1,"show":false,"reason":"分析中","markers":[]}` |
| ImageAnalysisNote | `画像分析中` |
| ImageAnalysisStatus | `TEMP_SAVED` |
| ImageVersion | 既存値+1 |
| ImageUserText | Power Appsから受け取った `user_text` |
| ImageExpiresAt | `addHours(utcNow(),24)` |
| ImageErrorCode | 空文字 |

## 6. Copilot Studioへ送るファイル名だけ変更

既存のCopilot Studio呼び出しアクションで、画像のマップを次のようにします。

- ファイル名：`Compose_ImageFileName`
- ファイル内容：従来と同じPower Appsトリガーの画像ファイル動的コンテンツ
- MIMEタイプ：従来と同じ値

画像本体は変換しません。ファイル名を `aio_<GUID>.<拡張子>` にすることで、
4-9とListsが同じ画像をトークンで照合できます。

## 7. 4-9と座標更新PA

- 4-9は添付名が `aio_` で始まる場合だけ座標保存を行う
- 添付のファイル本体は従来どおりAI Builderへ直接渡す
- `AI_画像座標更新_v3` の1番目入力 `record_id` には `System.Conversation.Id` を渡す
- 2番目入力 `image_token` には添付名の拡張子を除いた `aio_<GUID>` を渡す
- 座標更新PAは `ConversationId` と `ImageToken` の両方が一致する行だけを更新する

トリガーの入力名・順番は変えないため、Copilot Studioでツールが再生成されることを避けられます。

## 8. 失敗時の動作

- SharePoint保存失敗：従来の画像分析と回答は続行。Power Appsの画像と目印だけ非表示
- 座標JSON不正：安全な空JSONを保存し、回答は継続
- トークン不一致：古い画像結果で最新画像を上書きしない
- Teamsから直接送信され、`aio_` トークンを持たない画像：従来の分析と回答は実行し、Power Apps用目印保存だけ行わない

## 9. 公開順

1. 既存画像転送PAのコピーを作る
2. コピ側に上記処理を追加
3. PA単体テストで、ファイル名が `aio_`、ListsのImageTokenが同値であることを確認
4. `AI_画像座標更新_v3` の内部検索をConversationId+ImageToken版へ変更
5. 4-9をBase64なし版へ貼り替え
6. Power Appsから1枚の画像で端から端までテスト
7. ListsとPower Appsの目印が正しいことを確認してから公開

`AI_画像一時保存_v3` はこのテスト完了後にオフにします。すぐに削除しません。
