from __future__ import annotations

from datetime import datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "AI_ImageOverlay_Listsインポート用.xlsx"

HEADERS = [
    "Title",
    "ConversationId",
    "ChannelId",
    "UserId",
    "CaseId",
    "ImageToken",
    "ImageUrl",
    "FileIdentifier",
    "FileName",
    "MimeType",
    "PixelWidth",
    "PixelHeight",
    "OverlayJson",
    "AnalysisNote",
    "AnalysisStatus",
    "ImageVersion",
    "UserText",
    "ExpiresAt",
    "ErrorCode",
]

SAMPLE = [
    "DELETE_AFTER_IMPORT",
    "sample-conversation-delete",
    "sample-channel",
    "sample-user",
    "sample-case",
    "sample-token",
    "https://example.invalid/sample.jpg",
    "sample-file-identifier",
    "sample.jpg",
    "image/jpeg",
    1000,
    750,
    '{"version":1,"show":false,"reason":"列作成用サンプル","markers":[]}',
    "この行は列作成用です。Lists作成後に必ず削除してください。",
    "TEMP_SAVED",
    1,
    "列作成用サンプル",
    datetime(2099, 1, 1, 0, 0),
    "SAMPLE_DELETE_ME",
]

COLUMNS = [
    ("Title", "1行テキスト", "標準列", "Listsが最初から持つ列。PAが IMG-xxxxxxxx を保存", "変更不要。サンプル行は取込後に削除"),
    ("ConversationId", "1行テキスト", "重要", "Copilot/Teamsの会話ID。案件と画像を結び付ける", "Power Appsはこの値で最新画像を検索"),
    ("ChannelId", "1行テキスト", "補助", "Teams、Copilot等のチャネル識別", "利用経路の確認用"),
    ("UserId", "1行テキスト", "補助", "画像を投稿した利用者ID", "切り分け用"),
    ("CaseId", "1行テキスト", "将来用", "取得できる場合の案件ID", "空欄でも現在機能は動く"),
    ("ImageToken", "1行テキスト", "重要", "画像ごとの一意トークン", "古い画像結果の誤上書きを防止"),
    ("ImageUrl", "複数行テキスト（プレーン）", "重要", "一時保存画像のURL", "Power Appsの画像コントロールが表示"),
    ("FileIdentifier", "複数行テキスト（プレーン）", "重要", "SharePointファイルの内部識別子", "期限切れ画像の削除に使用"),
    ("FileName", "1行テキスト", "重要", "GUIDで作った保存ファイル名", "利用者の元ファイル名は保存先名に使わない"),
    ("MimeType", "1行テキスト", "補助", "image/png、image/jpeg等", "対応形式確認"),
    ("PixelWidth", "数値（小数0桁）", "重要", "元画像の横ピクセル数", "枠のX座標と幅の計算"),
    ("PixelHeight", "数値（小数0桁）", "重要", "元画像の縦ピクセル数", "枠のY座標と高さの計算"),
    ("OverlayJson", "複数行テキスト（プレーン）", "重要", "最大8個の枠、色、座標、タップ説明", "AI出力をPAが検証して保存"),
    ("AnalysisNote", "複数行テキスト（プレーン）", "表示用", "画像分析の説明文章", "確認・監査用"),
    ("AnalysisStatus", "1行テキスト", "状態", "TEMP_SAVED、ANALYZED等", "Choice列にしなくてよい"),
    ("ImageVersion", "数値（小数0桁）", "重要", "画像・座標の更新番号", "Power Appsの自動再読込判定"),
    ("UserText", "複数行テキスト（プレーン）", "表示用", "画像と同時に送信された質問や報告", "設置候補判断にも使用"),
    ("ExpiresAt", "日付と時刻", "重要", "一時画像の削除予定時刻", "定期削除PAが参照"),
    ("ErrorCode", "1行テキスト", "切分け", "保存・座標・画像寸法エラー", "通常は空欄"),
]


def style_table_sheet(ws, widths):
    ws.freeze_panes = "A2"
    for index, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + index) if index <= 26 else "A"].width = width
    ws.row_dimensions[1].height = 28
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def build():
    wb = Workbook()
    ws = wb.active
    ws.title = "インポート用"
    ws.append(HEADERS)
    ws.append(SAMPLE)
    table = Table(displayName="AI_ImageOverlay_Import", ref=f"A1:S2")
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2",
        showFirstColumn=False,
        showLastColumn=False,
        showRowStripes=True,
        showColumnStripes=False,
    )
    ws.add_table(table)
    widths = [22, 28, 18, 20, 18, 22, 36, 30, 22, 16, 14, 14, 55, 46, 20, 14, 35, 22, 24]
    for col, width in zip(range(1, len(widths) + 1), widths):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = width
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = "A1:S2"
    ws.row_dimensions[1].height = 32
    ws.row_dimensions[2].height = 56
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for cell in ws[2]:
        cell.fill = PatternFill("solid", fgColor="FFF2CC")
        cell.font = Font(color="9C0006", bold=True)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    ws["R2"].number_format = "yyyy/mm/dd hh:mm"
    status_validation = DataValidation(
        type="list",
        formula1='"TEMP_SAVED,ANALYZED,NEEDS_REVIEW,VISUAL_OK,ERROR"',
        allow_blank=True,
    )
    ws.add_data_validation(status_validation)
    status_validation.add("O2:O1048576")
    ws.conditional_formatting.add(
        "A2:S1048576",
        FormulaRule(formula=['$A2="DELETE_AFTER_IMPORT"'], fill=PatternFill("solid", fgColor="FFF2CC")),
    )

    guide = wb.create_sheet("列の種類と用途")
    guide.append(["列名", "Listsで選ぶ種類", "重要度", "用途（何を指すか）", "補足"])
    for row in COLUMNS:
        guide.append(row)
    guide.freeze_panes = "A2"
    guide.auto_filter.ref = f"A1:E{guide.max_row}"
    guide.column_dimensions["A"].width = 24
    guide.column_dimensions["B"].width = 30
    guide.column_dimensions["C"].width = 12
    guide.column_dimensions["D"].width = 54
    guide.column_dimensions["E"].width = 52
    for cell in guide[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in guide.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        if row[2].value == "重要":
            row[2].fill = PatternFill("solid", fgColor="F4CCCC")
        elif row[2].value == "標準列":
            row[2].fill = PatternFill("solid", fgColor="D9EAD3")

    steps = wb.create_sheet("導入手順")
    step_rows = [
        ("このExcelの使い方", "このExcelから新しいMicrosoft Listsを作ります。既存リストへ列だけ追加するExcel取込はできません。"),
        ("1", "今作ったAI_ImageOverlayが空なら、削除する前に本当に項目が0件か確認してください。削除が不安なら残したまま次へ進みます。"),
        ("2", "Microsoft Listsを開き、［新しいリスト］→［Excelから］を選び、このファイルをアップロードします。"),
        ("3", "テーブル AI_ImageOverlay_Import を選びます。"),
        ("4", "列の種類は『列の種類と用途』シートの2列目どおりに選びます。Titleは1行テキストのままで変更不要です。"),
        ("5", "新しいリスト名をAI_ImageOverlay_Importにして一度作成します。既存の空リストと同名にしないためです。"),
        ("6", "作成後、TitleがDELETE_AFTER_IMPORTのサンプル行を1行削除します。"),
        ("7", "列が全部あることを確認します。特にImageUrl、OverlayJson、AnalysisNote、UserTextは複数行テキスト、PixelWidth・PixelHeight・ImageVersionは数値、ExpiresAtは日付と時刻です。"),
        ("8", "既存のAI_ImageOverlayが本当に空なら、既存側をAI_ImageOverlay_old_emptyへ名前変更し、Excelから作った側をAI_ImageOverlayへ名前変更します。"),
        ("9", "Power Automateでは、列が揃った新しいAI_ImageOverlayを選びます。古い空リストを選ばないでください。"),
        ("Titleについて", "TitleはLists標準列なので、編集画面で名前変更程度しか見えないのが正常です。型変更は不要です。PAがIMG-xxxxxxxxを保存します。"),
        ("AnalysisStatusについて", "選択肢列にしなくて構いません。1行テキストにするとExcel取込とPA設定が簡単です。"),
        ("注意", "このExcelのサンプルURLは実在しません。DELETE_AFTER_IMPORT行は必ず削除してください。"),
    ]
    steps.append(["項目", "説明"])
    for item, explanation in step_rows:
        steps.append([item, explanation])
    steps.column_dimensions["A"].width = 24
    steps.column_dimensions["B"].width = 105
    steps.freeze_panes = "A2"
    for cell in steps[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center")
    thin = Side(style="thin", color="D9E1F2")
    for row in steps.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row in range(2, steps.max_row + 1):
        steps.row_dimensions[row].height = 44
    steps["A11"].fill = PatternFill("solid", fgColor="D9EAD3")
    steps["A12"].fill = PatternFill("solid", fgColor="D9EAD3")
    steps["A13"].fill = PatternFill("solid", fgColor="F4CCCC")

    mapping = wb.create_sheet("PAとの対応")
    mapping.append(["PA処理", "Lists列", "保存する値", "利用先"])
    mapping_rows = [
        ("画像一時保存", "ConversationId", "System.Conversation.Id", "Power Appsで案件と画像を結合"),
        ("画像一時保存", "ImageUrl", "SharePointに保存した画像URL", "Power Appsの画像表示"),
        ("画像一時保存", "PixelWidth / PixelHeight", "画像ピクセル寸法", "縦横比を維持した座標計算"),
        ("画像一時保存", "ImageToken", "guid()", "画像結果の取り違え防止"),
        ("画像座標更新", "OverlayJson", "AIの検証済み座標JSON", "最大8個の枠とタップ説明"),
        ("画像座標更新", "AnalysisNote", "画像分析の説明", "確認・監査"),
        ("画像座標更新", "ImageVersion", "既存値+1", "Power Appsの自動更新"),
        ("一時画像削除", "ExpiresAt", "削除予定時刻", "期限切れ判定"),
        ("一時画像削除", "FileIdentifier", "SharePoint内部ID", "画像ファイル削除"),
    ]
    for row in mapping_rows:
        mapping.append(row)
    mapping.freeze_panes = "A2"
    mapping.column_dimensions["A"].width = 24
    mapping.column_dimensions["B"].width = 30
    mapping.column_dimensions["C"].width = 46
    mapping.column_dimensions["D"].width = 46
    for cell in mapping[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in mapping.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    wb.save(OUTPUT)

    check = load_workbook(OUTPUT, data_only=False)
    assert check.sheetnames == ["インポート用", "列の種類と用途", "導入手順", "PAとの対応"]
    assert check["インポート用"].max_column == len(HEADERS)
    assert check["インポート用"]["A2"].value == "DELETE_AFTER_IMPORT"
    assert "AI_ImageOverlay_Import" in check["インポート用"].tables
    print(f"created: {OUTPUT}")


if __name__ == "__main__":
    build()
