# 新規・変更式のMicrosoft Power Fx検証

Microsoft.PowerFx.Interpreter 1.8.1と.NET 8 SDKを使用する。今回の開発環境のSDKは/tmp/subaru-dotnet（8.0.426）。

```bash
python SUBARU_optimized/validation/native_restart/run.py --dotnet /tmp/subaru-dotnet/dotnet
```

固定バージョンのNuGet依存をapi.nuget.orgから/tmpへ取得し、Roslynでコンパイルする。制限された環境のNuGet CLIの名前付きmutexを使わない。Program.csが変更・追加された20式の構文・型を確認し、45種類の番号入力を実際のPower Fxライブラリで評価する。

標準入力型はTopicの既存Stringと既存の目的再試行回数Number。AIへ問い合わせる試験ではない。自由文が番号パーサーで空文字になるケースは、入口のAI意味判定へ渡す設計の確認であり、AIが正しく分類した証拠ではない。

スタンドアロンライブラリの成功はCopilot Studioの読込・型推論・実会話の成功を保証しない。results.jsonのsource_sha256は検査したYAMLとの対応を示す。大きな既存プロンプトも確認するため検証上の式長上限を1,000,000文字にしているが、Studioの上限を意味しない。
