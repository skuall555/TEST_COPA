# Microsoft Power Fxによる検証

Microsoft.PowerFx.Interpreter **1.8.1** を使い、3-9の優先度関連式について構文・型・代入先との整合を検査し、16ケースの模擬AI応答から式を実行する。Copilot Studioのホスト、実モデルの分類、画像認識の試験ではない。

```bash
python SUBARU_optimized/validation/native_powerfx/run.py --dotnet /tmp/subaru-dotnet/dotnet
```

.NET 8 SDKとPython／PyYAMLが必要。今回は.NET SDK 8.0.426を/tmp/subaru-dotnetへ導入した。SDKやDLLをGitへ保存していない。別環境では--dotnetに実際の実行ファイルを指定する。Power Fxと依存する固定バージョンのNuGetパッケージをapi.nuget.orgから取得し、/tmp/subaru-native-powerfxへ展開してRoslynでコンパイルする。NuGet CLIの名前付きmutexを使わないため、制限された環境でも実行できる。

- Program.cs：Microsoftライブラリによる型チェックと式の実行。
- run.py：保存済みYAMLからの抽出、固定パッケージ取得、コンパイル、実行、結果保存。
- cases.py：16ケースの模擬AI応答と期待値。外部モデルを呼び出さない。
- results.json：今回の結果と対象YAMLのSHA-256。
- baseline_939ce9c_results.json：前版150式もスタンドアロンでは通ったという調査結果。前版のStudio読込が成功した証拠ではない。
- check.csproj：通常の.NET開発環境向けのパッケージ参照。

式の長さの検証上限は1,000,000文字に設定している。Copilot Studioに同じ上限があるという意味ではない。Topic／Globalの型は明示入力とSetVariable式から推定する。この型推定手順もStudioの実装を再現したものではない。

検証結果の「成功」はこの検証範囲だけを指す。Studioのトピックチェッカー、実機の状態遷移、モデルによる正しい意味解釈は別途確認が必要。
