"""Guard integration, first failure diagnostics and binding without invented IDs."""
import shutil,tempfile,unittest,yaml
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from bind_text_prompts import bind

def ix(p):return {n['id']:n for n in nodes(yaml.safe_load(p.read_text()))if'id'in n and'kind'in n}
class ResponseReliability(unittest.TestCase):
 def test_success_gate_has_one_unambiguous_condition_and_diagnostics(self):
  n=ix(R/FILES[1]);self.assertEqual(n['conditionGroup_prioritySucceeded']['conditions'][0]['condition'],'=Topic.優先度表示検証 = "合格"')
  for stage in ['Gate','Wait','Failed']:
   self.assertEqual(n['setVariable_priority'+stage+'Snapshot']['variable'],'Topic.優先度経路診断')
  self.assertIn('Topic.優先度表示検証',n['answer_priority']['userInput']);self.assertIn('Topic.優先度判定結果',n['answer_priority']['userInput'])
  self.assertEqual(n['setVariable_priorityPreviousResultInit']['value'],'=""')
 def test_binding_keeps_redirect_and_retry_targets_and_copies_text(self):
  # UUIDs here are fixtures only; generated test files are removed, never deployed.
  with tempfile.TemporaryDirectory()as td:
   paths=[Path(td)/FILES[i]for i in [0,1]]
   for p in paths:shutil.copyfile(R/p.name,p)
   old=[ix(p)for p in paths]
   bind(*paths,'12345678-1234-1234-1234-123456789001','12345678-1234-1234-1234-123456789002')
   after=[ix(p)for p in paths]
   for index,node,copy,target in [(0,'answer_inferPurposeFromText','setVariable_copyPurposePromptText','Topic.目的分野'),(1,'answer_priority','setVariable_copyPriorityPromptText','Topic.優先度判定結果')]:
    self.assertEqual(after[index][node]['kind'],'InvokeAIBuilderModelAction');self.assertEqual(after[index][copy]['variable'],target)
    self.assertTrue(after[index][copy]['value'].endswith('.text'))
    self.assertEqual(after[index][node]['input']['binding']['ContextText'],old[index][node]['userInput'])
    for ident,n in old[index].items():
     if n['kind']in ('GotoAction','BeginDialog','Question','InvokeFlowAction','SearchKnowledgeSources','SearchAndSummarizeContent'):self.assertEqual(n,after[index][ident])
 def test_binding_rejects_placeholder_identifiers(self):
  with self.assertRaises(ValueError):bind(Path('not-read'),Path('not-read'),'00000000-0000-0000-0000-000000000000','00000000-0000-0000-0000-000000000000')
if __name__=='__main__':unittest.main()
