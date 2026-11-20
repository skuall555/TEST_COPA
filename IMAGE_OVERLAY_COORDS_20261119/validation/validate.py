from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "copilot" / "4-9_画像座標対応_フローID置換前.yaml"
FINAL_YAML_PATH = ROOT / "copilot" / "4-9_画像座標対応_フローID設定済み.yaml"
DIALOG_YAML_PATH = ROOT / "copilot" / "4-9_画像座標対応_ツールdialog設定済み.yaml"
EXAMPLE_PATH = ROOT / "overlay.example.multiple.json"


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def validate_marker(marker: dict[str, Any]) -> None:
    required = {
        "id",
        "type",
        "color",
        "target",
        "msId",
        "label",
        "x1",
        "y1",
        "x2",
        "y2",
        "confidence",
        "basis",
        "message",
    }
    missing = required - marker.keys()
    assert not missing, f"marker missing: {sorted(missing)}"
    assert 0 <= marker["x1"] < marker["x2"] <= 1000
    assert 0 <= marker["y1"] < marker["y2"] <= 1000
    expected_color = {
        "observed": "green",
        "uncertain": "yellow",
        "candidate": "blue",
    }
    assert expected_color[marker["type"]] == marker["color"]
    assert marker["message"].strip()


def main() -> None:
    source = YAML_PATH.read_text(encoding="utf-8")
    document = yaml.safe_load(source)
    assert document["kind"] == "AdaptiveDialog"

    nodes = list(walk(document))
    ids = [node["id"] for node in nodes if isinstance(node.get("id"), str)]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    assert not duplicates, f"duplicate action ids: {duplicates}"

    action_ids = set(ids)
    goto_targets = [
        node["actionId"]
        for node in nodes
        if node.get("kind") == "GotoAction" and "actionId" in node
    ]
    missing_targets = sorted(set(goto_targets) - action_ids)
    assert not missing_targets, f"missing goto targets: {missing_targets}"

    assert source.count("__FLOW_IMAGE_TEMP_SAVE_ID__") == 1
    assert source.count("__FLOW_IMAGE_OVERLAY_UPDATE_ID__") == 1

    final_source = FINAL_YAML_PATH.read_text(encoding="utf-8")
    final_document = yaml.safe_load(final_source)
    assert final_document["kind"] == "AdaptiveDialog"
    assert "__FLOW_" not in final_source
    assert final_source.count("6e918d2e-1a53-e8bd-cf74-cb5820039c7e") == 1
    assert final_source.count("ea6c4f9f-1a5f-211b-1ead-24587202d7cf") == 1

    dialog_source = DIALOG_YAML_PATH.read_text(encoding="utf-8")
    dialog_document = yaml.safe_load(dialog_source)
    assert dialog_document["kind"] == "AdaptiveDialog"
    assert "InvokeFlowAction" not in dialog_source
    assert "flowId:" not in dialog_source
    assert "cr88f_SUBARU_search.action.AI__v3_-Qk" not in dialog_source
    assert dialog_source.count("cr88f_SUBARU_search.action.AI__v3\n") == 1
    assert "contentBytes" not in dialog_source
    assert "base64" not in dialog_source.lower()
    assert "invokeFlowAction_saveTemporaryImage" not in dialog_source
    assert "search_photoGuidelineRetrieve" not in dialog_source
    assert "撮影要領再利用秒数" not in dialog_source
    assert "撮影要領未取得" not in dialog_source
    assert "setVariable_useFixedImageGuideBody" in dialog_source
    assert "search_imageQuestionKnowledge" in dialog_source
    assert "search_unrelatedImageQuestionKnowledge" in dialog_source
    assert "02A2_固定撮影要領範囲外のナレッジ回答" in dialog_source
    assert "cr88f_SUBARU_search.topic.09___h1YzFolnLAJjhZiLsRJ3r" in dialog_source
    assert "cr88f_SUBARU_search.topic.00___XQrXfSFWOaET4lVzBCFXi" in dialog_source
    for meter_rule in (
        "メーター本体の直下に接続された縦配管の途中",
        "メーター本体上部の配管接続部",
        "ツマミの握り部の長軸が水平",
        "ツマミの握り部の長軸が垂直",
        "ツマミ付近の配管全体が連続して見えることは必須ではない",
        "縦長の平たいレバーが上下方向に明瞭なら「開」",
        "ツマミが明瞭に縦向きなのに、配管の一部がバルブで隠れていることを理由に開閉不明としない",
        "MS-001は閉止方向の確認自体が実施判定条件",
        "MS-001のmarkers座標は操作ツマミの外周だけ",
    ):
        assert meter_rule in dialog_source, meter_rule
    for binding in ("text:", "text_1:", "text_2:", "text_3:", "text_4:"):
        assert binding in dialog_source, binding
    for required_text in (
        "■座標化した対象物",
        "■画像表示方向",
        "[目印JSON]",
        "[/目印JSON]",
        "最大8件",
        "message",
        "TOKEN",
    ):
        if required_text == "TOKEN":
            assert "画像一時保存トークン" in dialog_source
        else:
            assert required_text in dialog_source, required_text

    example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert example["version"] == 1
    assert example["show"] is True
    assert 1 <= len(example["markers"]) <= 8
    for marker in example["markers"]:
        validate_marker(marker)

    app_doc = (ROOT / "power-apps" / "01_PowerApps導入.md").read_text(encoding="utf-8")
    for required_text in ("btnMarker1", "btnMarker8", "varMarkerPanelVisible", "Message"):
        assert required_text in app_doc

    app_page_doc = (ROOT / "power-apps" / "02_新規画像ページ_コード貼り付け版.md").read_text(encoding="utf-8")
    app_page_source = (ROOT / "power-apps" / "scrImageOverlay_画面内貼り付け用.pa.yaml").read_text(encoding="utf-8")
    app_button_source = (ROOT / "power-apps" / "btnOpenImageOverlay_貼り付け用.pa.yaml").read_text(encoding="utf-8")
    app_page = yaml.safe_load(app_page_source)
    app_button = yaml.safe_load(app_button_source)
    assert isinstance(app_page, list) and len(app_page) >= 20
    assert isinstance(app_button, list) and len(app_button) == 1
    child_names = {next(iter(child)) for child in app_page}
    for required_control in (
        "btnLoadImageOverlay",
        "imgOverlayPhoto",
        "btnImageMarker1",
        "btnImageMarker8",
        "btnMarkerModalBackdrop",
        "lblMarkerMessage",
        "btnImageBack",
        "tmrImageOverlayRefresh",
    ):
        assert required_control in child_names, required_control
    assert app_page_source.count("Control: Classic/Button@2.2.0") >= 12
    assert "Back(ScreenTransition.None)" in app_page_source
    assert "ImagePosition.Stretch" in app_page_source
    assert "Control: Screen" not in app_page_source
    assert "Control: Classic/Label" not in app_page_source
    assert app_page_source.count("Control: Label@") == 6
    assert "varReply" not in app_page_source
    assert "varReturnResultTab" not in app_page_source
    assert "ImageAnalysisStatus" not in app_page_source
    assert "ImagePixelWidth" not in app_page_source
    assert "ImagePixelHeight" not in app_page_source
    assert "https://tokyogasgroup.sharepoint.com/sites/NW_tool_library/AI_TemporaryImages/" in app_page_source
    assert "varImageConversationId" not in app_page_doc
    assert "varAgentConversationId" in app_page_doc
    assert "varAgentConversationId" in app_button_source
    assert "Navigate(scrImageOverlay, ScreenTransition.None)" in app_button_source

    sharepoint_doc = (ROOT / "sharepoint" / "01_SharePoint準備.md").read_text(encoding="utf-8")
    pa1_doc = (ROOT / "power-automate" / "01_AI_画像一時保存PA.md").read_text(encoding="utf-8")
    pa2_doc = (ROOT / "power-automate" / "02_AI_画像座標更新PA.md").read_text(encoding="utf-8")
    pa3_doc = (ROOT / "power-automate" / "03_AI_一時画像削除PA.md").read_text(encoding="utf-8")
    integration_doc = (ROOT / "power-automate" / "00_Base64なし_既存画像転送PAへ統合.md").read_text(encoding="utf-8")
    required_columns = (
        "ImageToken", "ImageUrl", "ImageFileIdentifier", "ImagePixelWidth",
        "ImagePixelHeight", "ImageOverlayJson", "ImageAnalysisNote",
        "ImageAnalysisStatus", "ImageVersion", "ImageUserText",
        "ImageExpiresAt", "ImageErrorCode",
    )
    for column in required_columns:
        assert column in sharepoint_doc, column
    for document in (pa1_doc, pa2_doc, pa3_doc, integration_doc, app_doc, app_page_doc, app_page_source, app_button_source):
        assert "AI_ImageOverlay" not in document
    assert "CASE_ROW_NOT_FOUND" in pa1_doc
    assert "base64()" in integration_doc
    assert "追加しません" in integration_doc
    assert "ConversationId" in pa2_doc and "ImageToken" in pa2_doc
    assert "項目の削除" not in pa3_doc
    assert "案件行そのものは絶対に削除しません" in pa3_doc

    print("PASS: YAML, tool dialogs, overlay contract, multi-marker example, and isolated Power Apps image screen")


if __name__ == "__main__":
    main()
