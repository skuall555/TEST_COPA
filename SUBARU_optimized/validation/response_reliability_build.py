"""Use a single operational rulebook; keep detailed design sources outside model input."""
from pathlib import Path
from restart_support import edit,setv
from itemized_build import lit
ROOT=Path(__file__).resolve().parents[1]
SOURCE='runtime_prompts/01_緊急保安_判定ルール.md'
def apply(field):
    def guide(n):n['value']=lit((ROOT/SOURCE).read_text().rstrip())
    def answer(n):
        n['additionalInstructions']='固定ガイドと現場報告のみで判定する。内部ブロック形式で返し、外部検索や前置き、7見出しの直接出力はしない。優先度と実施状況を独立に決める。室内・共用部臭気のP07と臭気／反応箇所のP09は高であり、設備や実施状況不明を理由に中へ下げない。基本措置の高を要請・避難へ横流ししない。実施済みの操作は保持し、追加範囲と効果確認を分ける。NEXTは高の未完了作業と効果確認を優先し質問だけにしない。CHECKは既報を繰り返さず、判断が変わる確認を1〜3点、理由付きの短い文章にする。'
        return [setv('setVariable_priorityBeforeAISnapshot','Topic.優先度経路診断','="subaru-text-20261102-v2|stage=beforeAI|inputChars=" & Text(Len(Topic.優先度判定プロンプト))'),n,setv('setVariable_priorityAfterAISnapshot','Topic.優先度経路診断','="subaru-text-20261102-v2|stage=afterAI|outputChars=" & Text(Len(Topic.優先度判定結果))')]
    def diagnostic(stage):
        return '="subaru-text-20261102-v2|stage='+stage+'|validation=" & Topic.優先度表示検証 & "|rawChars=" & Text(Len(Topic.優先度表示原文)) & "|displayChars=" & Text(Len(Topic.優先度表示組立)) & "|retry=" & Text(Topic.優先度様式再試行回数)'
    def gate(n):
        return [setv('setVariable_priorityGateSnapshot','Topic.優先度経路診断',diagnostic('gate')),n]
    def failed(n):
        return [setv('setVariable_priorityFailedSnapshot','Topic.優先度経路診断',diagnostic('failed')),n]
    def wait(n):
        return [setv('setVariable_priorityWaitSnapshot','Topic.優先度経路診断',diagnostic('wait')),n]
    def save(n):
        return [setv('setVariable_priorityBeforeSaveSnapshot','Topic.優先度経路診断',diagnostic('beforeCaseSave')),n,setv('setVariable_priorityAfterSaveSnapshot','Topic.優先度経路診断',diagnostic('afterCaseSave'))]
    def initialize(n):
        return [n,setv('setVariable_priorityPreviousResultInit','Topic.優先度判定結果','=""'),setv('setVariable_priorityPreviousCheckInit','Topic.優先度表示検証','=""')]
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'answer_priority':answer,'conditionGroup_prioritySucceeded':gate,'sendActivity_priorityFailed':failed,'question_priorityUpdate':wait,'setVariable_priorityFormatRetryInit':initialize,'invokeFlowAction_caseSaveFieldAdvice':save}))
