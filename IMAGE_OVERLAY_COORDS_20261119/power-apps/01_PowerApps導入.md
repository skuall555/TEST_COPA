# Power Apps導入

SharePointの画像URLを表示し、その上に最大8個の色枠を重ねます。枠をタップすると、その措置についてAIが確認した内容と残る対応を表示します。

## 1. データソースを追加

1. Power Apps Studioで対象アプリを編集します。
2. 「データ」→「データの追加」→「SharePoint」を選びます。
3. 対象サイトへ接続します。
4. `AI_ImageOverlay` を追加します。

`AI_TemporaryImages` ライブラリをデータソースとして追加する必要はありません。画像は `ImageUrl` から表示します。

## 2. 前提となる案件変数

この手順では、現在表示中の案件レコードを `varSelectedCase` と呼びます。

現在のアプリで別名を使っている場合は、以下の式にある `varSelectedCase` を実際の変数名へ置き換えてください。必要なのは既存案件行の `ConversationId` です。

## 3. 画像データ読込用の非表示ボタン

対象の詳細画面へクラシックボタンを1つ追加し、名前を `btnLoadImageOverlay` にします。

- Visible：`false`
- OnSelect：次の式

```powerfx
Refresh(AI_ImageOverlay);

Set(
    varImageRecord,
    First(
        SortByColumns(
            Filter(
                AI_ImageOverlay,
                ConversationId = Text(varSelectedCase.ConversationId)
            ),
            "Created",
            SortOrder.Descending
        )
    )
);

Set(varSourceW, Value(Coalesce(varImageRecord.PixelWidth, 0)));
Set(varSourceH, Value(Coalesce(varImageRecord.PixelHeight, 0)));
Set(varLoadedImageVersion, Value(Coalesce(varImageRecord.ImageVersion, 0)));
Set(varOverlayLoadError, false);
Set(varOverlayReason, "");
Set(varMarkerPanelVisible, false);
Set(varSelectedMarker, Blank());
Clear(colImageMarkers);

If(
    !IsBlank(varImageRecord.OverlayJson),
    IfError(
        Set(varOverlayReason, Text(ParseJSON(varImageRecord.OverlayJson).reason));
        ClearCollect(
            colImageMarkers,
            FirstN(
                ForAll(
                    Table(ParseJSON(varImageRecord.OverlayJson).markers) As JsonRow,
                    With(
                        {
                            J: JsonRow.Value,
                            NX1: Value(JsonRow.Value.x1),
                            NY1: Value(JsonRow.Value.y1),
                            NX2: Value(JsonRow.Value.x2),
                            NY2: Value(JsonRow.Value.y2),
                            NType: Text(JsonRow.Value.type),
                            NColor: Text(JsonRow.Value.color)
                        },
                        {
                            MarkerId: Text(J.id),
                            MarkerType: NType,
                            MarkerColor: NColor,
                            Target: Text(J.target),
                            MsId: Text(J.msId),
                            Label: Text(J.label),
                            X1: NX1,
                            Y1: NY1,
                            X2: NX2,
                            Y2: NY2,
                            Confidence: Text(J.confidence),
                            Basis: Text(J.basis),
                            Message: Text(J.message),
                            IsValid:
                                NX1 >= 0 && NX1 < NX2 && NX2 <= 1000 &&
                                NY1 >= 0 && NY1 < NY2 && NY2 <= 1000 &&
                                (
                                    (NType = "observed" && NColor = "green") ||
                                    (NType = "uncertain" && NColor = "yellow") ||
                                    (NType = "candidate" && NColor = "blue")
                                )
                        }
                    )
                ),
                8
            )
        ),
        Set(varOverlayLoadError, true);
        Set(varOverlayReason, "目印データを読み込めませんでした");
        Clear(colImageMarkers)
    )
);

ClearCollect(
    colValidImageMarkers,
    Filter(colImageMarkers, IsValid)
);
ClearCollect(colImageMarkers, colValidImageMarkers);
Clear(colValidImageMarkers)
```

この式は、JSONが壊れている場合や座標が範囲外の場合に、画像は表示して枠だけを消します。

## 4. 画面表示時に読み込む

対象画面の `OnVisible` の最後に追加します。

```powerfx
Select(btnLoadImageOverlay)
```

すでにOnVisibleへ式がある場合は、既存式を消さず、末尾へセミコロンを付けて追加します。

## 5. 手動レイアウトコンテナ

1. 「挿入」→「レイアウト」から、手動でX/Yを指定できる通常コンテナを追加します。
2. 名前を `conImageOverlay` にします。
3. 自動レイアウトの縦・横コンテナは使わないでください。子コントロールのX/Yが無効になるためです。

推奨サイズ：

```powerfx
Width  = Parent.Width
Height = Min(Parent.Height * 0.55, 620)
```

## 6. 元画像コントロール

`conImageOverlay` の中へ画像コントロールを追加し、名前を `imgOverlayPhoto` にします。

```powerfx
Image         = If(IsBlank(varImageRecord), Blank(), varImageRecord.ImageUrl)
ImagePosition = ImagePosition.Fit
X             = 0
Y             = 0
Width         = Parent.Width
Height        = Parent.Height
Visible       = !IsBlank(varImageRecord.ImageUrl)
```

`ImagePosition.Fit` を必ず使用します。後述の式が上下または左右の余白を計算し、元画像との座標を合わせます。

## 7. タップ可能な目印1を追加

`conImageOverlay` の中へクラシックボタンを追加し、名前を `btnMarker1` にします。画像コントロールより前面へ移動します。

### Visible

```powerfx
If(
    CountRows(colImageMarkers) < 1,
    false,
    varSourceW > 0 && varSourceH > 0 && Index(colImageMarkers, 1).IsValid
)
```

### X

```powerfx
If(
    CountRows(colImageMarkers) < 1 || varSourceW <= 0 || varSourceH <= 0,
    0,
    With(
        {
            M: Index(colImageMarkers, 1),
            S: Min(imgOverlayPhoto.Width / varSourceW, imgOverlayPhoto.Height / varSourceH)
        },
        imgOverlayPhoto.X +
        (imgOverlayPhoto.Width - varSourceW * S) / 2 +
        (M.X1 / 1000) * (varSourceW * S)
    )
)
```

### Y

```powerfx
If(
    CountRows(colImageMarkers) < 1 || varSourceW <= 0 || varSourceH <= 0,
    0,
    With(
        {
            M: Index(colImageMarkers, 1),
            S: Min(imgOverlayPhoto.Width / varSourceW, imgOverlayPhoto.Height / varSourceH)
        },
        imgOverlayPhoto.Y +
        (imgOverlayPhoto.Height - varSourceH * S) / 2 +
        (M.Y1 / 1000) * (varSourceH * S)
    )
)
```

### Width

```powerfx
If(
    CountRows(colImageMarkers) < 1 || varSourceW <= 0,
    0,
    With(
        {
            M: Index(colImageMarkers, 1),
            S: Min(imgOverlayPhoto.Width / varSourceW, imgOverlayPhoto.Height / varSourceH)
        },
        ((M.X2 - M.X1) / 1000) * (varSourceW * S)
    )
)
```

### Height

```powerfx
If(
    CountRows(colImageMarkers) < 1 || varSourceH <= 0,
    0,
    With(
        {
            M: Index(colImageMarkers, 1),
            S: Min(imgOverlayPhoto.Width / varSourceW, imgOverlayPhoto.Height / varSourceH)
        },
        ((M.Y2 - M.Y1) / 1000) * (varSourceH * S)
    )
)
```

### Fill

```powerfx
If(
    CountRows(colImageMarkers) < 1,
    RGBA(0, 0, 0, 0),
    Switch(
        Index(colImageMarkers, 1).MarkerType,
        "observed",  RGBA(38, 166, 91, 0.20),
        "uncertain", RGBA(255, 193, 7, 0.24),
        "candidate", RGBA(24, 111, 194, 0.20),
        RGBA(0, 0, 0, 0)
    )
)
```

### BorderColor

```powerfx
If(
    CountRows(colImageMarkers) < 1,
    RGBA(0, 0, 0, 0),
    Switch(
        Index(colImageMarkers, 1).MarkerType,
        "observed",  RGBA(24, 111, 67, 1),
        "uncertain", RGBA(180, 110, 0, 1),
        "candidate", RGBA(22, 100, 154, 1),
        RGBA(80, 80, 80, 1)
    )
)
```

その他：

```powerfx
BorderThickness = 3
Color           = RGBA(20, 20, 20, 1)
FontWeight      = FontWeight.Semibold
Size            = 11
Text            = If(Self.Width >= 110 && Self.Height >= 38, Index(colImageMarkers, 1).Label, "ⓘ")
Tooltip         = Index(colImageMarkers, 1).Label & Char(10) & Index(colImageMarkers, 1).Basis
OnSelect        = Set(varSelectedMarker, Index(colImageMarkers, 1)); Set(varMarkerPanelVisible, true)
```

## 8. 目印2〜8を複製

`btnMarker1` を7回複製し、次の名前にします。

- `btnMarker2`
- `btnMarker3`
- `btnMarker4`
- `btnMarker5`
- `btnMarker6`
- `btnMarker7`
- `btnMarker8`

各複製の数式にある次の2か所の数字を、そのボタン番号へ変更します。

```powerfx
CountRows(colImageMarkers) < 1
Index(colImageMarkers, 1)
```

例えば `btnMarker4` は次のようにします。

```powerfx
CountRows(colImageMarkers) < 4
Index(colImageMarkers, 4)
```

すべてのプロパティで番号を変更してください。これで1枚にポケット警報器、検知器調査、窓開け換気、火気厳禁表示、消火器などが同時に写っていても別々に表示できます。

## 9. タップ時の説明パネル

画面の最前面へコンテナを追加し、名前を `conMarkerMessage` にします。

```powerfx
Visible = varMarkerPanelVisible && !IsBlank(varSelectedMarker)
Fill    = RGBA(255, 255, 255, 0.98)
```

説明パネルには次を配置します。

### タイトル `lblMarkerTitle`

```powerfx
Text = varSelectedMarker.Label
Size = 18
```

### 種類 `lblMarkerType`

```powerfx
Text = Switch(
    varSelectedMarker.MarkerType,
    "observed", "画像で確認した対象",
    "uncertain", "追加確認が必要な対象",
    "candidate", "設置・操作の候補",
    ""
) & If(IsBlank(varSelectedMarker.MsId), "", "　" & varSelectedMarker.MsId)
```

### 本文 `lblMarkerMessage`

```powerfx
Text = varSelectedMarker.Message
Size = 16
AutoHeight = true
```

### AIの画像根拠 `lblMarkerBasis`

```powerfx
Text = "AIが画像で見た根拠：" & varSelectedMarker.Basis
Size = 14
AutoHeight = true
```

### 閉じるアイコン

```powerfx
OnSelect = Set(varMarkerPanelVisible, false); Set(varSelectedMarker, Blank())
```

## 10. 画像下の目印一覧

画像の枠が重なった場合や小さすぎる場合でも説明を選べるよう、縦ギャラリー `galMarkerList` を画像の下へ追加します。

```powerfx
Items = colImageMarkers
Visible = CountRows(colImageMarkers) > 0
```

ギャラリー内のボタン：

```powerfx
Text = ThisItem.Label
Fill = Switch(
    ThisItem.MarkerType,
    "observed",  RGBA(221, 244, 230, 1),
    "uncertain", RGBA(255, 242, 206, 1),
    "candidate", RGBA(220, 238, 252, 1),
    RGBA(240, 240, 240, 1)
)
OnSelect = Set(varSelectedMarker, ThisItem); Set(varMarkerPanelVisible, true)
```

## 11. エラー・非表示メッセージ

画像の下へラベル `lblOverlayNotice` を追加します。

```powerfx
Text = If(
    varOverlayLoadError,
    "AIの目印データを読み込めなかったため、画像だけを表示しています。",
    varSourceW <= 0 || varSourceH <= 0,
    "画像サイズを取得できなかったため、位置ずれ防止のため目印を表示していません。",
    CountRows(colImageMarkers) = 0,
    If(
        IsBlank(varOverlayReason),
        "この画像には表示対象の目印がありません。詳しくは画像分析結果を確認してください。",
        "目印なし：" & varOverlayReason
    ),
    "色枠をタップすると、AIの確認根拠と残る対応を表示します。"
)
```

## 12. 自動更新タイマー

画像分析中にPower Appsを開いた場合でも、完了後に自動更新するためタイマー `tmrImageOverlayRefresh` を追加します。

```powerfx
Duration  = 5000
Repeat    = true
AutoStart = true
Visible   = false
OnTimerEnd =
    Refresh(AI_ImageOverlay);
    With(
        {
            LatestImage: First(
                SortByColumns(
                    Filter(
                        AI_ImageOverlay,
                        ConversationId = Text(varSelectedCase.ConversationId)
                    ),
                    "Created",
                    SortOrder.Descending
                )
            )
        },
        If(
            !IsBlank(LatestImage) &&
            (
                LatestImage.ID <> Coalesce(varImageRecord.ID, 0) ||
                Value(Coalesce(LatestImage.ImageVersion, 0)) <> varLoadedImageVersion
            ),
            Select(btnLoadImageOverlay)
        )
    )
```

本番負荷が気になる場合は、画面を離れたらタイマーを停止するか、Durationを10000〜15000へ変更します。

## 13. 重要な表示条件

- 自動レイアウトコンテナ内へ目印ボタンを直接入れない
- `imgOverlayPhoto.ImagePosition` は `Fit`
- PixelWidthまたはPixelHeightが0なら枠を出さない
- 画像URLが変わったら必ず最新行を再読込
- 枠の判定だけで優先度表示を変更しない
- 目印メッセージはAIの説明であり、最終判断は担当者が行う

