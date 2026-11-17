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


def question(ident, variable, prompt, allow_interruption=False):
    return {
        "kind": "Question",
        "id": ident,
        "interruptionPolicy": {"allowInterruption": allow_interruption},
        "variable": variable,
        "prompt": prompt,
        "entity": {"kind": "StringPrebuiltEntity", "sensitivityLevel": "None"},
    }


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


CONSULT_SIGNAL = '=With({t: Lower(Trim(Topic.最新利用者入力))}, Or("?" in t, "？" in t, "教えて" in t, "どうす" in t, "どうした" in t, "どう進" in t, "どうしよう" in t, "何を" in t, "なにを" in t, "どこ" in t, "いつ" in t, "なぜ" in t, "理由" in t, "相談" in t, "困って" in t, "迷って" in t, "確認したい" in t, "確認して" in t, "確認すべき" in t, "すればいい" in t, "したらいい" in t, "していい" in t, "でいい" in t, "大丈夫" in t, "必要ですか" in t, "必要か" in t, "次の調査" in t, "次に調査" in t, "このあと" in t, "この後" in t, "マニュアル" in t, "規定" in t, "基準" in t))'

ITEM_TERMS = {
    "P01": ["火気", "着火", "喫煙"],
    "P02": ["電気", "スイッチ", "換気扇"],
    "P03": ["火気厳禁", "表示シート", "表示"],
    "P04": ["ポケット警報器", "警報器", "監視機器"],
    "P05": ["検知器", "検知", "測定", "調査", "反応", "濃度", "lel", "排水口"],
    "P06": ["換気", "窓", "扉"],
    "P07": ["メーターガス栓", "メーター栓", "メーター", "閉止"],
    "P08": ["分岐バルブ", "引込管", "遮断装置", "上流遮断"],
    "P09": ["消火器"],
    "P10": ["周辺住戸", "周辺建物", "周辺調査", "隣家", "別住戸"],
    "P11": ["消防", "警察", "要請", "通報"],
    "P12": ["避難", "退避", "誘導"],
    "P13": ["保安柵", "バリケード", "コーン", "立入", "規制"],
    "P14": ["高濃度", "ガス種", "濃度確認"],
    "P15": ["進入禁止", "進入"],
    "P16": ["保安範囲", "再設置", "拡大"],
    "P17": ["マンホール", "蓋", "開放"],
    "P18": ["救護", "負傷", "体調", "中毒"],
    "P19": ["空気呼吸器", "呼吸器"],
    "P20": ["追加検知", "追加調査", "未確認範囲"],
    "P21": ["周辺調査", "再調査", "調査拡大"],
    "P22": ["追加遮断", "供給遮断", "別系統"],
    "P23": ["圧力", "供給支障", "ガス不出", "弱火"],
}

PHOTO_IDS = {
    "P03": ["MS-003", "MS-004", "MS-005"],
    "P04": ["MS-007", "MS-008", "MS-009"],
    "P05": ["MS-011", "MS-012", "MS-013", "MS-014", "MS-015"],
    "P06": ["MS-006"],
    "P07": ["MS-001"],
    "P08": ["MS-002"],
    "P09": ["MS-010"],
    "P13": ["MS-016"],
}

STATE_CHANGE_TERMS = [
    "再撮影", "撮り直", "全景", "周辺を含", "設置場所", "位置確認", "確認済", "確認でき",
    "追加調査", "再調査", "調査範囲", "範囲確認", "是正", "移動", "撤去", "外した",
    "誤認", "間違", "訂正", "未実施", "していない", "できていない", "なかった", "設置済",
    "実施済", "対応済", "完了",
]


def any_in(terms, expression):
    checks = [f'"{term}" in {expression}' for term in terms]
    if not checks:
        return "false"
    if len(checks) == 1:
        return checks[0]
    return "Or(" + ", ".join(checks) + ")"


def item_state_guard(code):
    item_related = any_in(ITEM_TERMS[code], "latestText")
    change_signal = any_in(STATE_CHANGE_TERMS, "latestText")
    photo_related = any_in(PHOTO_IDS.get(code, []), "Global.写真措置済みテキスト")
    return (
        '=If(Topic.優先度表示検証 <> "合格", Topic.優先度表示検証, '
        'With({previousText: Topic.前回確定優先度原文, '
        f'previousBody: If("[[{code}]]" in Topic.前回確定優先度原文, Substitute(First(Split(Last(Split(Topic.前回確定優先度原文, "[[{code}]]")).Value, "[[/{code}]]")).Value, "｜", "|"), ""), '
        'currentStatus: Switch(Trim(Last(FirstN(Split(Topic.優先度表示区分, "|"), 2)).Value), "実施済み", "対応済み", "実施済", "対応済み", "対応済", "対応済み", "完了", "対応済み", "未確認", "要確認", "不明", "要確認", Trim(Last(FirstN(Split(Topic.優先度表示区分, "|"), 2)).Value)), '
        'latestText: Lower(Trim(Topic.最新利用者入力))}, '
        'With({previousStatus: If(IsBlank(previousBody), "", Switch(Trim(Last(FirstN(Split(previousBody, "|"), 2)).Value), "実施済み", "対応済み", "実施済", "対応済み", "対応済", "対応済み", "完了", "対応済み", "未確認", "要確認", "不明", "要確認", Trim(Last(FirstN(Split(previousBody, "|"), 2)).Value))), '
        f'itemMayChange: Or(And({item_related}, {change_signal}), And(Topic.写真判定反映中, {photo_related})), '
        f'photoRequiresDone: And(Topic.写真判定反映中, {photo_related})}}, '
        'If(And('
        'Or(IsBlank(previousBody), Not(Or(previousStatus = "対応済み", previousStatus = "対応済み【!】")), currentStatus = previousStatus, itemMayChange), '
        'Or(Not(photoRequiresDone), Or(currentStatus = "対応済み", currentStatus = "対応済み【!】"))'
        f'), "合格", "不合格:itemStateStable{code}"))))'
    )


def build_field(raw):
    doc = yaml.safe_load(raw)
    ix = index(doc)
    doc["modelDescription"] += "\n  現場対応中の相談・質問はこのトピック内で処理し、親エージェントの自由回答へ切り替えない。\n  進捗報告だけのときはユーザー回答を「ー」とする。相談文に含まれる具体的な現場事実は履歴へ保持する。\n  画像付き発話は4-9の完了を待ってから一度だけ反映し、画像と同時の文章を重複登録しない。\n  前回確定した対応済み・対応済み【!】は項目別に保持し、その項目を更新する明示情報がない限り変更しない。\n  優先度AIの形式不正時はこのトピックを終了せず、固定形式で再試行・待機する。\n"

    insert_after(doc, "setVariable_imageReceptionOffAtStart", [
        setv("setVariable_latestUserInputAtStart", "Topic.最新利用者入力", "=Topic.初回入力"),
        setv("setVariable_previousPriorityRawInit", "Topic.前回確定優先度原文", '=""'),
        setv("setVariable_previousPriorityDisplayInit", "Topic.前回確定優先度表示", '=""'),
    ])

    consult_answer = {
        "kind": "AnswerQuestionWithAI",
        "id": "answer_userConsult",
        "displayName": "11A_マニュアル早見表からの現場相談回答",
        "autoSend": False,
        "variable": "Topic.ユーザー相談回答候補",
        "userInput": '="【今回の相談】" & Char(10) & Topic.最新利用者入力 & Char(10) & Char(10) & "【初報】" & Char(10) & Topic.初回入力 & Char(10) & Char(10) & "【これまでの現場報告】" & Char(10) & Topic.追加情報履歴 & Char(10) & Char(10) & "【現在表示中の判断】" & Char(10) & Topic.優先度判定結果 & Char(10) & Char(10) & "【マニュアルから固定した緊急保安早見表】" & Char(10) & Topic.優先度ガイド取得結果',
        "additionalInstructions": "利用者の相談へ最初の一文から直接答え、現場担当者との壁打ちとして、次に何を考え、何を確認し、どの条件なら対応が変わるかを短く具体的に示してください。入力内の緊急保安早見表と報告済み事実だけを根拠にし、一般知識や未報告事実を作らないでください。早見表はマニュアルから固定した根拠です。検索結果、原文取得、ナレッジヒットの有無には言及しないでください。情報が足りない場合も回答を拒否せず、既に言えることを先に答え、判断を分ける確認を最大2点だけ質問してください。危険条件が早見表に成立する場合は追加回答待ちで結論を保留しないでください。優先度一覧や定型見出しは出力せず、相談への自然な回答だけを返してください。",
    }
    consult_nodes = [
        setv("setVariable_imageAnswerPending", "Topic.写真回答反映中", '=And(Not(IsBlank(Global.写真ユーザー回答テキスト)), Trim(Global.写真ユーザー回答テキスト) <> "ー")'),
        setv("setVariable_imageDecisionPending", "Topic.写真判定反映中", '=Global.写真判定反映待ち'),
        setv("setVariable_imageAnswerCarry", "Topic.画像引継ぎ回答", '=If(Topic.写真回答反映中, Trim(Global.写真ユーザー回答テキスト), "ー")'),
        setv("setVariable_userConsultAnswerReset", "Topic.判定ユーザー回答", '=Topic.画像引継ぎ回答'),
        setv("setVariable_userConsultCandidateReset", "Topic.ユーザー相談回答候補", '=""'),
        setv("setVariable_userConsultSignal", "Topic.ユーザー相談あり", CONSULT_SIGNAL),
        condition("conditionGroup_userConsultSearch", "=Topic.ユーザー相談あり", [
            consult_answer,
            setv("setVariable_userConsultAnswer", "Topic.判定ユーザー回答", '=With({consultText: If(IsBlank(Topic.ユーザー相談回答候補), "現在の報告だけでは相談内容を断定できません。表示中の未完了措置を止めず、判断を分ける現場情報を追加してください。", Trim(Topic.ユーザー相談回答候補))}, If(Topic.写真回答反映中, Topic.画像引継ぎ回答 & Char(10) & If(StartsWith(consultText, "└"), consultText, "└" & consultText), If(StartsWith(consultText, "└"), consultText, "└" & consultText)))'),
        ]),
    ]
    insert_before(doc, "setVariable_priorityPrompt", consult_nodes)

    ix = index(doc)
    prompt = ix["setVariable_priorityPrompt"]["value"]
    prompt = prompt.replace(
        '" & Topic.追加情報履歴 & "\n最新の明示報告を優先する。',
        '" & Topic.追加情報履歴 & "\n【今回の最新入力】\n" & Topic.最新利用者入力 & "\n【前回確定した内部判定】\n" & If(IsBlank(Topic.前回確定優先度原文), "なし", Topic.前回確定優先度原文) & "\n最新の明示報告を優先する。'
    )
    prompt = prompt.replace(
        "優先度は高／中／低、状態は対応済み／未実施／要確認の一つずつ。",
        "優先度は高／中／低、状態は対応済み／対応済み【!】／未実施／要確認の一つずつ。"
    )
    prompt = prompt.replace(
        "# 実施済みと範囲・効果",
        "# 質問を含む追加入力の事実抽出\n追加情報に質問・相談の表現が含まれていても、文中で具体的に報告された現場状況・警報・臭気・検知・不在・入室可否・実施済み措置は事実として保持する。質問、依頼、推測、AIの回答自体は事実にしない。\n\n# 前回確定状態の継承\n前回確定したP番号別の実施状況を状態台帳として扱う。対応済みまたは対応済み【!】は、今回の最新入力が同じP番号の実施・訂正・撤去・再撮影・適合確認を明示しない限り、状態も警告も一字も変更しない。別項目の進捗、別場所の情報、危険度の変化だけで対応済み【!】を対応済み・要確認・未実施へ変更しない。警告を外せるのは、警告理由そのものが新しい報告または写真で解消した場合だけ。画像のMS番号で実施済みが確認された項目を要確認・未実施へ戻さない。\n\n# 写真の警告付き対応済み\n画像履歴に【写真有】【!】がある場合、対象物と設置行為は確認できるが、設置場所・適合条件・撮影範囲に確認が残ることを示す。該当措置の状態を対応済み【!】とし、根拠には角括弧を使わず、確認できた実施と残る確認を分けて書く。対応済み【!】は高優先度の完了扱いにせず、NEXTまたはCHECKで再撮影・位置確認等を残す。対象物自体を断定できない画像は対応済み【!】にせず要確認とする。\n\n# 実施済みと範囲・効果"
    )
    ix["setVariable_priorityPrompt"]["value"] = prompt
    ix["answer_priority"]["additionalInstructions"] = "固定ガイドと現場報告のみで判定する。内部ブロック形式で返し、外部検索や前置き、7見出しの直接出力はしない。優先度と実施状況を独立に決める。室内・共用部臭気のP07と臭気／反応箇所のP09は高であり、設備や実施状況不明を理由に中へ下げない。基本措置の高を要請・避難へ横流ししない。不在・施錠・入室不能の住戸で警報器が現在鳴っている、または鳴り続ける報告はE-01を必ず照合し、通常の単独臭気初報としてP11・P12を低へ戻さない。前回確定した対応済み・対応済み【!】はP番号別の状態台帳であり、今回の最新入力が同じ項目の警告理由を明示的に解消・訂正しない限り同じ状態を厳密に維持する。別項目の進捗で【!】を消さない。画像履歴の【写真有】とMS番号は対応済みの根拠であり要確認へ戻さない。実施済みの操作は保持し、追加範囲と効果確認を分ける。NEXTは高の未完了作業と効果確認を優先し質問だけにしない。CHECKは既報を繰り返さず、判断が変わる確認を1〜3点、理由付きの短い文章にする。画像履歴の【写真有】【!】は対応済み【!】、物体自体が未確定なら要確認とする。"

    # Keep consultation inside the active field dialog, without adding the question to fact history.
    manual_switch = ix["conditionGroup_priorityPurposeSwitchToJunkai"]
    insert_after(doc, "setVariable_resyncHistoryFromGlobal", [
        setv("setVariable_latestUserInputAfterWait", "Topic.最新利用者入力", "=Topic.優先度追加回答"),
        condition("conditionGroup_priorityImageActivity", '=Or(Not(IsEmpty(System.Activity.Attachments)), Global.写真分析処理中, Global.写真判定反映待ち, Lower(Trim(Topic.最新利用者入力)) = "反映")', [
            condition("conditionGroup_priorityImageStillRunning", "=Or(Global.写真分析処理中, And(Not(IsEmpty(System.Activity.Attachments)), Not(Global.写真判定反映待ち)))", [
                question("question_priorityImageReflect", "Topic.画像反映合図", "画像分析結果が表示されたら「反映」と入力してください。画像分析結果が表示されない場合は、画像をもう一度送ってください。続報がある場合は、その内容を入力しても構いません。", True),
                setv("setVariable_resyncImageHistoryAfterReflect", "Topic.追加情報履歴", "=Global.緊急保安追加情報履歴"),
                setv("setVariable_latestImageReflectInput", "Topic.最新利用者入力", "=Topic.画像反映合図"),
                setv("setVariable_appendImageReflectExtra", "Topic.追加情報履歴", '=If(Or(IsBlank(Trim(Topic.画像反映合図)), Lower(Trim(Topic.画像反映合図)) = "反映", Trim(Topic.画像反映合図) = Trim(Global.写真同時テキスト)), Topic.追加情報履歴, Topic.追加情報履歴 & Char(10) & "追加情報：" & Topic.画像反映合図)'),
                setv("setVariable_syncImageReflectExtra", "Global.緊急保安追加情報履歴", "=Topic.追加情報履歴"),
                {"kind": "GotoAction", "id": "goto_priorityAfterImageWait", "actionId": "setVariable_imageAnswerPending"},
            ], [
                setv("setVariable_appendPendingImageExtra", "Topic.追加情報履歴", '=If(Or(IsBlank(Trim(Topic.最新利用者入力)), Lower(Trim(Topic.最新利用者入力)) = "反映", Trim(Topic.最新利用者入力) = Trim(Global.写真同時テキスト), Not(IsEmpty(System.Activity.Attachments))), Topic.追加情報履歴, Topic.追加情報履歴 & Char(10) & "追加情報：" & Topic.最新利用者入力)'),
                setv("setVariable_syncPendingImageExtra", "Global.緊急保安追加情報履歴", "=Topic.追加情報履歴"),
                {"kind": "GotoAction", "id": "goto_priorityAfterImageReady", "actionId": "setVariable_imageAnswerPending"},
            ]),
        ]),
        setv("setVariable_userConsultSignalAfterWait", "Topic.ユーザー相談あり", CONSULT_SIGNAL),
    ])
    replace(doc, "conditionGroup_priorityPurposeSwitchToJunkai", [
        condition("conditionGroup_priorityConsultOrProgress", "=Topic.ユーザー相談あり", [
            setv("setVariable_appendConsultHistory", "Topic.追加情報履歴", '=Topic.追加情報履歴 & Char(10) & "追加情報：" & Topic.優先度追加回答'),
            setv("setVariable_syncHistoryAfterConsult", "Global.緊急保安追加情報履歴", '=Topic.追加情報履歴'),
            setv("setVariable_keepImageReceptionOnForConsult", "Global.緊急保安画像受付中", "=true"),
            {"kind": "GotoAction", "id": "goto_priorityConsult", "actionId": "setVariable_imageAnswerPending"},
        ], copy.deepcopy(manual_switch["elseActions"]))
    ])
    index(doc)["goto_priorityAgain"]["actionId"] = "setVariable_imageAnswerPending"
    index(doc)["question_priorityUpdate"]["interruptionPolicy"]["allowInterruption"] = False

    # Accept the warning status while keeping it incomplete until the warning is resolved.
    for code in [f"P{i:02d}" for i in range(1, 24)]:
        node = index(doc).get("setVariable_itemValid" + code)
        if node:
            node["value"] = node["value"].replace('Or(itemStatus = "対応済み", itemStatus = "未実施", itemStatus = "要確認")', 'Or(itemStatus = "対応済み", itemStatus = "対応済み【!】", itemStatus = "未実施", itemStatus = "要確認")')
            insert_after(doc, "setVariable_itemValid" + code, [
                setv("setVariable_itemStateStable" + code, "Topic.優先度表示検証", item_state_guard(code)),
            ])

    render = index(doc)["setVariable_itemRender"]
    render["value"] = render["value"].replace('="【確認できた事実】', '="【ユーザーへの回答】" & Char(10) & Topic.判定ユーザー回答 & Char(10) & Char(10) & "【確認できた事実】')
    insert_before(doc, "invokeFlowAction_caseSaveFieldAdvice", [
        setv("setVariable_commitPreviousPriorityRaw", "Topic.前回確定優先度原文", "=Topic.優先度表示原文"),
        setv("setVariable_commitPreviousPriorityDisplay", "Topic.前回確定優先度表示", "=Topic.優先度判定結果"),
    ])
    insert_after(doc, "invokeFlowAction_caseSaveFieldAdvice", [
        condition("conditionGroup_clearImageAnswerAfterSave", "=Or(Topic.写真回答反映中, Topic.写真判定反映中)", [
            setv("setVariable_clearImageAnswerAfterSave", "Global.写真ユーザー回答テキスト", '="ー"'),
            setv("setVariable_clearImageAnswerPending", "Topic.写真回答反映中", "=false"),
            setv("setVariable_clearImageDecisionAfterSave", "Global.写真判定反映待ち", "=false"),
            setv("setVariable_clearImageDecisionPending", "Topic.写真判定反映中", "=false"),
            setv("setVariable_clearImageTurnTextAfterSave", "Global.写真同時テキスト", '=""'),
            setv("setVariable_clearImageDoneAfterSave", "Global.写真措置済みテキスト", '=""'),
            setv("setVariable_clearImageCheckAfterSave", "Global.写真要確認テキスト", '=""'),
        ])
    ])

    # A malformed AI payload is retried once.  A second failure keeps this dialog alive
    # instead of dropping the user into the parent agent's unrestricted free answer.
    succeeded = index(doc)["conditionGroup_prioritySucceeded"]
    succeeded["elseActions"] = [
        condition("conditionGroup_priorityFormatRetry", "=Topic.優先度様式再試行回数 < 1", [
            setv("setVariable_priorityFormatRetryIncrement", "Topic.優先度様式再試行回数", "=Topic.優先度様式再試行回数 + 1"),
            setv("setVariable_priorityFormatRetryPrompt", "Topic.優先度判定プロンプト", '=Topic.優先度判定プロンプト & Char(10) & Char(10) & "前回の生成は形式検証で不合格でした。原因：" & Topic.優先度表示検証 & "。内容を自由形式へ変えず、指定した内部ブロックだけを完全な順序で再出力してください。前回確定した対応済み・対応済み【!】を無関係な最新入力で変更しないでください。"'),
            {"kind": "GotoAction", "id": "goto_priorityFormatRetry", "actionId": "answer_priority"},
        ], [
            setv("setVariable_imageReceptionOnPriorityRecovery", "Global.緊急保安画像受付中", "=true"),
            setv("setVariable_priorityFailedSnapshot", "Topic.優先度経路診断", '="subaru-text-20261117-v4|stage=recover|validation=" & Topic.優先度表示検証 & "|rawChars=" & Text(Len(Topic.優先度表示原文)) & "|retry=" & Text(Topic.優先度様式再試行回数)'),
            question("question_priorityFormatRecovery", "Topic.優先度形式再開入力", "回答形式を自動修復できなかったため、未検証の回答は表示・保存していません。会話は継続しています。「再試行」と入力するか、新しい現場情報を入力してください。", False),
            setv("setVariable_resyncHistoryAfterFormatRecovery", "Topic.追加情報履歴", "=Global.緊急保安追加情報履歴"),
            setv("setVariable_latestInputAfterFormatRecovery", "Topic.最新利用者入力", "=Topic.優先度形式再開入力"),
            setv("setVariable_appendAfterFormatRecovery", "Topic.追加情報履歴", '=If(Or(Lower(Trim(Topic.優先度形式再開入力)) = "再試行", Lower(Trim(Topic.優先度形式再開入力)) = "反映"), Topic.追加情報履歴, Topic.追加情報履歴 & Char(10) & "追加情報：" & Topic.優先度形式再開入力)'),
            setv("setVariable_syncAfterFormatRecovery", "Global.緊急保安追加情報履歴", "=Topic.追加情報履歴"),
            {"kind": "GotoAction", "id": "goto_priorityAfterFormatRecovery", "actionId": "setVariable_imageAnswerPending"},
        ]),
    ]
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
        setv("setVariable_imageAnalysisRunning", "Global.写真分析処理中", "=true"),
        setv("setVariable_imageTurnTextGlobal", "Global.写真同時テキスト", "=System.Activity.Text"),
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
    history["value"] = '=If(Topic.画像関連判定 = "関連なし", If(IsBlank(Trim(Topic.画像同時テキスト)), Global.緊急保安追加情報履歴, Global.緊急保安追加情報履歴 & Char(10) & "追加情報（画像同時テキスト）：" & Topic.画像同時テキスト), ' + old[1:] + ')'
    insert_before(doc, "sendActivity_analysisResult", [
        setv("setVariable_imageAnalysisComplete", "Global.写真分析処理中", "=false"),
        setv("setVariable_imageDecisionReady", "Global.写真判定反映待ち", "=true"),
    ])
    insert_before(doc, "endDialog_unsupportedImageType", [
        setv("setVariable_imageAnalysisStopUnsupported", "Global.写真分析処理中", "=false"),
    ])
    insert_after(doc, "setVariable_imageReceptionBackOn", [
        setv("setVariable_imageAnalysisStopPromptMissing", "Global.写真分析処理中", "=false"),
    ])
    response = index(doc)["sendActivity_analysisResult"]
    response["activity"] = response["activity"].replace(
        "画像を分析しました（{Topic.画像ファイル名}）。\n\n",
        "画像を分析しました（{Topic.画像ファイル名}）。\n\n【ユーザーへの回答】\n{If(IsBlank(Topic.画像ユーザー回答), \"ー\", Topic.画像ユーザー回答)}\n\n"
    ).replace("【要確認】", "【確認したいこと】").replace(
        "この内容を初動措置の判定へ反映します。続けて何か一言（例：「反映」）を送ってください。別の写真を続けて送っていただいても構いません。",
        "この内容を初動措置の判定へ自動反映します。自動反映が続かない場合だけ「反映」と送ってください。別の写真を続けて送っていただいても構いません。"
    )
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
        diff_text = "".join(difflib.unified_diff(original.decode().splitlines(True), (ROOT / target).read_text().splitlines(True), fromfile="before/" + target, tofile="after/" + target))
        clean_diff = "\n".join(line.rstrip() for line in diff_text.splitlines()) + "\n"
        (ROOT / "validation" / (target + ".diff")).write_text(clean_diff, encoding="utf-8")
    print("Built", ", ".join(outputs))


if __name__ == "__main__":
    main()
