import sys,unittest,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from yaml_edit import nodes
def idx(p):return {n['id']:n for n in nodes(yaml.safe_load(p.read_text()))if'id'in n}
class Display(unittest.TestCase):
 def test_only_display_fields_changed(self):
  before=idx(ROOT/'source/変更前_3-9.yaml');after=idx(ROOT/'3-9_貼り替え用.yaml');self.assertEqual(set(before),set(after))
  allowed={'question_priorityUpdate','sendActivity_priorityDone','sendActivity_priorityGiveUp','setVariable_teamsDisplayRender'}
  for ident,n in before.items():
   if ident not in allowed:self.assertEqual({k:v for k,v in n.items()if k not in ['actions','conditions','elseActions']},{k:v for k,v in after[ident].items()if k not in ['actions','conditions','elseActions']},ident)
 def test_all_reply_paths_use_readable_text(self):
  after=idx(ROOT/'3-9_貼り替え用.yaml')
  for ident,key in [('question_priorityUpdate','prompt'),('sendActivity_priorityDone','activity'),('sendActivity_priorityGiveUp','activity')]:self.assertIn('{Topic.Teams現場表示}',after[ident][key]);self.assertNotIn('{If(',after[ident][key]);self.assertNotIn('{Topic.優先度判定結果}',after[ident][key])
 def test_flow_and_apps_renderer_and_retry_are_unchanged(self):
  before=idx(ROOT/'source/変更前_3-9.yaml');after=idx(ROOT/'3-9_貼り替え用.yaml')
  for ident in ['setVariable_itemRender','invokeFlowAction_caseSaveFieldAdvice','conditionGroup_runtimePriorityRetry','answer_priority','sendActivity_priorityFailed']:self.assertEqual(before[ident],after[ident])
 def test_text_and_yaml_match(self):self.assertEqual((ROOT/'3-9_貼り替え用.txt').read_bytes(),(ROOT/'3-9_貼り替え用.yaml').read_bytes())
if __name__=='__main__':unittest.main()
