# Copilot Studio導入

変更するのは `4-9-画像分析エージェント_緊急保安` だけです。3-9、入口トピック、エージェント全体指示は変更しません。

## 1. 先に確認すること

- `AI_画像一時保存` が保存済みでオン
- `AI_画像座標更新` が保存済みでオン
- 2本とも同じ環境にある
- SharePoint接続が正常
- PA単体テストで応答が返る

## 2. 2本のPAをツールへ追加

1. Copilot Studioで対象エージェントを開きます。
2. 「ツール」を開きます。
3. 「ツールの追加」→「フロー」を選びます。
4. `AI_画像一時保存` を追加します。
5. `AI_画像座標更新` を追加します。
6. 各ツールの入力と出力が次のとおり表示されることを確認します。

### AI_画像一時保存

入力：

- `text`：conversation_id
- `text_1`：channel_id
- `text_2`：user_id
- `text_3`：user_text
- `text_4`：mime_type
- `file`：image_file

出力：

- `success`
- `record_id`
- `image_token`
- `image_url`
- `image_width`
- `image_height`
- `image_version`
- `error_code`

### AI_画像座標更新

入力：

- `text`：record_id
- `text_1`：image_token
- `text_2`：overlay_json
- `text_3`：analysis_note
- `text_4`：analysis_status

出力：

- `success`
- `error_code`

内部名が異なる場合は、PAのトリガー入力をこの順番で作り直すか、YAMLのbinding名を実際のツール表示へ合わせます。

## 3. フローIDを確認

Power Automateで各フローの詳細画面を開きます。URLの次の部分がフローIDです。

```text
https://make.powerautomate.com/environments/環境ID/flows/ここがフローID/details
```

例：

```text
9a770168-65a8-f111-aaad-7ced8d2f9cab
```

2本のIDをメモします。

## 4. YAMLのIDを置換

[4-9_画像座標対応_フローID置換前.yaml](4-9_画像座標対応_フローID置換前.yaml) をテキストエディターで開きます。

次を検索して実際のIDへ置き換えます。

```text
__FLOW_IMAGE_TEMP_SAVE_ID__
```

→ `AI_画像一時保存` のフローID

```text
__FLOW_IMAGE_OVERLAY_UPDATE_ID__
```

→ `AI_画像座標更新` のフローID

置換後、`__FLOW_` がファイル内に残っていないことを確認します。

## 5. 現在の4-9をバックアップ

1. 「トピック」→ `4-9-画像分析エージェント_緊急保安` を開きます。
2. コードビューを開きます。
3. 全文を別ファイルへ保存します。
4. ファイル名に日付と「導入前」を付けます。

このバックアップがロールバック用です。

## 6. YAMLを貼り替える

1. フローID置換済みYAMLの全文をコピーします。
2. 4-9のコードビューを全選択して置き換えます。
3. 保存します。
4. トピックチェッカーを開きます。

次が0件であることを確認します。

- PowerFxError
- MissingRequiredProperty
- 未解決のflowId
- 未解決の変数
- 重複したアクションID

## 7. file入力でPowerFxErrorになる場合

環境によって、ファイル入力のレコード型名が異なることがあります。該当箇所は次です。

```yaml
file: '={name: Topic.画像ファイル名, contentBytes: First(System.Activity.Attachments).Content}'
```

エラーになる場合だけ、次の手順を使います。

1. デザイナーで「ツールを呼び出す」アクションを一時追加します。
2. `AI_画像一時保存` を選びます。
3. image_fileへ、受信した最初の添付ファイルを指定します。
4. 保存後、コードビューで自動生成された `InvokeFlowAction` の `file:` 行を確認します。
5. その `file:` の値だけを今回のYAMLへ移します。
6. 一時追加した重複アクションを削除します。

この部分はテナント側のツールスキーマで決まるため、Copilot Studioが自動生成した型を優先します。

## 8. 今回追加した安全策

- 画像保存PAをAI分析より先に呼ぶ
- 保存失敗でも画像分析は継続
- 座標は0〜1000の整数
- 1枚で最大8個の措置を別々にマーキング
- 関係ない画像・不鮮明画像には無理に座標を作らない
- 目印JSONが壊れていても従来の5見出しを破棄しない
- 座標は優先度・対応済み判定を変更しない
- 画像トークン一致時だけListsを更新
- 各マーカーにタップ時メッセージを持たせる

## 9. 公開前テスト

Copilot Studioのテスト画面で[テスト手順](../テスト手順.md)をすべて実施します。合格するまで公開しません。

## 10. ロールバック

保存エラーや既存画像分析の回帰が出た場合：

1. 4-9を導入前バックアップへ戻す
2. 保存
3. 2本の新しい画像PAをオフ
4. 既存案件のテキスト・画像分析を再テスト

3-9と既存案件保存PAを変更していないため、ロールバック範囲を限定できます。

