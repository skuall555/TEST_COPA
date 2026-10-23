"""Offline contract tests; does not execute Power Fx or Copilot Studio."""
import unittest,yaml
from validate import R,PAIRS,flat,dependencies,dataflow
class Contracts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=[yaml.safe_load((R/'originals'/a).read_text()) for a,b in PAIRS]
  cls.new=[yaml.safe_load((R/b).read_text()) for a,b in PAIRS]
  cls.a=[flat(d) for d in cls.old];cls.b=[flat(d) for d in cls.new]
 def test_all_existing_action_ids_preserved(self):
  for a,b in zip(self.a,self.b):self.assertLessEqual(set(a),set(b))
 def test_dependencies_preserved(self):
  for a,b in zip(self.a,self.b):self.assertEqual(dependencies(a),{k:v for k,v in dependencies(b).items()if k in a})
 def test_questions_and_interruptions_preserved(self):
  for a,b in zip(self.a,self.b):
   for k,n in a.items():
    if n['kind']=='Question':
     if k=='question_purposeMissing':
      self.assertEqual(n['variable'],b[k]['variable']);self.assertEqual(n['entity'],b[k]['entity']);self.assertEqual(n['interruptionPolicy'],b[k]['interruptionPolicy'])
     else:self.assertEqual(n,b[k])
 def test_no_removed_sends(self):
  for a,b in zip(self.a,self.b):self.assertLessEqual({k for k,n in a.items()if n['kind']=='SendActivity'},set(b))
 def test_priority_guide_has_authorized_current_risk_override(self):
  old=self.a[1]['setVariable_priorityGuideFixed']['value'];new=self.b[1]['setVariable_priorityGuideFixed']['value']
  # Risk thresholds remain verbatim; output formatting and the unknown-status rule are intentionally revised.
  self.assertEqual(new.split('# 判定手順')[0],old.split('# 判定手順')[0])
  self.assertIn('現在の危険と改善を踏まえる優先規則',new)
  self.assertIn('事故が起きるまで待たず',new)
  self.assertIn('止漏だけ、単一地点の改善だけ',new)
  self.assertIn('endDialog_priorityRetryExhausted',self.b[1])
  self.assertEqual(self.b[1]['endDialog_priorityRetryExhausted']['kind'],'EndDialog')
 def test_rankers_unchanged(self):
  for suffix in ['Fit','Directness','Certainty','Consensus']:
   k='answer_manualCheckRank'+suffix;self.assertEqual(self.a[0][k],self.b[0][k])
 def test_image_history_return_preserved(self):
  for k in ['setVariable_appendImageResultToGlobalHistory','setVariable_globalDone','setVariable_globalCheck','endDialog_afterRestartEmergency']:
   self.assertEqual(self.a[2][k],self.b[2][k])
  self.assertNotIn('startBehavior',self.new[2]);self.assertFalse(any(n['kind']=='BeginDialog' for n in self.b[2].values()))
 def test_image_trigger_unchanged(self):
  for k in ['kind','id','condition','priority','type']:self.assertEqual(self.old[2]['beginDialog'][k],self.new[2]['beginDialog'][k])
 def test_coverage_gates_are_conservative(self):
  c=self.b[0]['conditionGroup_checkAdditionalSearchNeeded']['conditions'][0]
  self.assertIn('文書内容確認',c['condition']);self.assertIn('十分',c['condition'])
  self.assertEqual(sum(n['kind']=='SearchAndSummarizeContent' for n in c['actions']),3)
  self.assertIn('例外の有無が不明なら不足',self.b[0]['answer_manualCheckDirectCoverage']['additionalInstructions'])
 def test_final_guard_receives_source(self):self.assertIn('Topic.確認本文検索テキスト',self.b[0]['answer_manualCheckAnswerAudit']['userInput'])
 def test_revise_short_text_not_discarded(self):self.assertNotIn('< 200',self.b[0]['setVariable_manualReviseExpandedText']['value'])
 def test_no_continuation_copies_original(self):
  n=self.b[0]['setVariable_reviseCopyWithoutMerge'];self.assertEqual(n['value'],'=Topic.改訂見出し全文')
 def test_revise_all_row_validation(self):
  for prefix,ident in [('format','conditionGroup_manualReviseFormatReady'),('repair','conditionGroup_manualReviseRepairFormatReady')]:
   stages=[n for k,n in self.b[0].items() if k.startswith('setVariable_'+prefix+'RowCheck')]
   self.assertEqual(len(stages),19)
   checks=' '.join(n['value'] for n in stages)
   for f in ['文書名：','ページ：','項目・見出し：','変更前：','変更後：','変更理由：','信頼度：']:self.assertIn(f,checks)
   self.assertNotIn('Filter(',self.b[0][ident]['conditions'][0]['condition'])
 def test_row_checks_have_shallow_expressions(self):
  import re
  for k,n in self.b[0].items():
   if k.startswith(('setVariable_format','setVariable_repairRow','setVariable_repairEnvelope','setVariable_repairNoHit')):
    expr=re.sub(r'"(?:[^"]|"")*"','',n.get('value',''))
    depth=peak=0
    for c in expr:
     if c=='(':depth+=1;peak=max(peak,depth)
     elif c==')':depth-=1
    self.assertLessEqual(peak,8,k)
    self.assertNotIn('&&',expr)
 def test_no_new_variable_candidates(self):
  for a,b in zip(self.old,self.new):
   old,_=dataflow(a);new,_=dataflow(b);prior={(n['id'],v)for n in old for v in n['variables']}
   self.assertFalse({(n['id'],v)for n in new for v in n['variables']}-prior)
 def test_invalid_number_does_not_search_again(self):self.assertEqual(self.b[1]['goto_repairChoiceAgain']['actionId'],'question_repairChoice')
 def test_guide_failure_does_not_generate_completed_measures(self):
  n=self.b[2]['setVariable_photoGuideUnavailableResult'];self.assertIn('[措置済み]',n['value']);self.assertIn('・なし',n['value'])
  self.assertEqual(self.b[2]['goto_photoGuideUnavailableSections']['actionId'],'setVariable_sectionExtra')
 def test_negative_pass_substring_rejected(self):
  for i,k in [(0,'conditionGroup_manualCheckVerified'),(1,'conditionGroup_repairVerified')]:self.assertIn('Not("不合格" in ',self.b[i][k]['conditions'][0]['condition'])
 def test_purpose_number_mapping_executes_scalar_formulas(self):
  from powerfx_subset import evaluate
  b=self.b[0]
  for raw,want in [('1','現場対応アドバイス'),('[2]','マニュアル確認'),(' ［３］ ','マニュアル改訂'),('9',''),('0',''),('1,2',''),('写真です','')]:
   normalized=evaluate(b['setVariable_purposeNumber']['value'],{'目的回答':raw})
   got=evaluate(b['setVariable_purposeFromNumber']['value'],{'目的選択番号':normalized})
   self.assertEqual(got,want)
  self.assertEqual(b['goto_numberFieldSpecialist']['actionId'],'64VMOA')
  self.assertIn('ガス漏れ対応中',b['setVariable_numberPurposeMeaning']['value'])
 def test_unclear_purpose_has_natural_inference_then_number_question(self):
  b=self.b[0];self.assertEqual(b['answer_purposeInfer']['autoSend'],False)
  self.assertIn('不明',b['answer_purposeInfer']['additionalInstructions'])
  prompt=b['question_purposeMissing']['prompt']
  for line in ['番号を入力してください。','[1]ガス漏れ対応中','[2]社内基準、マニュアルを確認したい','[3]社内基準、マニュアルを変更したい']:self.assertIn(line,prompt)
 def test_natural_manual_requests_are_not_forced_to_field_by_alarm_keyword(self):
  from powerfx_subset import evaluate
  expr=self.b[0]['conditionGroup_inferPurposeIfMissing']['conditions'][0]['condition']
  for text,want in [('警報器が鳴る場合の社内基準を確認したい',True),('ガス漏れ時の規定に項目を追記したい',True),('ES工法の口径は',True),('現場アドバイス ガスが噴き出している',False),('マニュアル確認 ES工法',False)]:
   self.assertEqual(evaluate(expr,{'目的分野':'現場対応アドバイス','初回入力':text}),want)
 def test_field_returns_to_owned_question(self):
  import json
  graph=json.loads((R/'validation/1-マニュアル関連入口_optimized.yaml.graph.json').read_text())
  self.assertEqual(graph['64VMOA'],['conditionGroup_fieldReturnPurposeSwitch'])
  self.assertIn('question_fieldContinue',graph['conditionGroup_fieldReturnPurposeSwitch'])
  self.assertEqual(self.b[0]['goto_fieldContinueSpecialist']['actionId'],'64VMOA')
  self.assertEqual(self.b[0]['setVariable_fieldContinueHistory']['value'],'=Global.緊急保安追加情報履歴')
  self.assertIn('現場入力（時系列）',self.b[1]['setVariable_fieldTurnHistory']['value'])
  self.assertEqual(self.b[0]['goto_fieldSwitchPurpose']['actionId'],'setVariable_purposeDetect')
  from powerfx_subset import evaluate
  condition=self.b[0]['conditionGroup_fieldContinueSwitch']['conditions'][0]['condition']
  for intent,want in [('現場対応アドバイス',False),('マニュアル確認',True),('マニュアル改訂',True),('不明',False)]:self.assertEqual(evaluate(condition,{'現場継続目的':intent}),want)
  self.assertEqual(self.b[0]['goto_fieldUnknownNumberMenu']['actionId'],'conditionGroup_purposeMissing')
 def test_field_exit_preserves_parent_and_history(self):
  for k,n in self.b[1].items():
   if n['kind']=='EndDialog':
    self.assertNotIn('clearTopicQueue',n)
    self.assertEqual(self.b[1][k+'_historyToGlobal']['value'],'=Topic.追加情報履歴')
 def test_appearance_import_excludes_pdf_comparison_workflow(self):
  text=self.b[2]['setVariable_prompt1']['value']+self.b[2]['setVariable_prompt2']['value']
  for x in ['PHOTOACCESS','TOTAL_ALARM_RAW','AI9','AI10','28列','正答率']:self.assertNotIn(x,text)
  for x in ['アンテナ状の筒','手に持って検査','火気使用禁止','スイッチ操作禁止','配管・外壁貫通部','単なる黒色または茶色のケースしか見えない場合は確定しない']:self.assertIn(x,text)
 def test_placement_is_not_unconditional_presence(self):
  text=self.b[2]['setVariable_prompt2']['value']
  self.assertIn('対象物の識別＋置かれた設置／監視状態＋滞留または流入箇所との位置関係の3条件',text)
  self.assertIn('対象物の識別＋実際の掲示／設置＋対象場所との位置関係',text)
  self.assertNotIn('→ 火気厳禁表示シート。',text)
if __name__=='__main__':unittest.main()
