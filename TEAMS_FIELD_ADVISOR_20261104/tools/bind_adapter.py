"""Bind verified save/load/render agent flow; refuse missing tenant metadata."""
from pathlib import Path
import argparse,json,shutil
from yaml_edit import edit,setv,cg
from build_topics import ROOT,FILES,teams_expr,lit
from flow_definition import validate_config

def bind_topics(c,fields,out):
 validate_config(c,fields);out=Path(out);out.mkdir(parents=True,exist_ok=True)
 for name in FILES:shutil.copyfile(ROOT/'topics'/name,out/name)
 p=out/FILES[1]
 def request(ident,record_type,body,snapshot,operation='save'):
  bindings={'operation':lit(operation),'case_id':'=Topic.案件比較キー','owner_key':'=Topic.案件所有者','event_key':'=Topic.投稿チャネル & "|" & System.Conversation.Id & "|" & System.User.Id & "|" & System.Activity.Id & "|'+record_type+'"','record_type':lit(record_type),'legacy_text':'='+body,'current_snapshot':'='+snapshot,'facts_history':'=Topic.初回入力 & Char(10) & Topic.追加情報履歴','source_channel':'=Topic.投稿チャネル'}
  if operation=='save':bindings['operation']='=If(Or(IsBlank(System.User.Id), IsBlank(System.Conversation.Id), IsBlank(System.Activity.Id)), "invalid", "save")'
  outputs={'status':'Topic.案件読込状態'if operation=='load'else 'Topic.保存応答状態','case_id':'Topic.案件ID','item_id':'Topic.保存項目ID','teams_text':'Topic.保存応答Teams文','previous_status':'Topic.保存前比較状態','previous_snapshot':'Topic.保存前スナップショット','case_facts':'Topic.読込案件事実','error_code':'Topic.保存エラーコード'}
  return {'kind':'InvokeFlowAction','id':ident,'input':{'binding':bindings},'output':{'binding':outputs},'flowId':c['flow_id']}
 def initialize(n):
  return [n]+[setv('setVariable_adapterInit'+suffix,'Topic.'+var,'=""')for suffix,var in [('State','保存応答状態'),('Item','保存項目ID'),('Text','保存応答Teams文'),('PreviousState','保存前比較状態'),('Previous','保存前スナップショット'),('Facts','読込案件事実'),('Error','保存エラーコード'),('Load','案件読込状態'),('Loaded','案件文脈読込済み')]]
 def load_before(n):
  load=request('invokeFlowAction_adapterLoadCase'+('Repair'if n['id']=='setVariable_repairSelectInit'else'Field'),'field_advice','""','""','load')
  suffix='Repair'if n['id']=='setVariable_repairSelectInit'else'Field'
  actions=[load,cg('conditionGroup_adapterLoadFailed'+suffix,'=Topic.案件読込状態 <> "loaded"',[setv('setVariable_adapterClearBadKey'+suffix,'Global.TeamsCaseKey','=""'),{'kind':'SendActivity','id':'sendActivity_adapterLoadFailed'+suffix,'activity':'指定された案件を確認できませんでした。案件IDと権限を確認して再送するか、「新しい案件」と入力してください。別案件の情報を使って続行はしていません。'},{'kind':'EndDialog','id':'endDialog_adapterLoadFailed'+suffix}]),setv('setVariable_adapterLoadFacts'+suffix,'Topic.追加情報履歴','=Topic.読込案件事実 & Char(10) & Topic.追加情報履歴'),setv('setVariable_adapterLoadHistory'+suffix,'Global.緊急保安追加情報履歴','=Topic.追加情報履歴'),setv('setVariable_adapterLoaded'+suffix,'Topic.案件文脈読込済み','="はい"')]
  return [cg('conditionGroup_adapterLoadCase'+suffix,'=And(Topic.明示案件指定 = "あり", Topic.案件継続 <> "はい", Topic.案件文脈読込済み <> "はい")',actions),n]
 def pending(kind,body):
  return [setv('setVariable_adapterPending'+kind,'Global.TeamsPendingReply','='+body),setv('setVariable_adapterPendingOwner'+kind,'Global.TeamsPendingOwner','=System.User.Id'),setv('setVariable_adapterPendingEvent'+kind,'Global.TeamsPendingActivityId','=System.Activity.Id')]
 def field_save(n):
  before=[setv('setVariable_adapterFallbackCompare','Topic.前回比較状態','=If(Coalesce(Global.TeamsFieldReportCount, 0) = 0, "first", "unavailable")'),setv('setVariable_adapterFallbackChanges','Topic.優先度変更点','="前回比較は現在できません。保存先の前回情報をまだ確認できていません。"'),setv('setVariable_adapterFallbackRender','Topic.Teams現場回答',teams_expr())]+pending('Field','If(Topic.投稿チャネル = "msteams", Topic.Teams現場回答, Topic.優先度判定結果)')
  return before+[request(n['id'],'field_advice','Topic.優先度判定結果','Topic.今回現場スナップショット')]
 def confirmed(n):
  good=[setv('setVariable_adapterUseSavedTeams','Topic.Teams現場回答','=Topic.保存応答Teams文'),setv('setVariable_adapterCanonicalCase','Topic.案件比較キー','=Topic.案件ID'),setv('setVariable_adapterCanonicalGlobal','Global.TeamsCaseKey','=Topic.案件比較キー'),setv('setVariable_adapterSaveStatus','Topic.保存状態','=Topic.保存応答状態')]
  bad=[setv('setVariable_adapterFailedCompare','Topic.前回比較状態','=If(Coalesce(Global.TeamsFieldReportCount, 0) = 0, "first", "unavailable")'),setv('setVariable_adapterFailedChanges','Topic.優先度変更点','="前回比較は現在できません。保存先の情報取得・記録処理が完了していません。"'),setv('setVariable_adapterFailedRender','Topic.Teams現場回答',teams_expr()+' & Char(10) & Char(10) & "記録を保存できていません。再送前に記録状態を確認してください。"'),setv('setVariable_adapterFailedStatus','Topic.保存状態','="保存未完了"')]
  return [cg('conditionGroup_adapterSaveStatus','=And(Or(Topic.保存応答状態 = "saved", Topic.保存応答状態 = "duplicate"), Not(IsBlank(Topic.保存応答Teams文)))',good,bad),setv('setVariable_adapterClearPending','Global.TeamsPendingReply','=""')]
 def repair_save(n):
  suffix='Question'if n['id'].endswith('Question')else'Final'
  good=[setv('setVariable_adapterRepairText'+suffix,'Topic.修理最終回答','=Topic.保存応答Teams文')]
  bad=[setv('setVariable_adapterRepairFailure'+suffix,'Topic.修理最終回答','=Topic.修理最終回答 & Char(10) & Char(10) & "記録を保存できていません。再送前に記録状態を確認してください。"')]
  return pending('Repair'+suffix,'Topic.修理最終回答')+[request(n['id'],'repair_guidance','Topic.修理最終回答','""'),cg('conditionGroup_adapterRepairSave'+suffix,'=And(Or(Topic.保存応答状態 = "saved", Topic.保存応答状態 = "duplicate"), Not(IsBlank(Topic.保存応答Teams文)))',good,bad),setv('setVariable_adapterClearRepairPending'+suffix,'Global.TeamsPendingReply','=""')]
 ops={'setVariable_teamsInitSaveStatus':initialize,'setVariable_priorityPrompt':load_before,'setVariable_repairSelectInit':load_before,'invokeFlowAction_caseSaveFieldAdvice':field_save,'setVariable_teamsSaveUnknown':confirmed,'invokeFlowAction_teamsSaveRepair':repair_save,'invokeFlowAction_teamsSaveRepairQuestion':repair_save,'question_repairMoreInfo':lambda n:n.update(prompt='{Topic.修理最終回答}')}
 p.write_text(edit(p,ops))
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--config',required=True,type=Path);a.add_argument('--fields',required=True,type=Path);a.add_argument('--output-dir',required=True,type=Path);x=a.parse_args();fields=json.loads(x.fields.read_text());fields=fields.get('value',fields)if isinstance(fields,dict)else fields
 if x.output_dir.resolve()in [(ROOT/'topics').resolve(),(ROOT/'source').resolve()]:raise ValueError('Use a separate deployment output directory')
 bind_topics(json.loads(x.config.read_text()),fields,x.output_dir);print('Generated bound topic copies. Tenant connections/import/execution remain unverified.')
if __name__=='__main__':main()
