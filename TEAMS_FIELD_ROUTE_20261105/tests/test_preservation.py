from pathlib import Path
import unittest,yaml,sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from yaml_edit import nodes
def idx(d):return {n['id']:n for n in nodes(d)if'id'in n}
class Preservation(unittest.TestCase):
 def setUp(self):self.old=yaml.safe_load((ROOT/'source/変更前_1.yaml').read_text());self.new=yaml.safe_load((ROOT/'1_貼り替え用.yaml').read_text())
 def test_existing_logic_and_save_contract_preserved(self):
  old=idx(self.old);new=idx(self.new)
  for ident,n in old.items():
   self.assertIn(ident,new)
   if ident=='setVariable_buildVersion':continue
   own=lambda x:{k:v for k,v in x.items()if k not in ['actions','elseActions','conditions']}
   self.assertEqual(own(n),own(new[ident]),ident)
  for ident in ['invokeFlowAction_caseSaveManualCheckEveryResult','invokeFlowAction_caseSaveManualRevision','invokeFlowAction_caseSaveManualRevisionRepair','64VMOA','answer_inferPurposeFromText']:self.assertEqual(old[ident],new[ident],ident)
 def test_field_guard_is_before_classifier(self):
  actions=self.new['beginDialog']['actions'];order={n['id']:i for i,n in enumerate(actions)}
  self.assertLess(order['setVariable_history'],order['conditionGroup_fieldBeforePurposeAI']);self.assertLess(order['setVariable_purposeRetryCount'],order['conditionGroup_fieldBeforePurposeAI']);self.assertLess(order['conditionGroup_fieldBeforePurposeAI'],order['answer_inferPurposeFromText'])
  self.assertEqual(idx(self.new)['goto_fieldBeforePurposeAI']['actionId'],'64VMOA')
 def test_ids_and_schema(self):
  ids=[n['id']for n in nodes(self.new)if'id'in n];self.assertEqual(len(ids),len(set(ids)));self.assertTrue(all(n['actionId']in ids for n in nodes(self.new)if n.get('kind')=='GotoAction'))
  for k in ['inputType','outputType','modelDescription']:self.assertEqual(self.old[k],self.new[k])
  self.assertEqual(self.old['beginDialog']['kind'],self.new['beginDialog']['kind'])
 def test_original_utterance_not_rewritten(self):self.assertEqual(idx(self.new)['setVariable_initialInput'],idx(self.old)['setVariable_initialInput']);self.assertEqual((ROOT/'1_貼り替え用.yaml').read_bytes(),(ROOT/'1_貼り替え用.txt').read_bytes())
if __name__=='__main__':unittest.main()
