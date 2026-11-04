"""Scoped patches to the existing agent; no new agent or fabricated flow IDs."""
from pathlib import Path
import sys,shutil,json,yaml
from yaml_edit import edit,setv,cg,dump,nodes
ROOT=Path(__file__).resolve().parents[1];REPO=ROOT.parent
MEASURES=json.loads((ROOT/'contracts/measures.json').read_text())
FILES=['1-マニュアル関連入口_optimized.yaml','3-9-緊急保安業務エージェント_optimized.yaml','4-9-画像分析エージェント_緊急保安_optimized.yaml']
SAVE_ID='9a770168-65a8-f111-aaad-7ced8d2f9cab'
FIELD_DIALOG='cr88f_SUBARU_search.topic.9xY'
def q(s):return '"'+s.replace('"','""')+'"'
def lit(s):return '='+q(s)
REPAIR_WORDS=['修理方法','修理の方法','修理手順','どう直す','どうやって直す','復旧方法','修理工法','補修手順','補修方法','直し方','直す方法']
def repair_requested(var):return 'Or('+', '.join(q(word)+' in '+var for word in REPAIR_WORDS)+')'
def go(ident,target):return {'kind':'GotoAction','id':ident,'actionId':target}
def question(ident,var,prompt):return {'kind':'Question','id':ident,'interruptionPolicy':{'allowInterruption':True},'variable':var,'prompt':prompt,'entity':{'kind':'StringPrebuiltEntity','sensitivityLevel':'None'}}
def append_actions(p,actions):
 s=p.read_text();a=s.rfind('\ninputType:');assert a>0;p.write_text(s[:a]+'\n'+dump(actions,4)+s[a:])
def label_expr(code):return 'Switch('+code+', '+', '.join(q(k)+', '+q(v)for k,v in MEASURES)+', '+code+')'
def snapshot_expr():
 code='Switch(true, '+', '.join('StartsWith(labelText, '+q('└'+name+'：')+'), '+q(code)for code,name in MEASURES)+', "")'
 return '=Concat(Filter(Split(Topic.判定表示行, Char(30)), Not(IsBlank(Value))), With({parts: Split(Value, "|")}, With({labelText: Last(parts).Value}, '+code+' & "|" & First(parts).Value & "|" & Last(FirstN(parts, 2)).Value)), Char(10))'
def changes_expr():
 # Assemble nested calls structurally so parentheses cannot drift during edits.
 def call(name,*args):return name+'('+', '.join(args)+')'
 def w(fields,body):return call('With','{'+', '.join(k+': '+v for k,v in fields.items())+'}',body)
 def rs(var):return call('Filter',call('Split',var,'Char(10)'),'Not(IsBlank(Value))')
 oldp='Last(FirstN(Split(previous, "|"), 2)).Value';olds='Last(Split(previous, "|")).Value'
 label=label_expr('code')
 line='"・" & '+label+' & "："'
 change=call('If','IsBlank(previous)',line+' & "新規項目（" & priority & "／" & state & "）"',call('If','priority <> '+oldp,line+' & '+oldp+' & " → " & priority',call('If','state <> '+olds,line+' & "状態 " & '+olds+' & " → " & state & "（優先度 " & priority & " は同じ）"','""')))
 previous='First(Filter(Split(Topic.前回現場スナップショット, Char(10)), StartsWith(Value, code & "|"))).Value'
 current=call('Concat',rs('Topic.今回現場スナップショット'),w({'parts':'Split(Value, "|")'},w({'code':'First(parts).Value','priority':'Last(FirstN(parts, 2)).Value','state':'Last(parts).Value'},w({'previous':previous},change))),'Char(10)')
 absent='IsBlank(First(Filter(Split(Topic.今回現場スナップショット, Char(10)), StartsWith(Value, code & "|"))).Value)'
 removed=call('Concat',rs('Topic.前回現場スナップショット'),w({'code':'First(Split(Value, "|")).Value'},call('If',absent,line+' & "今回は未判定（解消とは判定しません）"','""')),'Char(10)')
 found=w({'changes':'Trim('+current+' & Char(10) & '+removed+')'},'If(IsBlank(changes), "前回から優先度の変更なし", changes)')
 return '=If(Topic.前回比較状態 = "found", '+found+', If(Topic.前回比較状態 = "first", "", "前回比較は現在できません。別案件や未確認の過去情報とは比較していません。"))'

def teams_expr():
 s='"📍 現場アドバイス" & Char(10) & If(Topic.前回比較状態 = "first", "", Char(10) & "【① 前回報告からの変更点】" & Char(10) & Topic.優先度変更点 & Char(10)) & Char(10) & "【② 初動措置の優先度】"'
 for title,var in [('🔴 高','判定高欄'),('🟠 中','判定中欄'),('🟢 低','判定低欄')]:s+=' & Char(10) & '+q(title)+' & Char(10) & If(IsBlank(Topic.'+var+'), "・該当なし", Substitute(Topic.'+var+', "└", "・"))'
 s+=' & Char(10) & Char(10) & "【③ 確認したいこと】" & Char(10) & Topic.判定確認文 & Char(10) & Char(10) & "【④ ネクストアクション】" & Char(10) & Substitute(Topic.判定次行動, "└", "・")'
 return '='+s

def case_init():
 out=[setv('setVariable_teamsIncoming','Topic.今回受信文','=Topic.初回入力'),setv('setVariable_teamsMode','Topic.判定応答方式','=Coalesce(Topic.判定応答方式, "通常")'),setv('setVariable_teamsChannel','Topic.投稿チャネル','=Lower(Coalesce(System.Activity.ChannelId, "unknown"))'),setv('setVariable_teamsOwner','Topic.案件所有者','=System.User.Id'),setv('setVariable_teamsExplicitCase','Topic.明示案件指定','=If(StartsWith(Trim(Topic.今回受信文), "案件ID="), "あり", "なし")'),setv('setVariable_teamsCaseKey','Topic.案件比較キー','=If(Trim(Topic.今回受信文) = "新しい案件", Text(GUID()), If(Topic.明示案件指定 = "あり", Trim(First(Split(Mid(Trim(Topic.今回受信文), 6), Char(10))).Value), If(And(Not(IsBlank(Global.TeamsCaseKey)), Global.TeamsCaseOwner = Topic.案件所有者), Global.TeamsCaseKey, Text(GUID()))))'),setv('setVariable_teamsResume','Topic.案件継続','=If(And(Global.TeamsCaseKey = Topic.案件比較キー, Global.TeamsCaseOwner = Topic.案件所有者), "はい", "いいえ")')]
 out += [cg('conditionGroup_teamsResumeHistory','=And(Topic.案件継続 = "はい", Topic.判定応答方式 <> "画像単発")',[setv('setVariable_teamsRestoreInitial','Topic.初回入力','=Global.緊急保安初回入力'),setv('setVariable_teamsRestoreHistory','Topic.追加情報履歴','=Global.緊急保安追加情報履歴 & Char(10) & "追加情報：" & Topic.今回受信文')]),cg('conditionGroup_teamsFreshScope','=Topic.案件継続 <> "はい"',[setv('setVariable_teamsClearSnapshot','Global.TeamsLastFieldSnapshot','=""'),setv('setVariable_teamsClearCaseId','Global.TeamsLastCaseId','=""'),setv('setVariable_teamsClearCount','Global.TeamsFieldReportCount','=0')])]
 for ident,var,expr in [('ScopeKey','Global.TeamsCaseKey','=Topic.案件比較キー'),('ScopeOwner','Global.TeamsCaseOwner','=Topic.案件所有者'),('Initial','Global.緊急保安初回入力','=Topic.初回入力'),('History','Global.緊急保安追加情報履歴','=Topic.追加情報履歴'),('RepairFlag','Global.TeamsRepairActive','="いいえ"')]:out.append(setv('setVariable_teamsInit'+ident,var,expr))
 for suffix,var in [('Snapshot','今回現場スナップショット'),('Previous','前回現場スナップショット'),('PreviousId','前回現場案件ID'),('Compare','前回比較状態'),('Changes','優先度変更点'),('Text','Teams現場回答'),('RepairText','修理最終回答'),('RepairReply','修理後入力'),('SaveStatus','保存状態'),('EventKey','投稿識別子')]:out.append(setv('setVariable_teamsInit'+suffix,'Topic.'+var,'=""'))
 return out

def render_steps():
 return [setv('setVariable_teamsCurrentSnapshot','Topic.今回現場スナップショット',snapshot_expr()),setv('setVariable_teamsPreviousSnapshot','Topic.前回現場スナップショット','=Coalesce(Global.TeamsLastFieldSnapshot, "")'),setv('setVariable_teamsPreviousId','Topic.前回現場案件ID','=Coalesce(Global.TeamsLastCaseId, "")'),setv('setVariable_teamsEventKey','Topic.投稿識別子','=Topic.投稿チャネル & "|" & System.Conversation.Id & "|" & System.User.Id & "|" & System.Activity.Id & "|field_advice"')]
def after_save():
 return [setv('setVariable_teamsCompareStatus','Topic.前回比較状態','=If(Coalesce(Global.TeamsFieldReportCount, 0) = 0, If(Topic.明示案件指定 = "あり", "unavailable", "first"), If(And(Not(IsBlank(Text(Topic.案件ID))), Text(Topic.案件ID) = Topic.前回現場案件ID), "found", "unavailable"))'),setv('setVariable_teamsChanges','Topic.優先度変更点',changes_expr()),setv('setVariable_teamsRender','Topic.Teams現場回答',teams_expr()),setv('setVariable_teamsSaveUnknown','Topic.保存状態','="既存保存フローの応答を受領。SharePoint反映は実環境で確認が必要です。"'),setv('setVariable_teamsCacheSnapshot','Global.TeamsLastFieldSnapshot','=Topic.今回現場スナップショット'),setv('setVariable_teamsCacheCaseId','Global.TeamsLastCaseId','=Text(Topic.案件ID)'),setv('setVariable_teamsCacheLegacy','Global.TeamsLastLegacyText','=Topic.優先度判定結果'),setv('setVariable_teamsCacheReply','Global.TeamsLastTeamsText','=Topic.Teams現場回答'),setv('setVariable_teamsCount','Global.TeamsFieldReportCount','=Coalesce(Global.TeamsFieldReportCount, 0) + 1')]

def save_repair(ident,body_var='Topic.修理最終回答'):
 return {'kind':'InvokeFlowAction','id':ident,'input':{'binding':{'text':'=System.Conversation.Id','text_1':'="マニュアル確認"','text_2':'='+body_var,'text_3':'="修理回答"'}},'output':{'binding':{'case_id':'Topic.修理記録応答ID'}},'flowId':SAVE_ID}
def repair_return_actions():
 return [setv('setVariable_teamsRepairReception','Global.緊急保安画像受付中','=true'),question('question_teamsRepairContinue','Topic.修理後入力','{Topic.修理最終回答}'),setv('setVariable_teamsRepairHistorySync','Topic.追加情報履歴','=Global.緊急保安追加情報履歴'),cg('conditionGroup_teamsNewCaseAfterRepair','=Trim(Topic.修理後入力) = "新しい案件"',[go('goto_teamsNewCaseAfterRepair','question_teamsNewCase')]),cg('conditionGroup_teamsManualAfterRepair','=Or("マニュアル確認" in Topic.修理後入力, "マニュアル改訂" in Topic.修理後入力, "マニュアル改定" in Topic.修理後入力)',[setv('setVariable_teamsManualReturn','Global.巡回切替入力','=Topic.修理後入力'),{'kind':'EndDialog','id':'endDialog_teamsManualReturn'}]),setv('setVariable_teamsRepairAppend','Topic.追加情報履歴','=Topic.追加情報履歴 & Char(10) & "追加情報：" & Topic.修理後入力'),setv('setVariable_teamsRepairSync','Global.緊急保安追加情報履歴','=Topic.追加情報履歴'),cg('conditionGroup_teamsRepairAgain','=Or("修理方法" in Topic.修理後入力, "補修手順" in Topic.修理後入力, "修理工法" in Topic.修理後入力)',[setv('setVariable_teamsRepairAgainOn','Topic.修理方法モード','=true'),go('goto_teamsRepairAgain','setVariable_repairSelectInit')]),setv('setVariable_teamsBackToField','Topic.修理方法モード','=false'),setv('setVariable_teamsRepairOff','Global.TeamsRepairActive','="いいえ"'),go('goto_teamsFieldAfterRepair','setVariable_priorityPrompt')]

def build():
 for name in FILES:shutil.copyfile(ROOT/'source'/name,ROOT/'topics'/name)
 p=ROOT/'topics'/FILES[0]
 def intent(n):n['additionalInstructions']+='\n修理方法・補修手順・修理工法の照会は現場対応アドバイスとして既存3-9の修理検索へ渡す。通常の規定確認・改訂は従来どおり。'
 def direct_case(n):
  return [n,cg('conditionGroup_teamsNewCaseAtEntry','=Trim(Topic.初回入力) = "新しい案件"',[setv('setVariable_teamsEntryFieldPurpose','Topic.目的分野','="現場対応アドバイス"'),setv('setVariable_teamsEntryFieldFolder','Topic.対象フォルダ','="09_緊急保安_共通"'),go('goto_teamsEntryField','64VMOA')])]
 p.write_text(edit(p,{'answer_inferPurposeFromText':intent,'setVariable_purposeDetect':direct_case}))
 p=ROOT/'topics'/FILES[1]
 def init(n):
  return [n]+case_init()+[cg('conditionGroup_teamsInitialNewCase','=Trim(Topic.今回受信文) = "新しい案件"',[question('question_teamsInitialNewCase','Topic.新規案件報告','新しい案件の場所と現在の状況を入力してください。'),setv('setVariable_teamsInitialNewCaseText','Topic.初回入力','=Topic.新規案件報告'),setv('setVariable_teamsInitialNewCaseIncoming','Topic.今回受信文','=Topic.新規案件報告'),setv('setVariable_teamsInitialNewCaseGlobal','Global.緊急保安初回入力','=Topic.初回入力')])]
 def resync_scope(n):
  sync=[setv('setVariable_teamsResyncCaseKey','Topic.案件比較キー','=Global.TeamsCaseKey'),setv('setVariable_teamsResyncInitial','Topic.初回入力','=Global.緊急保安初回入力'),setv('setVariable_teamsResyncHistory','Topic.追加情報履歴','=Global.緊急保安追加情報履歴'),setv('setVariable_teamsResyncExplicit','Topic.明示案件指定','="なし"')]
  return [cg('conditionGroup_teamsResyncCase','=And(Not(IsBlank(Global.TeamsCaseKey)), Global.TeamsCaseOwner = System.User.Id, Topic.案件比較キー <> Global.TeamsCaseKey)',sync),n]
 def early_repair(n):n['conditions'][0]['condition']='='+repair_requested('Topic.今回受信文')
 def save(n):return render_steps()+[n]+after_save()+[cg('conditionGroup_teamsImageOneShot','=Topic.判定応答方式 = "画像単発"',[setv('setVariable_teamsImageReceptionOn','Global.緊急保安画像受付中','=true'),{'kind':'SendActivity','id':'sendActivity_teamsImageAdvice','activity':'{If(Topic.投稿チャネル = "msteams", Topic.Teams現場回答, Topic.優先度判定結果)}'},{'kind':'EndDialog','id':'endDialog_teamsImageOneShot'}])]
 def field_question(n):
  n['prompt']='{If(Topic.投稿チャネル = "msteams", Topic.Teams現場回答, Topic.優先度判定結果)}\n\n同じ案件の追加報告や写真を送ってください。別案件は「新しい案件」と入力してください。'
  return [n,cg('conditionGroup_teamsNewCaseInField','=Trim(Topic.優先度追加回答) = "新しい案件"',[go('goto_teamsNewCaseInField','question_teamsNewCase')])]
 def body_send(n):n['activity']=n['activity'].replace('{Topic.優先度判定結果}','{If(Topic.投稿チャネル = "msteams", Topic.Teams現場回答, Topic.優先度判定結果)}')
 ops={'setVariable_priorityRetryCount':init,'setVariable_priorityPrompt':resync_scope,'conditionGroup_repairRequestedAtStart':early_repair,'invokeFlowAction_caseSaveFieldAdvice':save,'question_priorityUpdate':field_question,'sendActivity_priorityDone':body_send,'sendActivity_priorityGiveUp':body_send}
 # Terminal repair answers go through one shared save + question, keeping original text.
 pairs=[('sendActivity_repairProcedure','endDialog_repairProcedureDone','=Topic.修理手順結果 & Char(10) & Char(10) & "安全確保を最優先に、落ち着いて対応してください。"'),('sendActivity_repairResult','endDialog_repairDone','=Topic.修理指示結果 & Char(10) & Char(10) & "お疲れさまでした。安全確保を最優先に、落ち着いて対応してください。"'),('sendActivity_repairBestEffort','endDialog_repairBestEffort','="現時点で考えられる修理方法をお伝えします（十分に絞り込めていない可能性があります）。安全確保を最優先に対応してください。" & Char(10) & Char(10) & Topic.修理指示結果')]
 raw_nodes={n['id']:n for n in nodes(yaml.safe_load(p.read_text()))if 'id'in n and'kind'in n}
 import re
 for ident,node in raw_nodes.items():
  if node['kind']=='ConditionGroup'and any('"修理の方法"'in c['condition']for c in node['conditions'])and ident not in ops:
   def expand_repair(n):
    for c in n['conditions']:
     match=re.search(r'"修理の方法" in (Topic\.[^, )]+)',c['condition'])
     if match:c['condition']='='+repair_requested(match[1])
   ops[ident]=expand_repair
 for send,end in [('sendActivity_repairProcedureNotFound','endDialog_repairProcedureNotFound'),('sendActivity_repairNoCandidate','endDialog_repairNoCandidate'),('sendActivity_repairZeroLimit','endDialog_repairZeroLimit'),('sendActivity_repairFailed','endDialog_repairFailed')]:
  text=raw_nodes[send]['activity'];pieces=re.split(r'(\{Topic\.[^}]+\})',text)
  expr='='+' & '.join(piece[1:-1]if piece.startswith('{Topic.')else q(piece)for piece in pieces if piece)
  pairs.append((send,end,expr))
 for send,end,expr in pairs:
  ops[send]=lambda n,expr=expr:setv(n['id'],'Topic.修理最終回答',expr+' & Char(10) & Char(10) & "同じ案件の状況更新・写真は、そのまま送ってください。別案件は「新しい案件」と入力してください。"')
  ops[end]=lambda n:go(n['id'],'invokeFlowAction_teamsSaveRepair')
 def repair_question(n):
  before=[setv('setVariable_teamsRepairQuestionText','Topic.修理最終回答','=Topic.修理指示結果'),save_repair('invokeFlowAction_teamsSaveRepairQuestion')]
  guard=cg('conditionGroup_teamsFieldUpdateDuringRepairQuestion','=Or(Global.TeamsImageResume = "はい", "設置済み" in Topic.修理追加回答, "閉止" in Topic.修理追加回答, "臭気" in Topic.修理追加回答, "警報" in Topic.修理追加回答, "検知" in Topic.修理追加回答, "写真" in Topic.修理追加回答)',[setv('setVariable_teamsRepairQuestionFieldFlag','Global.TeamsImageResume','="いいえ"'),setv('setVariable_teamsRepairQuestionModeOff','Topic.修理方法モード','=false'),setv('setVariable_teamsRepairQuestionFieldHistory','Topic.追加情報履歴','=Global.緊急保安追加情報履歴 & Char(10) & "追加情報：" & Topic.修理追加回答'),go('goto_teamsFieldDuringRepairQuestion','setVariable_priorityPrompt')])
  return before+[setv('setVariable_teamsRepairMoreImageOn','Global.緊急保安画像受付中','=true'),n,setv('setVariable_teamsRepairQuestionSync','Topic.追加情報履歴','=Global.緊急保安追加情報履歴'),guard]
 ops['question_repairMoreInfo']=repair_question
 def repair_choice(n):
  return [setv('setVariable_teamsRepairQuestionActive','Global.TeamsRepairActive','="はい"'),setv('setVariable_teamsRepairChoiceImageOn','Global.緊急保安画像受付中','=true'),n,cg('conditionGroup_teamsFieldUpdateDuringRepair','=Or(Global.TeamsImageResume = "はい", "設置済み" in Topic.修理選択回答, "閉止" in Topic.修理選択回答, "臭気" in Topic.修理選択回答, "警報" in Topic.修理選択回答, "検知" in Topic.修理選択回答, "写真" in Topic.修理選択回答)',[setv('setVariable_teamsRepairChoiceFieldFlag','Global.TeamsImageResume','="いいえ"'),setv('setVariable_teamsRepairChoiceModeOff','Topic.修理方法モード','=false'),setv('setVariable_teamsRepairChoiceHistory','Topic.追加情報履歴','=Global.緊急保安追加情報履歴 & Char(10) & "追加情報：" & Topic.修理選択回答'),go('goto_teamsFieldDuringRepairChoice','setVariable_priorityPrompt')])]
 ops['question_repairChoice']=repair_choice
 ops['setVariable_repairSelectInit']=lambda n:[n,setv('setVariable_teamsRepairResetImageFlag','Global.TeamsImageResume','="いいえ"'),setv('setVariable_teamsRepairSelectionActive','Global.TeamsRepairActive','="はい"')]
 p.write_text(edit(p,ops))
 data=yaml.safe_load(p.read_text());data['inputType']['properties']['判定応答方式']={'displayName':'判定応答方式','description':'既存画像トピックの単発再判定専用。通常呼出しは省略可。','type':'String'}
 # Only add the declared optional input; retain raw existing topic text elsewhere.
 s=p.read_text();tail=s.rfind('\ninputType:');s=s[:tail]+'\n'+dump({'inputType':data['inputType'],'outputType':data.get('outputType',{})});p.write_text(s)
 shared=[{'kind':'EndDialog','id':'endDialog_teamsExistingPathDone'},save_repair('invokeFlowAction_teamsSaveRepair')]+repair_return_actions()
 # New-case command explicitly discards the old case facts and comparison cache.
 shared += [question('question_teamsNewCase','Topic.新規案件報告','新しい案件として扱います。場所と現在の状況を入力してください。'),setv('setVariable_teamsNewCaseKey','Topic.案件比較キー','=Text(GUID())'),setv('setVariable_teamsNewGlobalKey','Global.TeamsCaseKey','=Topic.案件比較キー'),setv('setVariable_teamsNewInitial','Topic.初回入力','=Topic.新規案件報告'),setv('setVariable_teamsNewHistory','Topic.追加情報履歴','=""'),setv('setVariable_teamsNewGlobalInitial','Global.緊急保安初回入力','=Topic.初回入力'),setv('setVariable_teamsNewGlobalHistory','Global.緊急保安追加情報履歴','=""'),setv('setVariable_teamsNewSnapshot','Global.TeamsLastFieldSnapshot','=""'),setv('setVariable_teamsNewSavedId','Global.TeamsLastCaseId','=""'),setv('setVariable_teamsNewSequence','Global.TeamsFieldReportCount','=0'),setv('setVariable_teamsNewExplicit','Topic.明示案件指定','="なし"'),setv('setVariable_teamsNewFieldMode','Topic.修理方法モード','=false'),go('goto_teamsNewCaseAdvice','setVariable_priorityPrompt')]
 append_actions(p,shared)
 instructions=(ROOT/'source/エージェント指示_before.txt').read_text()+'\n## Teamsと案件の保持\n同じ既存エージェントをTeamsの個人チャットで利用する。現場担当者にPower Appsを開かせない。現場の表示はトピックのTeams用文章をそのまま返す。保存用の機械マーカーや変数名、JSONを表示しない。修理回答後の現場更新・写真も既存3-9と4-9へ渡す。別案件の情報は引き継がず「新しい案件」を使う。保存の完了が確認できない時に保存成功と補足しない。\n'
 (ROOT/'topics/エージェント指示_Teams追記.txt').write_text(instructions)
 print('Built entry + field topic patches; image patch follows in build_images.py')
if __name__=='__main__':build()
