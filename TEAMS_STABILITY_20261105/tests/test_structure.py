import sys,unittest,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from yaml_edit import nodes
def index(d):return {n['id']:n for n in nodes(d)if'id'in n}
class Stability(unittest.TestCase):
 def test_preserve_all_old_logic_except_failure_message(self):
  for before,after in [('変更前_1.yaml','1_貼り替え用.yaml'),('変更前_3-9.yaml','3-9_貼り替え用.yaml')]:
   old=yaml.safe_load((ROOT/'source'/before).read_text());new=yaml.safe_load((ROOT/after).read_text());oi=index(old);ni=index(new)
   for ident,n in oi.items():
    self.assertIn(ident,ni)
    own=lambda x:{k:v for k,v in x.items()if k not in ['actions','elseActions','conditions']}
    if ident=='sendActivity_priorityFailed':self.assertTrue(ni[ident]['activity'].startswith(n['activity']))
    elif n.get('variable')=='Topic.優先度経路診断':self.assertEqual(ni[ident]['value'],n['value'].replace('subaru-text-20261102-v2','subaru-runtime-20261105-v1'))
    else:self.assertEqual(own(n),own(ni[ident]),ident)
   ids=[n['id']for n in nodes(new)if'id'in n];self.assertEqual(len(ids),len(set(ids)));self.assertTrue(all(n['actionId']in ni for n in nodes(new)if n.get('kind')=='GotoAction'))
   self.assertEqual(old['inputType'],new['inputType']);self.assertEqual(old['outputType'],new['outputType'])
 def test_retry_jumps_after_initialization_without_reset(self):
  d=yaml.safe_load((ROOT/'3-9_貼り替え用.yaml').read_text());idx=index(d)
  main=idx['conditionGroup_priorityGuideRetrieveSucceeded']['conditions'][0]['actions'];order={n['id']:i for i,n in enumerate(main)}
  self.assertLess(order['setVariable_priorityFormatRetryInit'],order['answer_priority']);self.assertLess(order['answer_priority'],order['setVariable_priorityGateSnapshot']);self.assertLess(order['setVariable_priorityGateSnapshot'],order['conditionGroup_runtimePriorityRetry']);self.assertLess(order['conditionGroup_runtimePriorityRetry'],order['conditionGroup_prioritySucceeded'])
  self.assertEqual(idx['goto_runtimePriorityRetry']['actionId'],'answer_priority');self.assertEqual(idx['conditionGroup_prioritySucceeded']['conditions'][0]['condition'],'=Topic.優先度表示検証 = "合格"')
 def test_same_flow_and_legacy_renderer_and_display(self):
  a=index(yaml.safe_load((ROOT/'source/変更前_3-9.yaml').read_text()));b=index(yaml.safe_load((ROOT/'3-9_貼り替え用.yaml').read_text()))
  for ident in a:
   if ident.startswith(('setVariable_teamsDisplay','setVariable_item'))or a[ident].get('kind')in ['InvokeFlowAction','AnswerQuestionWithAI']:self.assertEqual(a[ident],b[ident],ident)
 def test_manual_branches_are_not_shortcut_targets(self):
  d=index(yaml.safe_load((ROOT/'1_貼り替え用.yaml').read_text()));self.assertEqual(d['goto_runtimeDirectEmergency']['actionId'],'64VMOA');self.assertEqual(d['64VMOA']['dialog'],'cr88f_SUBARU_search.topic.9xY')
 def test_paste_files_are_complete_yaml(self):
  for prefix in ['1','3-9']:self.assertEqual((ROOT/(prefix+'_貼り替え用.txt')).read_bytes(),(ROOT/(prefix+'_貼り替え用.yaml')).read_bytes())
if __name__=='__main__':unittest.main()
