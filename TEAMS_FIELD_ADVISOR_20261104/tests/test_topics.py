import copy,hashlib,json,tempfile,unittest,sys
from pathlib import Path
import yaml
from fixtures import ROOT,config
from yaml_edit import nodes
from build_topics import FILES,FIELD_DIALOG
from bind_adapter import bind_topics
from patch_export import patch_export

def index(path):return {n['id']:n for n in nodes(yaml.safe_load(path.read_text()))if'id'in n and'kind'in n}
class TopicCompatibility(unittest.TestCase):
 def setUp(self):self.old=[index(ROOT/'source'/n)for n in FILES];self.new=[index(ROOT/'topics'/n)for n in FILES]
 def test_yaml_ids_and_gotos(self):
  for name in FILES:
   data=yaml.safe_load((ROOT/'topics'/name).read_text());ids=[n['id']for n in nodes(data)if'id'in n];self.assertEqual(len(ids),len(set(ids)),name)
   self.assertTrue(all(n['actionId']in ids for n in nodes(data)if n.get('kind')=='GotoAction'),name)
  for old,new in zip(self.old,self.new):self.assertTrue(set(old)<=set(new))
 def test_source_matches_pinned_audit(self):
  audit=json.loads((ROOT/'validation/source_audit.json').read_text())
  for name,digest in audit['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'source'/name).read_bytes()).hexdigest(),digest)
 def test_legacy_renderer_and_save_contract_unchanged(self):
  self.assertEqual(self.old[1]['setVariable_itemRender'],self.new[1]['setVariable_itemRender'])
  self.assertEqual(self.old[1]['invokeFlowAction_caseSaveFieldAdvice'],self.new[1]['invokeFlowAction_caseSaveFieldAdvice'])
 def test_manual_knowledge_actions_unchanged(self):
  for old,new in zip(self.old,self.new):
   for ident,n in old.items():
    if ident=='answer_inferPurposeFromText':
     self.assertTrue(new[ident]['additionalInstructions'].startswith(n['additionalInstructions']));continue
    if n['kind']in ['SearchAndSummarizeContent','SearchKnowledgeSources','AnswerQuestionWithAI','AnswerQuestionWithAIAction','AnswerQuestionWithAI']or n['kind'].startswith('Search'):
     self.assertEqual(n,new[ident],ident)
  for ident,n in self.old[0].items():
   if n['kind']in ['InvokeFlowAction','BeginDialog']:self.assertEqual(n,self.new[0][ident],ident)
 def test_image_model_and_feature_definitions_unchanged(self):
  old=self.old[2]['invokeAIBuilderModelAction_imageFacts'];new=self.new[2]['invokeAIBuilderModelAction_imageFacts']
  self.assertEqual(old['aIModelId'],new['aIModelId']);self.assertEqual(old['input']['binding']['ContextText'],new['input']['binding']['ContextText'])
  for ident,n in self.old[2].items():
   if n['kind']=='SetVariable'and '特徴'in n.get('variable',''):self.assertEqual(n,self.new[2][ident])
 def test_image_invokes_existing_agent_and_terminates_before_question(self):
  n=self.new[2]['beginDialog_teamsPhotoSingleAdvice'];self.assertEqual(n['dialog'],FIELD_DIALOG);self.assertEqual(n['input']['binding']['判定応答方式'],'="画像単発"')
  branch=self.new[1]['conditionGroup_teamsImageOneShot']['conditions'][0]['actions'];self.assertEqual(branch[-1]['kind'],'EndDialog');self.assertFalse(any(n['kind']=='Question'for n in branch))
  self.assertEqual(self.new[2]['setVariable_teamsPhotoLimit']['value'],'=Min(CountRows(System.Activity.Attachments), 5)')
 def test_repair_saved_and_displayed_same_variable(self):
  n=self.new[1]['invokeFlowAction_teamsSaveRepair'];self.assertEqual(n['input']['binding']['text_2'],'=Topic.修理最終回答');self.assertEqual(self.new[1]['question_teamsRepairContinue']['prompt'],'{Topic.修理最終回答}')
  for suffix in ['Choice','Question']:self.assertIn('goto_teamsFieldDuringRepair'+suffix,self.new[1])
 def test_new_case_clears_facts_and_comparison(self):
  for ident in ['setVariable_teamsNewGlobalHistory','setVariable_teamsNewSnapshot','setVariable_teamsNewSavedId']:self.assertEqual(self.new[1][ident]['value'],'=""')
  self.assertEqual(self.new[1]['setVariable_teamsNewSequence']['value'],'=0')
 def test_binding_only_in_separate_output(self):
  c,fields=config()
  with tempfile.TemporaryDirectory()as tmp:
   out=bind_topics(c,fields,Path(tmp)/'bound');bound=index(out/FILES[1]);n=bound['invokeFlowAction_caseSaveFieldAdvice'];self.assertEqual(n['flowId'],c['flow_id']);self.assertIn('operation',n['input']['binding']);self.assertEqual(n['input']['binding']['legacy_text'],'=Topic.優先度判定結果')
   self.assertEqual(bound['setVariable_itemRender'],self.old[1]['setVariable_itemRender'])
   for name in FILES:yaml.safe_load((out/name).read_text())
 def test_patch_solution_keeps_identity_and_metadata(self):
  c,fields=config();from flow_definition import generate
  with tempfile.TemporaryDirectory()as tmp:
   root=Path(tmp)/'input';(root/'Workflows').mkdir(parents=True);p=root/'Workflows'/('Real-'+c['flow_id']+'.json')
   original={'id':'EXISTING_ID','properties':{'displayName':'EXISTING_NAME','definition':{'triggers':{'manual':{'type':'Request','kind':'Skills'}}},'connectionReferences':{}}};p.write_text(json.dumps(original));(root/'metadata.xml').write_text('keep byte for byte')
   result=patch_export(root,p,generate(c,fields),c['flow_id'],Path(tmp)/'output');new=json.loads(result.read_text());self.assertEqual(new['id'],original['id']);self.assertEqual(new['properties']['displayName'],original['properties']['displayName']);self.assertEqual((result.parents[1]/'metadata.xml').read_text(),'keep byte for byte');self.assertEqual(json.loads(p.read_text()),original)
if __name__=='__main__':unittest.main()
