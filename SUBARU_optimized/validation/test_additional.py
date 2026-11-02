"""Preservation from the last delivered 7b4724b; live AI accuracy is not tested."""
import subprocess,unittest,yaml
from restart_build import FILES,R
from restart_support import nodes
BASE='7b4724bde0cbf1895d3252574b5e6f84c7118c3d'
def prior(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def index(text):return {n['id']:n for n in nodes(yaml.safe_load(text))if 'id'in n and 'kind'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
class Additional(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.old=index(prior(FILES[1]));cls.new=index((R/FILES[1]).read_text())
 def test_only_scoped_existing_fields_changed(self):
  self.assertLessEqual(set(self.old),set(self.new))
  changed={k for k in self.old if own(self.old[k])!=own(self.new[k])}
  self.assertEqual(changed,{'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority','conditionGroup_prioritySucceeded','conditionGroup_priorityLoopNeeded','sendActivity_priorityFailed'})
 def test_entry_and_images_byte_identical(self):
  self.assertEqual(prior(FILES[0]),(R/FILES[0]).read_text())
  self.assertTrue((R/FILES[3]).read_text().startswith(prior(FILES[3])))
 def test_connector_questions_and_manual_repair_nodes_unchanged(self):
  for k,n in self.old.items():
   if n['kind']in ('InvokeFlowAction','Question','SearchAndSummarizeContent','SearchKnowledgeSources','BeginDialog')or 'repair' in k.lower()or 'investigation'in k.lower():self.assertEqual(own(n),own(self.new[k]),k)
 def test_new_variables_are_scalars_with_explicit_initializing_values(self):
  added=[n for k,n in self.new.items()if k not in self.old]
  writes={n['variable']:n['value']for n in reversed(added)if n['kind']=='SetVariable'}
  existing={n.get('variable')for n in self.old.values()}
  for variable,expression in writes.items():
   if variable not in existing and variable!='Topic.優先度表示原文':self.assertTrue(expression.startswith('="')or expression=='=0',variable)
  self.assertEqual(writes['Topic.優先度様式再試行回数'],'=0')
  local_tables={'setVariable_itemBucketHigh','setVariable_itemBucketMedium','setVariable_itemBucketLow','setVariable_itemIncomplete'}
  self.assertFalse(any(('Filter('in n.get('value','')or 'Concat('in n.get('value',''))and n['id']not in local_tables for n in added))
 def test_no_autonomous_format_retry_and_success_guard_retained(self):
  for ident in ['conditionGroup_priorityFormatRetry','goto_priorityFormatRetry','setVariable_priorityFormatRetryIncrement']:self.assertNotIn(ident,self.new)
  self.assertEqual(self.new['setVariable_priorityFormatRetryInit']['value'],'=0')
  self.assertEqual(self.new['conditionGroup_prioritySucceeded']['conditions'][0]['condition'],'=Topic.優先度表示検証 = "合格"')
 def test_other_safety_and_image_ownership_preserved(self):
  self.assertEqual(own(self.old['question_priorityUpdate']),own(self.new['question_priorityUpdate']))
  self.assertTrue(self.new['question_priorityUpdate']['interruptionPolicy']['allowInterruption'])
if __name__=='__main__':unittest.main()
