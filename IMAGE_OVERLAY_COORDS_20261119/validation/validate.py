from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
YAML_PATH = ROOT / "copilot" / "4-9_画像座標対応_フローID置換前.yaml"
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
            assert "画像一時保存トークン" in source
        else:
            assert required_text in source, required_text

    example = json.loads(EXAMPLE_PATH.read_text(encoding="utf-8"))
    assert example["version"] == 1
    assert example["show"] is True
    assert 1 <= len(example["markers"]) <= 8
    for marker in example["markers"]:
        validate_marker(marker)

    app_doc = (ROOT / "power-apps" / "01_PowerApps導入.md").read_text(encoding="utf-8")
    for required_text in ("btnMarker1", "btnMarker8", "varMarkerPanelVisible", "Message"):
        assert required_text in app_doc

    print("PASS: YAML structure, goto targets, overlay contract, multi-marker example, Apps guide")


if __name__ == "__main__":
    main()
