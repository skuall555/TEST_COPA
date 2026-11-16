"""Static and route-contract checks for the generated Copilot Studio topics."""
from __future__ import annotations

import hashlib
import subprocess
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
BASE = "4fa63fbcfc1ccf39d063276d9999a5ffb3166132"


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def load(name):
    return yaml.safe_load((ROOT / name).read_text(encoding="utf-8"))


def source(name):
    return subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{BASE}:SUBARU_optimized/{name}"]
    )


def node(document, ident):
    matches = [item for item in walk(document) if item.get("id") == ident]
    assert len(matches) == 1, (ident, len(matches))
    return matches[0]


def ids(document):
    return [item["id"] for item in walk(document) if isinstance(item.get("id"), str)]


def check_common(document):
    all_ids = ids(document)
    assert not [key for key, count in Counter(all_ids).items() if count > 1]
    targets = {
        item["actionId"]
        for item in walk(document)
        if item.get("kind") == "GotoAction" and item.get("actionId")
    }
    assert not targets.difference(all_ids), targets.difference(all_ids)


def main():
    field = load("3-9_貼り替え用.txt")
    image = load("4-9_貼り替え用.txt")
    check_common(field)
    check_common(image)

    # These two files are deliberately unchanged in this package.
    for name in ["1-マニュアル関連入口_optimized.yaml", "SUBARU_エージェント指示_optimized.txt"]:
        actual = (ROOT / "source" / name).read_bytes()
        expected = source(name)
        assert hashlib.sha256(actual).digest() == hashlib.sha256(expected).digest(), name

    # The field topic keeps the existing save flow and uses the embedded manual quick-reference for consultation.
    assert node(field, "invokeFlowAction_caseSaveFieldAdvice")["flowId"] == "9a770168-65a8-f111-aaad-7ced8d2f9cab"
    assert node(field, "conditionGroup_userConsultSearch")["conditions"][0]["condition"] == "=Topic.ユーザー相談あり"
    assert not any(item.get("id") == "search_userConsultManual" for item in walk(field))
    consult = node(field, "answer_userConsult")
    assert "Topic.優先度ガイド取得結果" in consult["userInput"]
    assert "検索結果、原文取得、ナレッジヒットの有無には言及しない" in consult["additionalInstructions"]
    assert not any(item.get("id") == "conditionGroup_priorityPurposeSwitchToJunkai" for item in walk(field))

    prompt = node(field, "setVariable_priorityPrompt")["value"]
    assert "[[ANSWER]]" not in prompt and "FACTS・EMERGENCY・P01〜P13・NEXT・CHECK" in prompt
    assert 'StartsWith(Trim(Topic.優先度表示原文), "[[FACTS]]")' in node(field, "setVariable_priorityFormatEnvelope")["value"]
    assert "質問・相談の表現が含まれていても" in prompt
    assert "対応済み【!】は高優先度の完了扱いにせず" in prompt
    assert node(field, "setVariable_userConsultAnswerReset")["variable"] == "Topic.判定ユーザー回答"
    consult_branch = node(field, "conditionGroup_priorityConsultOrProgress")
    assert any(item.get("id") == "setVariable_appendConsultHistory" for item in walk(consult_branch["conditions"][0]["actions"]))
    assert any(item.get("id") == "setVariable_appendPriorityHistory" for item in walk(consult_branch["elseActions"]))
    assert next(item for item in walk(consult_branch["conditions"][0]["actions"]) if item.get("kind") == "GotoAction")["actionId"] == "setVariable_imageAnswerPending"
    assert "Global.写真ユーザー回答テキスト" in node(field, "setVariable_imageAnswerPending")["value"]
    assert node(field, "conditionGroup_clearImageAnswerAfterSave")["conditions"][0]["condition"] == "=Topic.写真回答反映中"
    assert "【ユーザーへの回答】" in node(field, "setVariable_itemRender")["value"]
    assert node(field, "goto_priorityAgain")["actionId"] == "setVariable_imageAnswerPending"
    for code in [f"P{i:02d}" for i in range(1, 24)]:
        assert "対応済み【!】" in node(field, "setVariable_itemValid" + code)["value"]

    # The first image pass has an explicit conservative relevance gate.
    p1 = node(image, "setVariable_prompt1")["value"]
    assert "次の8見出し" in p1
    assert "■現場対応との関連判定" in p1 and "■ユーザー向けコメント" in p1
    assert "着火・炎・煙・損傷" in p1 and "判断に迷う場合は不明" in p1
    fast = node(image, "conditionGroup_imageUnrelatedFastExit")
    assert fast["conditions"][0]["condition"] == '=Topic.画像関連判定 = "関連なし"'
    goto = next(item for item in walk(fast) if item.get("kind") == "GotoAction")
    assert goto["actionId"] == "setVariable_globalImageUserAnswer"

    # Unrelated images cannot reach the guide lookup; related/unknown images retain it.
    ordered = [item.get("id") for item in walk(image)]
    positions = {ident: i for i, ident in enumerate(ordered) if ident}
    assert positions["conditionGroup_imageUnrelatedFastExit"] < positions["conditionGroup_reuseImageGuide"]
    reuse = node(image, "conditionGroup_reuseImageGuide")
    assert any(item.get("id") == "search_photoGuidelineRetrieve" for item in walk(reuse.get("elseActions", [])))
    assert not any(item.get("id") == "search_photoGuidelineRetrieve" for item in walk(fast))

    # Cache contains only the stable guide text and is conversation/user/channel/version scoped.
    cache_condition = reuse["conditions"][0]["condition"]
    for token in ["会話ID", "利用者ID", "チャネル", "キャッシュ版", "取得時刻", "CountIf(Sequence(18)"]:
        assert token in cache_condition
    cache_writes = [item for item in walk(image) if str(item.get("variable", "")).startswith("Global.画像要領キャッシュ")]
    assert cache_writes
    assert not any("画像事実" in str(item.get("value", "")) for item in cache_writes)

    # Warning and user-answer contracts are present in both the judge and visible response.
    p2 = node(image, "setVariable_prompt2")["value"]
    for token in ["[ユーザーへの回答]", "【警告付きの実施確認】", "【写真有】【!】", "【重要な危険の扱い】"]:
        assert token in p2
    judge = node(image, "answer_photoGuidelineJudge")["additionalInstructions"]
    assert "5見出し" in judge and "対象物自体を断定できない場合は措置済みにしない" in judge
    visible = node(image, "sendActivity_analysisResult")["activity"]
    assert "【ユーザーへの回答】" in visible and "【確認したいこと】" in visible
    history = node(image, "setVariable_appendImageResultToGlobalHistory")["value"]
    assert 'Topic.画像関連判定 = "関連なし"' in history

    # Scope guard: no Apps, Power Automate, Lists, entry, or global-instruction paste files.
    paste_files = {path.name for path in ROOT.iterdir() if path.is_file() and path.suffix == ".txt"}
    assert paste_files == {"3-9_貼り替え用.txt", "4-9_貼り替え用.txt"}, paste_files
    print("PASS: YAML, IDs, gotos, routing, cache, warning, output, and scope contracts")


if __name__ == "__main__":
    main()
