from __future__ import annotations

from datetime import datetime
from pathlib import Path

import xlsxwriter
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "AI_ImageOverlay_Listsインポート用_v2.xlsx"

HEADERS = [
    "Title", "ConversationId", "ChannelId", "UserId", "CaseId",
    "ImageToken", "ImageUrl", "FileIdentifier", "FileName", "MimeType",
    "PixelWidth", "PixelHeight", "OverlayJson", "AnalysisNote",
    "AnalysisStatus", "ImageVersion", "UserText", "ExpiresAt", "ErrorCode",
]

SAMPLE = [
    "DELETE_AFTER_IMPORT", "sample-conversation-delete", "sample-channel",
    "sample-user", "sample-case", "sample-token",
    "https://example.invalid/sample.jpg", "sample-file-identifier",
    "sample.jpg", "image/jpeg", 1000, 750,
    '{"version":1,"show":false,"reason":"列作成用サンプル","markers":[]}',
    "この行は列作成用です。Lists作成後に必ず削除してください。",
    "TEMP_SAVED", 1, "列作成用サンプル", datetime(2099, 1, 1, 0, 0),
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

STEPS = [
    ("このExcelの使い方", "このExcelから新しいMicrosoft Listsを作ります。既存リストへ列だけ追加するExcel取込はできません。"),
    ("1", "今作ったAI_ImageOverlayが空なら、削除する前に本当に項目が0件か確認してください。削除が不安なら残したまま次へ進みます。"),
    ("2", "Microsoft Listsを開き、［新しいリスト］→［Excelから］を選び、このファイルをアップロードします。"),
    ("3", "テーブル AI_ImageOverlay_Import を選びます。"),
    ("4", "列の種類は『列の種類と用途』シートの2列目どおりに選びます。Titleは1行テキストのままで変更不要です。"),
    ("5", "新しいリスト名をAI_ImageOverlay_Importにして一度作成します。既存の空リストと同名にしないためです。"),
    ("6", "作成後、TitleがDELETE_AFTER_IMPORTのサンプル行を1行削除します。"),
    ("7", "列を確認します。ImageUrl、OverlayJson、AnalysisNote、UserTextは複数行テキスト、PixelWidth・PixelHeight・ImageVersionは数値、ExpiresAtは日付と時刻です。"),
    ("8", "既存のAI_ImageOverlayが本当に空なら、既存側をAI_ImageOverlay_old_emptyへ名前変更し、Excelから作った側をAI_ImageOverlayへ名前変更します。"),
    ("9", "Power Automateでは、列が揃った新しいAI_ImageOverlayを選びます。古い空リストを選ばないでください。"),
    ("Titleについて", "TitleはLists標準列なので、編集画面で名前変更程度しか見えないのが正常です。型変更は不要です。PAがIMG-xxxxxxxxを保存します。"),
    ("AnalysisStatusについて", "選択肢列にしなくて構いません。1行テキストにするとExcel取込とPA設定が簡単です。"),
    ("注意", "このExcelのサンプルURLは実在しません。DELETE_AFTER_IMPORT行は必ず削除してください。"),
]

MAPPING = [
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


def add_plain_sheet(workbook, worksheet, headers, rows, widths):
    header_format = workbook.add_format({
        "bold": True, "font_color": "white", "bg_color": "#1F4E78",
        "align": "center", "valign": "vcenter", "text_wrap": True,
        "border": 1, "border_color": "#D9E1F2",
    })
    body_format = workbook.add_format({
        "valign": "top", "text_wrap": True,
        "border": 1, "border_color": "#D9E1F2",
    })
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)
        worksheet.set_column(col, col, widths[col])
    for row_index, row in enumerate(rows, start=1):
        for col_index, value in enumerate(row):
            worksheet.write(row_index, col_index, value, body_format)
        worksheet.set_row(row_index, 42)
    worksheet.set_row(0, 28)
    worksheet.freeze_panes(1, 0)


def build():
    workbook = xlsxwriter.Workbook(OUTPUT)
    workbook.set_properties({
        "title": "AI_ImageOverlay Microsoft Lists import template",
        "author": "Codex",
        "comments": "Generated with XlsxWriter for Microsoft Lists import compatibility",
    })

    import_sheet = workbook.add_worksheet("インポート用")
    header_format = workbook.add_format({
        "bold": True, "font_color": "white", "bg_color": "#1F4E78",
        "align": "center", "valign": "vcenter", "text_wrap": True,
    })
    sample_format = workbook.add_format({
        "bold": True, "font_color": "#9C0006", "bg_color": "#FFF2CC",
        "valign": "top", "text_wrap": True,
    })
    sample_date_format = workbook.add_format({
        "bold": True, "font_color": "#9C0006", "bg_color": "#FFF2CC",
        "num_format": "yyyy/mm/dd hh:mm", "valign": "top",
    })
    widths = [22, 28, 18, 20, 18, 22, 36, 30, 22, 16, 14, 14, 55, 46, 20, 14, 35, 22, 24]
    for col, (header, width) in enumerate(zip(HEADERS, widths)):
        import_sheet.write(0, col, header, header_format)
        import_sheet.set_column(col, col, width)
    for col, value in enumerate(SAMPLE):
        if isinstance(value, datetime):
            import_sheet.write_datetime(1, col, value, sample_date_format)
        else:
            import_sheet.write(1, col, value, sample_format)
    import_sheet.set_row(0, 30)
    import_sheet.set_row(1, 56)
    import_sheet.freeze_panes(1, 0)
    # The table supplies its own filter. Do not add a worksheet-level autofilter.
    import_sheet.add_table(0, 0, 1, len(HEADERS) - 1, {
        "name": "AI_ImageOverlay_Import",
        "style": "Table Style Medium 2",
        "columns": [{"header": header} for header in HEADERS],
    })
    guide = workbook.add_worksheet("列の種類と用途")
    add_plain_sheet(workbook, guide,
        ["列名", "Listsで選ぶ種類", "重要度", "用途（何を指すか）", "補足"],
        COLUMNS, [24, 30, 12, 54, 52])

    steps = workbook.add_worksheet("導入手順")
    add_plain_sheet(workbook, steps, ["項目", "説明"], STEPS, [24, 105])

    mapping = workbook.add_worksheet("PAとの対応")
    add_plain_sheet(workbook, mapping,
        ["PA処理", "Lists列", "保存する値", "利用先"],
        MAPPING, [24, 30, 46, 46])

    workbook.close()

    check = load_workbook(OUTPUT, data_only=False)
    assert check.sheetnames == ["インポート用", "列の種類と用途", "導入手順", "PAとの対応"]
    assert check["インポート用"].max_column == len(HEADERS)
    assert check["インポート用"]["A2"].value == "DELETE_AFTER_IMPORT"
    assert "AI_ImageOverlay_Import" in check["インポート用"].tables
    print(f"created: {OUTPUT}")


if __name__ == "__main__":
    build()
