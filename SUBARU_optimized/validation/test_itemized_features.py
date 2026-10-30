"""Runtime wiring and isolated item editing; this does not evaluate image recognition."""
import shutil,subprocess,tempfile,unittest,yaml
from pathlib import Path
from restart_support import nodes
from restart_build import R,FILES
from image_features_build import apply,ITEMS
BASE='640af62021dbb4c5bc45917cf7b1f264ab40e655'
def old(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def index(s):return {n['id']:n for n in nodes(yaml.safe_load(s))if 'kind'in n and 'id'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','elseActions','conditions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
class ItemizedFeatures(unittest.TestCase):
 def test_unrelated_entry_and_global_instructions_unchanged(self):
  for name in [FILES[0],FILES[3]]:self.assertEqual(old(name),(R/name).read_text())
 def test_image_connector_trigger_and_history_preserved(self):
  a=index(old(FILES[2]));b=index((R/FILES[2]).read_text())
  self.assertLessEqual(set(a),set(b))
  self.assertEqual({k for k in a if own(a[k])!=own(b[k])},{'setVariable_prompt1','setVariable_prompt2'})
  for code,name in ITEMS:self.assertIn('Topic.特徴_'+name,b['setVariable_imageFeatureCatalog']['value'])
  self.assertIn('Topic.画像特徴カタログ',b['setVariable_prompt1']['value']);self.assertIn('Topic.画像特徴カタログ',b['setVariable_prompt2']['value'])
 def test_editing_only_pocket_feature_changes_only_its_node(self):
  with tempfile.TemporaryDirectory()as td:
   root=Path(td);shutil.copytree(R/'image_features',root/'image_features')
   p=root/FILES[2];p.write_text(old(FILES[2]));apply(p);before=index(p.read_text())
   source=root/'image_features/02_ポケット警報器.md';source.write_text(source.read_text()+'\nポケット識別の更新テスト。\n')
   p.write_text(old(FILES[2]));apply(p);after=index(p.read_text())
   self.assertEqual({k for k in before if own(before[k])!=own(after[k])},{'setVariable_imageFeature02'})
 def test_only_obsolete_layout_parser_ids_are_retired(self):
  import re
  a=index(old(FILES[1]));b=index((R/FILES[1]).read_text())
  retired=set(a)-set(b)
  self.assertTrue(retired)
  self.assertTrue(all(re.fullmatch(r'setVariable_priorityFormat(?:AssembleInit|Section[0-6]|Check[0-6]|Append[0-6])',k)for k in retired))
  for k,n in a.items():
   if n['kind']in ('Question','InvokeFlowAction','BeginDialog','SearchKnowledgeSources','SearchAndSummarizeContent'):self.assertEqual(own(n),own(b[k]),k)
 def test_retry_limit_cannot_fall_through_to_completed_phase(self):
  ix=index((R/FILES[1]).read_text());actions=ix['conditionGroup_priorityRetryLimit']['conditions'][0]['actions']
  self.assertEqual(actions[-2]['id'],'sendActivity_priorityGiveUp')
  self.assertEqual(actions[-1],{'kind':'EndDialog','id':'endDialog_priorityRetryLimit','clearTopicQueue':True})
if __name__=='__main__':unittest.main()
