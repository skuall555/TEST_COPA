"""Compile and run the package's changed Power Fx expressions with Microsoft's SDK."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import subprocess
import urllib.request
import zipfile
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
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


def index(document):
    return {item["id"]: item for item in walk(document) if item.get("id") and item.get("kind")}


def parent_list(value, ident):
    if isinstance(value, list):
        if any(isinstance(item, dict) and item.get("id") == ident for item in value):
            return value
        for child in value:
            found = parent_list(child, ident)
            if found is not None:
                return found
    elif isinstance(value, dict):
        for child in value.values():
            found = parent_list(child, ident)
            if found is not None:
                return found
    return None


def wire(answer="ー", warning=False):
    rows = [
        f"[[ANSWER]]{answer}[[/ANSWER]]",
        "[[FACTS]]└台所で臭気あり[[/FACTS]]",
        "[[EMERGENCY]]通常|避難と要請を同時に高とする具体的危険は未報告[[/EMERGENCY]]",
    ]
    for number in range(1, 14):
        code = f"P{number:02d}"
        if warning and code == "P04":
            priority, status, reason = "高", "対応済み【!】", "ポケット警報器の設置は写真で確認できるが設置場所の周辺範囲は未確認"
        elif code == "P01":
            priority, status, reason = "高", "対応済み", "火気使用禁止を実施済みと報告"
        else:
            priority, status, reason = "中", "要確認", "必要な実施状況が未報告"
        rows.append(f"[[{code}]]{priority}|{status}|{reason}[[/{code}]]")
    rows += [
        "[[NEXT]]└未確認の措置を確認する[[/NEXT]]",
        "[[CHECK]]未確認の実施状況を教えてください。[[/CHECK]]",
    ]
    return "\n".join(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dotnet", type=Path, required=True)
    args = parser.parse_args()
    dotnet = args.dotnet.resolve()
    build = Path("/tmp/field-consult-image-fast-native")
    build.mkdir(exist_ok=True)

    for package, version in [
        ("microsoft.powerfx.core", "1.8.1"),
        ("microsoft.powerfx.interpreter", "1.8.1"),
        ("microsoft.powerfx.transport.attributes", "1.8.1"),
        ("microsoft.bcl.asyncinterfaces", "6.0.0"),
    ]:
        archive = build / f"{package}.nupkg"
        if not archive.exists():
            url = f"https://api.nuget.org/v3-flatcontainer/{package}/{version}/{package}.{version}.nupkg"
            archive.write_bytes(urllib.request.urlopen(url, timeout=30).read())
        package_zip = zipfile.ZipFile(io.BytesIO(archive.read_bytes()))
        for member in package_zip.namelist():
            if member.startswith("lib/netstandard2.0/") and member.endswith(".dll"):
                output = build / member.removeprefix("lib/netstandard2.0/")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(package_zip.read(member))

    files = {
        "field": ("3-9-緊急保安業務エージェント_optimized.yaml", "3-9_貼り替え用.txt"),
        "image": ("4-9-画像分析エージェント_緊急保安_optimized.yaml", "4-9_貼り替え用.txt"),
    }
    expressions = []
    documents = {}
    for label, (original_name, generated_name) in files.items():
        before = yaml.safe_load(subprocess.check_output(["git", "-C", str(REPO), "show", f"{BASE}:SUBARU_optimized/{original_name}"]))
        after = yaml.safe_load((ROOT / generated_name).read_text(encoding="utf-8"))
        documents[label] = after
        old, new = index(before), index(after)
        for ident, item in new.items():
            previous = old.get(ident, {})
            if item.get("kind") == "SetVariable" and item.get("value") != previous.get("value"):
                variable = item.get("variable", "")
                expected = "Boolean" if variable in {"Topic.ユーザー相談あり", "Topic.撮影要領再利用", "Topic.デバッグ表示"} else "Number" if variable in {"Topic.撮影要領再利用秒数", "Topic.画像事実実質長", "Topic.優先度様式再試行回数"} else "DateTime" if variable == "Global.画像要領キャッシュ取得時刻" else "String"
                expressions.append({"id": label + ":" + ident, "expression": item["value"][1:], "expected": expected})
            if item.get("kind") in {"AnswerQuestionWithAI", "SearchAndSummarizeContent"} and item.get("userInput") != previous.get("userInput"):
                expressions.append({"id": label + ":" + ident + ":input", "expression": item["userInput"][1:], "expected": "String"})
            if item.get("kind") == "ConditionGroup":
                old_conditions = {row.get("id"): row.get("condition") for row in previous.get("conditions", [])}
                for row in item.get("conditions", []):
                    if row.get("condition") != old_conditions.get(row.get("id")):
                        expressions.append({"id": label + ":" + row["id"], "expression": row["condition"][1:], "expected": "Boolean"})

    # Build a broad Studio-like type scope from every explicit Topic/Global reference.
    import re
    topic_types, global_types = {}, {}
    for item in expressions:
        for name in re.findall(r"Topic\.([\w\u3000-\u9fff]+)", item["expression"]):
            topic_types.setdefault(name, "String")
        for name in re.findall(r"Global\.([\w\u3000-\u9fff]+)", item["expression"]):
            global_types.setdefault(name, "String")
    for name in ["ユーザー相談あり", "撮影要領再利用", "デバッグ表示"]:
        topic_types[name] = "Boolean"
    for name in ["撮影要領再利用秒数", "画像事実実質長", "優先度様式再試行回数"]:
        topic_types[name] = "Number"
    global_types["画像要領キャッシュ取得時刻"] = "DateTime"

    field = documents["field"]
    sequence = parent_list(field, "setVariable_priorityFormatRaw")
    assert sequence is not None
    start = next(i for i, item in enumerate(sequence) if item.get("id") == "setVariable_priorityFormatRaw")
    end = next(i for i, item in enumerate(sequence) if item.get("id") == "setVariable_itemRender")
    field_steps = [
        {"id": item["id"], "variable": item["variable"].removeprefix("Topic."), "expression": item["value"][1:]}
        for item in sequence[start:end + 1]
        if item.get("kind") == "SetVariable"
    ]
    field_cases = [
        {"name": "progress answer is dash", "text": wire(), "accept": True, "contains": "【ユーザーへの回答】\nー"},
        {"name": "consultation answer is retained", "text": wire("└次の調査は取得したマニュアルの範囲で案内します"), "accept": True, "contains": "【ユーザーへの回答】\n└次の調査"},
        {"name": "warning status is accepted but incomplete", "text": wire(warning=True), "accept": True, "contains": "ポケット警報器等の設置：対応済み【!】", "incomplete": "あり"},
        {"name": "legacy payload without ANSWER is rejected", "text": wire().replace("[[ANSWER]]ー[[/ANSWER]]\n", ""), "accept": False},
    ]
    image_index = index(documents["image"])
    consult_expression = index(documents["field"])["setVariable_userConsultSignal"]["value"][1:]
    relation_expression = image_index["setVariable_imageRelation"]["value"][1:]
    comment_expression = image_index["setVariable_imageUserComment"]["value"][1:]
    image_unrelated = "■現場対応との関連判定\n・関連なし\n■ユーザー向けコメント\n・送っていただいた画像は鉢植えに見えます。進捗要素は見当たりません。\n■写っている物\n・鉢植え"
    image_related = "■現場対応との関連判定\n・関連あり\n■ユーザー向けコメント\n・ー\n■写っている物\n・消火器"
    semantic_cases = [
        {"name": "plain progress is not consultation", "expression": consult_expression, "topic": {"最新利用者入力": "消火器設置済み"}, "expectedBoolean": False},
        {"name": "question triggers consultation", "expression": consult_expression, "topic": {"最新利用者入力": "このあと何を調査すればいい？"}, "expectedBoolean": True},
        {"name": "unrelated image marker parses", "expression": relation_expression, "topic": {"画像事実": image_unrelated}, "expectedString": "関連なし"},
        {"name": "related image marker parses", "expression": relation_expression, "topic": {"画像事実": image_related}, "expectedString": "関連あり"},
        {"name": "missing image marker is conservative", "expression": relation_expression, "topic": {"画像事実": "■写っている物\n・不鮮明"}, "expectedString": "不明"},
        {"name": "unrelated image comment parses", "expression": comment_expression, "topic": {"画像事実": image_unrelated}, "expectedString": "送っていただいた画像は鉢植えに見えます。進捗要素は見当たりません。"},
    ]
    data = {
        "expressions": expressions,
        "topicTypes": topic_types,
        "globalTypes": global_types,
        "fieldSteps": field_steps,
        "fieldCases": field_cases,
        "semanticCases": semantic_cases,
    }
    input_path = build / "input.json"
    input_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    sdk = max((dotnet.parent / "sdk").iterdir(), key=lambda path: tuple(int(part) for part in path.name.split(".")))
    references = list((dotnet.parent / "packs/Microsoft.NETCore.App.Ref").glob("*/ref/net8.0/*.dll")) + list(build.glob("Microsoft.*.dll"))
    response = build / "compile.rsp"
    response.write_text("-nologo\n-target:exe\n-out:" + str(build / "check.dll") + "\n" + "\n".join("-r:" + str(path) for path in references) + "\n" + str(HERE / "NativeChecks.cs"), encoding="utf-8")
    (build / "check.runtimeconfig.json").write_text(json.dumps({"runtimeOptions": {"tfm": "net8.0", "framework": {"name": "Microsoft.NETCore.App", "version": "8.0.0"}}}), encoding="utf-8")
    subprocess.run([str(dotnet), str(sdk / "Roslyn/bincore/csc.dll"), "@" + str(response)], check=True)
    completed = subprocess.run([str(dotnet), str(build / "check.dll"), str(input_path)], check=True, text=True, capture_output=True)
    result = json.loads(completed.stdout)
    result["source_sha256"] = {
        name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
        for name in ["3-9_貼り替え用.txt", "4-9_貼り替え用.txt"]
    }
    (ROOT / "validation" / "native_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    failed_checks = [item for item in result["checks"] if not item["success"]]
    failed_semantics = [item for item in result["semantics"] if not item["success"]]
    failed_formats = [item for item in result["formats"] if not item["success"]]
    print(f"Power Fx: {len(result['checks'])} expressions, {len(result['semantics'])} semantic cases, {len(result['formats'])} format cases")
    if failed_checks:
        print(json.dumps(failed_checks, ensure_ascii=False, indent=2))
    if failed_formats:
        print(json.dumps(failed_formats, ensure_ascii=False, indent=2))
    if failed_semantics:
        print(json.dumps(failed_semantics, ensure_ascii=False, indent=2))
    if failed_checks or failed_semantics or failed_formats:
        raise SystemExit(1)
    print("PASS: native Power Fx checks")


if __name__ == "__main__":
    main()
