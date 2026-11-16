"""Build paste-ready field and image topics from the pre-Teams 4fa63fb baseline."""
from __future__ import annotations

import copy
import difflib
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
BASE = "4fa63fbcfc1ccf39d063276d9999a5ffb3166132"
FIELD = "3-9-緊急保安業務エージェント_optimized.yaml"
IMAGE = "4-9-画像分析エージェント_緊急保安_optimized.yaml"
ENTRY = "1-マニュアル関連入口_optimized.yaml"
INSTRUCTIONS = "SUBARU_エージェント指示_optimized.txt"
IMAGE_GUIDE_VERSION = "photo-guide-20261116-v1|cr88f_SUBARU_search.file._.pdf_Ten"

sys.path.insert(0, str(REPO / "SUBARU_optimized/validation"))
from restart_support import D


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def index(document):
    return {node["id"]: node for node in walk(document) if isinstance(node, dict) and "id" in node and "kind" in node}


def find_parent_list(value, ident):
    if isinstance(value, list):
        for position, child in enumerate(value):
            if isinstance(child, dict) and child.get("id") == ident:
                return value, position
            found = find_parent_list(child, ident)
            if found:
                return found
    elif isinstance(value, dict):
        for child in value.values():
            found = find_parent_list(child, ident)
            if found:
                return found
    return None


def setv(ident, variable, expression):
    return {"kind": "SetVariable", "id": ident, "variable": variable, "value": expression}


def condition(ident, expression, actions, otherwise=None):
    result = {"kind": "ConditionGroup", "id": ident, "conditions": [{"id": ident + "_item", "condition": expression, "actions": actions}]}
    if otherwise is not None:
        result["elseActions"] = otherwise
    return result


def insert_before(document, ident, nodes):
    parent, position = find_parent_list(document, ident)
    parent[position:position] = nodes


def insert_after(document, ident, nodes):
    parent, position = find_parent_list(document, ident)
    parent[position + 1:position + 1] = nodes


def replace(document, ident, nodes):
    parent, position = find_parent_list(document, ident)
    parent[position:position + 1] = nodes


def dump(document, path):
    path.write_text(yaml.dump(document, Dumper=D, allow_unicode=True, sort_keys=False, width=100000), encoding="utf-8")


def raw_source(name):
    return subprocess.check_output(["git", "-C", str(REPO), "show", BASE + ":SUBARU_optimized/" + name])


CONSULT_SIGNAL = '=With({t: Lower(Trim(Topic.最新利用者入力))}, Or("?" in t, "？" in t, "教えて" in t, "どうす" in t, "どうした" in t, "どう進" in t, "何を" in t, "なにを" in t, "どこ" in t, "いつ" in t, "なぜ" in t, "理由" in t, "相談" in t, "確認したい" in t, "確認して" in t, "確認すべき" in t, "すればいい" in t, "したらいい" in t, "していい" in t, "でいい" in t, "大丈夫" in t, "必要ですか" in t, "必要か" in t, "次の調査" in t, "次に調査" in t, "このあと" in t, "この後" in t, "マニュアル" in t, "規定" in t, "基準" in t))'


def build_field(raw):
    doc = yaml.safe_load(raw)
    ix = index(doc)
    doc["modelDescription"] += "\n  現場対応中の相談・質問はトピックを終了させず、必要時だけWord原本を検索し、ユーザー回答と優先度表示を同時に返す。\n  進捗報告だけのときはユーザー回答を「ー」とする。相談文は優先度を変える現場事実として扱わない。\n"

    insert_after(doc, "setVariable_imageReceptionOffAtStart", [
        setv("setVariable_latestUserInputAtStart", "Topic.最新利用者入力", "=Topic.初回入力"),
    ])

    manual_search = {
        "kind": "SearchAndSummarizeContent",
        "id": "search_userConsultManual",
        "displayName": "11A_現場相談の根拠取得",
        "autoSend": False,
        "variable": "Topic.ユーザー相談根拠",
        "userInput": '=Topic.最新利用者入力 & Char(10) & "現場の既報：" & Topic.初回入力 & Char(10) & Topic.追加情報履歴',
        "additionalInstructions": "検索できた原文を、質問への回答に直接必要な箇所だけ、文書名・見出しとともに原文に近い形で提示してください。一般知識で補完しないでください。現場事実や優先度を作らないでください。質問と直接関係する根拠がない場合は「なし」とだけ出力してください。",
        "fileSearchDataSource": {"searchFilesMode": {"kind": "DoNotSearchFiles"}},
        "knowledgeSources": {"kind": "SearchSpecificKnowledgeSources", "knowledgeSources": [
            "cr88f_SUBARU_search.topic.09___h1YzFolnLAJjhZiLsRJ3r",
            "cr88f_SUBARU_search.topic.00___XQrXfSFWOaET4lVzBCFXi",
        ]},
        "applyModelKnowledgeSetting": False,
    }
    consult_nodes = [
        setv("setVariable_userConsultSourceReset", "Topic.ユーザー相談根拠", '="なし"'),
        setv("setVariable_userConsultSignal", "Topic.ユーザー相談あり", CONSULT_SIGNAL),
        condition("conditionGroup_userConsultSearch", "=Topic.ユーザー相談あり", [manual_search]),
    ]
    insert_before(doc, "setVariable_priorityPrompt", consult_nodes)

    ix = index(doc)
    prompt = ix["setVariable_priorityPrompt"]["value"]
    prompt = prompt.replace(
        '【追加報告・画像結果】\n" & Topic.追加情報履歴 & "\n',
        '【追加報告・画像結果】\n" & Topic.追加情報履歴 & "\n【今回の最新入力】\n" & Topic.最新利用者入力 & "\n【今回の入力に質問・相談の表現があるか】\n" & If(Topic.ユーザー相談あり, "あり", "なし") & "\n【質問・相談に回答するため取得したマニュアル原文】\n" & Topic.ユーザー相談根拠 & "\n'
    )
    prompt = prompt.replace(
        "FACTS・EMERGENCY・P01〜P13・NEXT・CHECKを各1回、順番どおり出力する。",
        "ANSWER・FACTS・EMERGENCY・P01〜P13・NEXT・CHECKを各1回、順番どおり出力する。"
    )
    prompt = prompt.replace(
        "[[FACTS]]確認できた事実を└から始まる行で記載[[/FACTS]]",
        "[[ANSWER]]質問・相談への回答。質問・相談が無い場合はー。回答がある場合は└から始める[[/ANSWER]]\n[[FACTS]]確認できた事実を└から始まる行で記載[[/FACTS]]"
    )
    prompt = prompt.replace(
        "優先度は高／中／低、状態は対応済み／未実施／要確認の一つずつ。",
        "優先度は高／中／低、状態は対応済み／対応済み【!】／未実施／要確認の一つずつ。"
    )
    prompt = prompt.replace(
        "# 実施済みと範囲・効果",
        "# ユーザーへの回答\n今回の最新入力が進捗報告だけならANSWERは必ず「ー」。質問・相談が含まれる場合だけ、取得したマニュアル原文または固定ガイドに直接根拠がある範囲で短く回答する。根拠が取得できない場合は、その旨をANSWERで伝え、推測で回答しない。現場対応と無関係な質問には、現場アドバイザーの対象外であることと、進捗報告は継続できることを伝える。ANSWERの内容をFACTSや優先度の根拠に流用しない。質問文を実施済み・未実施の報告とみなさない。\n\n# 写真の警告付き対応済み\n画像履歴に【写真有】【!】がある場合、対象物と設置行為は確認できるが、設置場所・適合条件・撮影範囲に確認が残ることを示す。該当措置の状態を対応済み【!】とし、根拠には角括弧を使わず、確認できた実施と残る確認を分けて書く。対応済み【!】は高優先度の完了扱いにせず、NEXTまたはCHECKで再撮影・位置確認等を残す。対象物自体を断定できない画像は対応済み【!】にせず要確認とする。\n\n# 実施済みと範囲・効果"
    )
    ix["setVariable_priorityPrompt"]["value"] = prompt
    ix["answer_priority"]["additionalInstructions"] = "固定ガイド、報告された現場事実、取得したマニュアル原文だけで処理する。内部ブロック形式でANSWERから順に返し、外部検索や前置き、ユーザー用見出しの直接出力はしない。進捗報告だけならANSWERはー。質問・相談には根拠の範囲で回答し、根拠なしでも処理全体を停止しない。ANSWERや質問文を優先度の事実に混ぜない。画像の【写真有】【!】は対応済み【!】、物体自体が未確定なら要確認とする。"

    # Keep the active field dialog instead of ending it for manual/check wording.
    manual_switch = ix["conditionGroup_priorityPurposeSwitchToJunkai"]
    replace(doc, "conditionGroup_priorityPurposeSwitchToJunkai", copy.deepcopy(manual_switch["elseActions"]))
    insert_after(doc, "setVariable_resyncHistoryFromGlobal", [
        setv("setVariable_latestUserInputAfterWait", "Topic.最新利用者入力", "=Topic.優先度追加回答"),
    ])
    index(doc)["goto_priorityAgain"]["actionId"] = "setVariable_userConsultSourceReset"

    # Add ANSWER parsing immediately after the envelope check.
    envelope = index(doc)["setVariable_priorityFormatEnvelope"]
    envelope["value"] = envelope["value"].replace('StartsWith(Trim(Topic.優先度表示原文), "[[FACTS]]")', 'StartsWith(Trim(Topic.優先度表示原文), "[[ANSWER]]")')
    answer_nodes = [
        setv("setVariable_itemSectionANSWER", "Topic.優先度表示区分", '=First(Split(Last(Split(Topic.優先度表示原文, "[[ANSWER]]")).Value, "[[/ANSWER]]")).Value'),
        setv("setVariable_itemUniqueANSWER", "Topic.優先度表示検証", '=If(Topic.優先度表示検証 <> "合格", Topic.優先度表示検証, If(And(CountRows(Split(Topic.優先度表示原文, "[[ANSWER]]")) = 2, CountRows(Split(Topic.優先度表示原文, "[[/ANSWER]]")) = 2), "合格", "不合格:itemUniqueANSWER"))'),
        setv("setVariable_itemRemoveANSWER", "Topic.判定残余", '=Substitute(Topic.判定残余, "[[ANSWER]]" & Topic.優先度表示区分 & "[[/ANSWER]]", "")'),
        setv("setVariable_itemBodyANSWER", "Topic.判定ユーザー回答", '=With({bodyText: Trim(Substitute(Substitute(Topic.優先度表示区分, "【", "（"), "】", "）"))}, If(bodyText = "ー", "ー", Substitute(Substitute(If(StartsWith(bodyText, "・"), "└" & Mid(bodyText, 2), If(StartsWith(bodyText, "- "), "└" & Mid(bodyText, 3), If(StartsWith(bodyText, "└"), bodyText, "└" & bodyText))), Char(10) & "・", Char(10) & "└"), Char(10) & "- ", Char(10) & "└")))'),
        setv("setVariable_itemBodyValidANSWER", "Topic.優先度表示検証", '=If(Topic.優先度表示検証 <> "合格", Topic.優先度表示検証, If(And(Len(Topic.判定ユーザー回答) > 0, Not("[[" in Topic.判定ユーザー回答), Or(Topic.判定ユーザー回答 = "ー", StartsWith(Topic.判定ユーザー回答, "└"))), "合格", "不合格:itemBodyValidANSWER"))'),
    ]
    insert_after(doc, "setVariable_priorityFormatEnvelope", answer_nodes)

    # Accept the warning status while keeping it incomplete until the warning is resolved.
    for code in [f"P{i:02d}" for i in range(1, 24)]:
        node = index(doc).get("setVariable_itemValid" + code)
        if node:
            node["value"] = node["value"].replace('Or(itemStatus = "対応済み", itemStatus = "未実施", itemStatus = "要確認")', 'Or(itemStatus = "対応済み", itemStatus = "対応済み【!】", itemStatus = "未実施", itemStatus = "要確認")')

    render = index(doc)["setVariable_itemRender"]
    render["value"] = render["value"].replace('="【確認できた事実】', '="【ユーザーへの回答】" & Char(10) & Topic.判定ユーザー回答 & Char(10) & Char(10) & "【確認できた事実】')
    return doc


def build_image(raw):
    doc = yaml.safe_load(raw)
    ix = index(doc)
    doc["modelDescription"] = doc["modelDescription"].replace("出力は次の3つに仕分けて", "出力はユーザーへの回答と次の3つに仕分けて")
    doc["modelDescription"] += "\n  第1段で現場対応との関連を判定し、明確に無関係なら撮影要領検索と第2段を省略する。\n  関連あり・不明は従来の照合を続行する。撮影要領は同じ会話・利用者・チャネルで5分だけ再利用する。\n"

    p1 = ix["setVariable_prompt1"]["value"]
    p1 = p1.replace(
        "【出力形式】\n次の6見出しを必ず全て出力してください。",
        "【現場対応との関連判定】\nMS-001〜MS-018の対象物・措置、ガス設備、検知・臭気・漏えい、着火・炎・煙・損傷・危険行為・人身影響・立入危険など、現場対応へつながる要素があれば関連あり。該当要素が見当たらず、一般の風景・植物・食事・文房具等だけと明確に判断できる場合だけ関連なし。画像が不鮮明、対象の一部かもしれない、判断に迷う場合は不明。関連なしを推測で選ばない。\n\n関連なしの場合、ユーザー向けコメントに、画像が何に見えるか、進捗要素が見当たらないこと、見落としがあればコメントで教えてほしいことを2文程度で書く。関連あり・不明は「・ー」とする。\n\n【出力形式】\n次の8見出しを必ず全て出力してください。\n\n■現場対応との関連判定\n■ユーザー向けコメント"
    )
    p1 = p1.replace("・6つの見出しを必ず全て出力する", "・8つの見出しを必ず全て出力する")
    p1 = p1.replace("・各見出しの下に「・」で始まる行を必ず1行以上書く", "・関連判定の下は「・関連あり」「・関連なし」「・不明」のいずれか1行。その他の各見出しも「・」で始まる行を必ず1行以上書く")
    p1 = p1.replace("・画像が読み取れない場合は、全見出しに「・画像を読み取れません」と書く", "・画像が読み取れない場合は関連判定を「・不明」とし、その他の見出しに「・画像を読み取れません」と書く")
    ix["setVariable_prompt1"]["value"] = p1

    # Remove the two new headings when checking whether the model returned substantive facts.
    facts_len = ix["setVariable_imageFactsLength"]["value"]
    facts_len = facts_len.replace('Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(', 'Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(Substitute(')
    facts_len = facts_len.replace('Topic.画像事実, "■写っている物"', 'Topic.画像事実, "■現場対応との関連判定", ""), "■ユーザー向けコメント", ""), "■写っている物"')
    ix["setVariable_imageFactsLength"]["value"] = facts_len
    relation_nodes = [
        setv("setVariable_imageRelation", "Topic.画像関連判定", '=If("■現場対応との関連判定" in Topic.画像事実, With({bodyText: Trim(First(Split(Last(Split(Topic.画像事実, "■現場対応との関連判定")).Value, "■ユーザー向けコメント")).Value)}, If("関連なし" in bodyText, "関連なし", If("関連あり" in bodyText, "関連あり", "不明"))), "不明")'),
        setv("setVariable_imageUserComment", "Topic.画像ユーザー回答", '=If("■ユーザー向けコメント" in Topic.画像事実, With({bodyText: Trim(First(Split(Last(Split(Topic.画像事実, "■ユーザー向けコメント")).Value, "■写っている物")).Value)}, Trim(Substitute(Substitute(bodyText, "・", ""), "ー", ""))), "")'),
    ]
    insert_after(doc, "setVariable_imageFacts", relation_nodes)

    unrelated = condition("conditionGroup_imageUnrelatedFastExit", '=Topic.画像関連判定 = "関連なし"', [
        setv("setVariable_unrelatedAnswer", "Topic.画像ユーザー回答", '=If(IsBlank(Topic.画像ユーザー回答), "送っていただいた画像から、現場の進捗報告に該当する要素は確認できませんでした。対象物の見落としがあれば、コメントで教えてください。", Topic.画像ユーザー回答)'),
        setv("setVariable_unrelatedExtra", "Topic.追加情報部", '="・現場進捗に該当する要素は確認できませんでした"'),
        setv("setVariable_unrelatedDone", "Topic.措置済み部", '="・なし"'),
        setv("setVariable_unrelatedCheck", "Topic.要確認部", '="・なし"'),
        setv("setVariable_unrelatedUnknown", "Topic.判定なし部", '="・現場対応との関連なし"'),
        {"kind": "GotoAction", "id": "goto_unrelatedResult", "actionId": "setVariable_globalImageUserAnswer"},
    ])
    insert_after(doc, "conditionGroup_stage1Empty", [unrelated])

    # Short-lived, scoped, versioned cache for the unchanged guideline text.
    init_cache = [
        setv("setVariable_imageGuideReuse", "Topic.撮影要領再利用", "=true"),
        setv("setVariable_imageGuideReuseSeconds", "Topic.撮影要領再利用秒数", "=300"),
        setv("setVariable_imageGuideConversation", "Topic.画像要領会話ID", "=Text(System.Conversation.Id)"),
        setv("setVariable_imageGuideUser", "Topic.画像要領利用者ID", "=Text(System.User.Id)"),
        setv("setVariable_imageGuideChannel", "Topic.画像要領チャネル", "=Lower(Text(System.Activity.ChannelId))"),
        setv("setVariable_imageGuideVersion", "Topic.画像要領キャッシュ版", "=" + json.dumps(IMAGE_GUIDE_VERSION, ensure_ascii=False)),
    ]
    insert_after(doc, "setVariable_debugMode", init_cache)
    search = copy.deepcopy(index(doc)["search_photoGuidelineRetrieve"])
    cache_ok = '=And(Topic.撮影要領再利用, Not(IsBlank(Topic.画像要領会話ID)), Not(IsBlank(Topic.画像要領利用者ID)), Not(IsBlank(Topic.画像要領チャネル)), Global.画像要領キャッシュ会話ID = Topic.画像要領会話ID, Global.画像要領キャッシュ利用者ID = Topic.画像要領利用者ID, Global.画像要領キャッシュチャネル = Topic.画像要領チャネル, Global.画像要領キャッシュ版 = Topic.画像要領キャッシュ版, Not(IsBlank(Global.画像要領キャッシュ取得時刻)), DateDiff(Global.画像要領キャッシュ取得時刻, Now(), TimeUnit.Seconds) >= 0, DateDiff(Global.画像要領キャッシュ取得時刻, Now(), TimeUnit.Seconds) < Topic.撮影要領再利用秒数, Not(IsBlank(Global.画像要領キャッシュ本文)), CountIf(Sequence(18), Not(("MS-" & Text(Value, "000")) in Global.画像要領キャッシュ本文)) = 0)'
    store_ok = '=And(Topic.撮影要領再利用, Not(IsBlank(Topic.画像要領会話ID)), Not(IsBlank(Topic.画像要領利用者ID)), Not(IsBlank(Topic.画像要領チャネル)), Not(IsBlank(Topic.撮影要領本文)), Trim(Topic.撮影要領本文) <> "なし", CountIf(Sequence(18), Not(("MS-" & Text(Value, "000")) in Topic.撮影要領本文)) = 0)'
    store = [
        setv("setVariable_storeImageGuideBody", "Global.画像要領キャッシュ本文", "=Topic.撮影要領本文"),
        setv("setVariable_storeImageGuideConversation", "Global.画像要領キャッシュ会話ID", "=Topic.画像要領会話ID"),
        setv("setVariable_storeImageGuideUser", "Global.画像要領キャッシュ利用者ID", "=Topic.画像要領利用者ID"),
        setv("setVariable_storeImageGuideChannel", "Global.画像要領キャッシュチャネル", "=Topic.画像要領チャネル"),
        setv("setVariable_storeImageGuideVersion", "Global.画像要領キャッシュ版", "=Topic.画像要領キャッシュ版"),
        setv("setVariable_storeImageGuideTime", "Global.画像要領キャッシュ取得時刻", "=Now()"),
    ]
    search_branch = [search, condition("conditionGroup_storeImageGuide", store_ok, store)]
    replace(doc, "search_photoGuidelineRetrieve", [condition("conditionGroup_reuseImageGuide", cache_ok, [
        setv("setVariable_reuseImageGuideBody", "Topic.撮影要領本文", "=Global.画像要領キャッシュ本文"),
    ], search_branch)])

    # Stage 2 now produces a user-facing answer and the warning semantics.
    ix = index(doc)
    p2 = ix["setVariable_prompt2"]["value"]
    p2 = p2.replace(
        "【判定と仕分け】",
        "【警告付きの実施確認】\n対象物と設置・実施行為が画像で確認できるが、設置場所・周辺範囲・撮影角度等のため撮影要領への適合だけ確認できない、または設置場所が基準を満たしていない場合は、措置済みに【写真有】【!】を付ける。同時に要確認へ、何が不足・不適合か、どう再撮影・是正確認するかを書く。物体自体がボケ・一部だけ・類似物で断定できない場合は措置済みにせず、要確認へ【!】を付ける。\n\n【重要な危険の扱い】\n着火・炎・煙・破損・危険行為など、撮影要領の対象物でなくても現場対応に影響する事実は追加情報に残し、緊急に確認すべき内容を要確認とユーザーへの回答に書く。\n\n【判定と仕分け】"
    )
    p2 = p2.replace(
        "【出力形式】（この形式以外は出力しないこと。前置き・総括・引用URLは禁止）\n[追加情報]",
        "【出力形式】（この形式以外は出力しないこと。前置き・総括・引用URLは禁止）\n[ユーザーへの回答]\n・（警告・再撮影・重要な確認がある場合は短く説明。通常は「ー」）\n\n[追加情報]"
    )
    ix["setVariable_prompt2"]["value"] = p2
    judge = ix["answer_photoGuidelineJudge"]
    judge["additionalInstructions"] = judge["additionalInstructions"].replace("[追加情報] [措置済み] [要確認] [判定なし]", "[ユーザーへの回答] [追加情報] [措置済み] [要確認] [判定なし]")
    judge["additionalInstructions"] = judge["additionalInstructions"].replace("の4見出し", "の5見出し")
    judge["additionalInstructions"] += "\n対象物と設置行為が確認でき、適合条件だけ不明・不適合なら【写真有】【!】として措置済みに残し、要確認とユーザー回答に再撮影・是正確認を記載してください。対象物自体を断定できない場合は措置済みにしないでください。"
    fallback = ix["setVariable_photoGuideUnavailableResult"]
    fallback["value"] = fallback["value"].replace('="[追加情報]"', '="[ユーザーへの回答]" & Char(10) & "・撮影要領を取得できなかったため、画像の実施判定は保留しました。" & Char(10) & "[追加情報]"')

    answer_extract = setv("setVariable_imageUserAnswerFromJudge", "Topic.画像ユーザー回答", '=If("[ユーザーへの回答]" in Topic.要領照合結果, With({bodyText: Trim(First(Split(Last(Split(Topic.要領照合結果, "[ユーザーへの回答]")).Value, "[追加情報]")).Value)}, If(Or(bodyText = "・ー", bodyText = "ー"), "ー", Trim(Substitute(bodyText, "・", "")))), "ー")')
    insert_before(doc, "setVariable_sectionExtra", [answer_extract])
    sections = index(doc)["conditionGroup_sectionsMissing"]
    sections["conditions"][0]["condition"] = sections["conditions"][0]["condition"].replace('And("[追加情報]"', 'And("[ユーザーへの回答]" in Topic.要領照合結果, "[追加情報]"')
    sections["conditions"][0]["actions"].insert(0, setv("setVariable_fallbackImageUserAnswer", "Topic.画像ユーザー回答", '="撮影要領との照合形式を確認できなかったため、画像の実施判定は保留しました。"'))

    insert_before(doc, "setVariable_globalDone", [setv("setVariable_globalImageUserAnswer", "Global.写真ユーザー回答テキスト", '=If(IsBlank(Topic.画像ユーザー回答), "ー", Topic.画像ユーザー回答)')])
    history = index(doc)["setVariable_appendImageResultToGlobalHistory"]
    old = history["value"]
    history["value"] = '=If(Topic.画像関連判定 = "関連なし", Global.緊急保安追加情報履歴, ' + old[1:] + ')'
    response = index(doc)["sendActivity_analysisResult"]
    response["activity"] = response["activity"].replace(
        "画像を分析しました（{Topic.画像ファイル名}）。\n\n",
        "画像を分析しました（{Topic.画像ファイル名}）。\n\n【ユーザーへの回答】\n{If(IsBlank(Topic.画像ユーザー回答), \"ー\", Topic.画像ユーザー回答)}\n\n"
    ).replace("【要確認】", "【確認したいこと】")
    return doc


def main():
    for folder in (ROOT, ROOT / "source", ROOT / "validation"):
        folder.mkdir(parents=True, exist_ok=True)
    sources = {}
    for name in (ENTRY, FIELD, IMAGE, INSTRUCTIONS):
        data = raw_source(name)
        sources[name] = data
        (ROOT / "source" / name).write_bytes(data)
    outputs = {
        "3-9_貼り替え用.txt": build_field(sources[FIELD]),
        "4-9_貼り替え用.txt": build_image(sources[IMAGE]),
    }
    for name, document in outputs.items():
        dump(document, ROOT / name)
    scope = {
        "baseline": BASE,
        "source_sha256": {name: hashlib.sha256(data).hexdigest() for name, data in sources.items()},
        "outputs": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in outputs},
        "changed_topics": [FIELD, IMAGE],
        "unchanged_topics": [ENTRY],
        "unchanged_global_instructions": INSTRUCTIONS,
        "apps_changed": False,
        "power_automate_changed": False,
        "lists_changed": False,
    }
    (ROOT / "validation/scope.json").write_text(json.dumps(scope, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for target, original in (("3-9_貼り替え用.txt", sources[FIELD]), ("4-9_貼り替え用.txt", sources[IMAGE])):
        (ROOT / "validation" / (target + ".diff")).write_text("".join(difflib.unified_diff(original.decode().splitlines(True), (ROOT / target).read_text().splitlines(True), fromfile="before/" + target, tofile="after/" + target)), encoding="utf-8")
    print("Built", ", ".join(outputs))


if __name__ == "__main__":
    main()
