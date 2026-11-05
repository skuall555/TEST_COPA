import hashlib,sys,unittest,yaml
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from build import SOURCE,YAML,TEXT,index
from yaml_edit import nodes

class DisplayOnly(unittest.TestCase):
 def setUp(self):
  self.old=yaml.safe_load(SOURCE.read_text());self.new=yaml.safe_load(YAML.read_text());self.before=index(self.old);self.after=index(self.new)
 def test_source_is_uploaded_bytes(self):self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'7745bf5f7348d66974e9ddeb54febd63bbcc4e2f2f5ca9e0e8a0444bec054d4b')
 def test_all_existing_nodes_unchanged_except_three_display_templates(self):
  def mapping(d):return {n['id']:n for n in nodes(d)if'id'in n}
  before=mapping(self.old);after=mapping(self.new)
  allowed={'question_priorityUpdate','sendActivity_priorityDone','sendActivity_priorityGiveUp'}
  for ident,n in before.items():
   self.assertIn(ident,after)
   if ident in allowed:continue
   own=lambda n:{k:v for k,v in n.items()if k not in ['actions','conditions','elseActions']}
   self.assertEqual(own(n),own(after[ident]),ident)
 def test_flows_and_models_and_rules_unchanged(self):
  for ident,n in self.before.items():
   if n['kind']in ['InvokeFlowAction','AnswerQuestionWithAI','SearchAndSummarizeContent','InvokeAIBuilderModelAction']or ident in ['setVariable_itemRender','setVariable_priorityGuideFixed','setVariable_priorityPrompt']:self.assertEqual(n,self.after[ident],ident)
  self.assertEqual(self.before['invokeFlowAction_caseSaveFieldAdvice']['input']['binding']['text_2'],'=Topic.優先度判定結果')
 def test_ids_unique_references_valid_schema_unchanged(self):
  ids=[n['id']for n in nodes(self.new)if'id'in n];self.assertEqual(len(ids),len(set(ids)))
  self.assertTrue(all(n['actionId']in ids for n in nodes(self.new)if n.get('kind')=='GotoAction'))
  self.assertEqual(self.old['inputType'],self.new['inputType']);self.assertEqual(self.old['outputType'],self.new['outputType']);self.assertEqual(self.old['modelDescription'],self.new['modelDescription'])
 def test_new_actions_only_string_assignments(self):
  added=[n for ident,n in self.after.items()if ident not in self.before];self.assertEqual(len(added),35)
  self.assertTrue(all(n['kind']=='SetVariable'for n in added));self.assertTrue(all(n['variable'].startswith(('Topic.Teams','Global.Teams'))for n in added))
 def test_all_success_templates_use_conditional_display(self):
  for ident,key in [('question_priorityUpdate','prompt'),('sendActivity_priorityDone','activity'),('sendActivity_priorityGiveUp','activity')]:
   before=self.before[ident][key];after=self.after[ident][key]
   self.assertEqual(before,after.replace('{If(Topic.Teams表示チャネル = "msteams", Topic.Teams現場表示, Topic.優先度判定結果)}','{Topic.優先度判定結果}'))
 def test_text_download_identical_to_yaml(self):self.assertEqual(TEXT.read_bytes(),YAML.read_bytes())
if __name__=='__main__':unittest.main()
