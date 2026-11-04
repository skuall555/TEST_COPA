# Teams 現場アドバイザー改修パック｜2026-11-04

**コード修正完了／本番動作未検証。** 既存Copilot Studioエージェントをスマホ版Teamsから使い、事務所の既存Power Appsへ記録を引き継ぐための差分改修です。新しいエージェントや現場用Power Appsは作りません。

このZIPは**改修ソース・YAML全文・設定生成ツール・手順・検証結果の配布用**です。Copilot StudioへそのままインポートできるMicrosoftソリューションZIPではありません。[導入手順](docs/導入手順.md)に従い、実環境の定義を確認して適用してください。

| 内容 | ファイル |
|---|---|
| 読む順序・設定方法 | [導入手順](docs/導入手順.md) |
| Teamsだけ保存されない問題の切り分け | [保存経路の調査](docs/保存経路の調査.md) |
| 現行経路・変更箇所・制限 | [調査と設計](docs/調査と設計.md) |
| 修正後3トピック | `topics/*.yaml`（省略なし）／[コードブロック版](docs/YAML全文.md) |
| エージェントの「指示」 | `topics/エージェント指示_Teams追記.txt`（既存指示を含む全文） |
| 変更前バックアップ | `source/`（基準コミット `4fa63fb`） |
| 差分 | `validation/*.diff` |
| SharePoint保存フロー定義の生成 | `tools/flow_definition.py`、[契約](docs/保存フロー契約.md) |
| 実値設定のひな形 | `contracts/deployment.example.json`（未確認値はnull） |
| 互換性・検証・未実施項目 | [検証結果](docs/検証結果.md)、`validation/` |

Teamsには①前回との差分（初回省略）、②高・中・低、③確認事項、④次の行動を表示します。SharePointに渡す現場回答は従来の7見出しを維持します。修理の最終回答と追加質問は表示文と同文を保存経路へ渡し、写真や現場続報で元の現場処理へ戻せます。

`topics/` は既存の保存フローID・入力契約を維持した互換版です。**これだけではTeamsの保存不具合の解決、永続的な前回比較、修理レコードのApps除外は保証できません。** 実際のフロー本体・SharePoint列・Power Apps式が提供されていないためです。確認後、既存保存フローを直すか、同じエージェントから呼ぶ保存アダプターに結び付けます。生成した接続版は別ディレクトリへ出力します。

1. 既存ソリューション、保存フロー、リスト列定義、Apps式を取得する。
2. 保存問題を切り分け、列・案件ID・保存方式・権限を確認する。
3. テスト環境へYAMLと必要な保存処理を適用する。
4. スマホTeams・SharePoint・既存Appsで受入テストを行い、同じエージェントを公開する。

再生成・ローカル検証（Python 3.12、PyYAML、Power Fx検証には.NET 8 SDK）：

```bash
python -m pip install -r requirements-dev.txt
python tools/build_topics.py
python tools/build_images.py
python -m unittest discover -s tests -p 'test_*.py' -v
python tools/native/run.py --dotnet /absolute/path/to/dotnet
```

`tests/fixtures.py` の値は模擬テスト専用です。接続設定へ転用しないでください。テナントの機密情報・実写真・認証情報はこの配布物に含めていません。実行できた検証の範囲は検証結果に記載しています。
