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
    if n['kind']=='Question':self.assertEqual(n,b[k])
 def test_no_removed_sends(self):
  for a,b in zip(self.a,self.b):self.assertLessEqual({k for k,n in a.items()if n['kind']=='SendActivity'},set(b))
 def test_priority_guide_unchanged(self):self.assertEqual(self.a[1]['setVariable_priorityGuideFixed'],self.b[1]['setVariable_priorityGuideFixed'])
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
if __name__=='__main__':unittest.main()
