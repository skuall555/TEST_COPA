"""Regression guard for the concept merge; does not simulate model judgement."""
import subprocess,unittest,yaml
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
from itemized_build import validator
BASE='ae67e129b5b2c8469d5f70f58c3c719393ef535f'
def previous(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def index(text):return {n['id']:n for n in nodes(yaml.safe_load(text))if 'id'in n and 'kind'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
class FieldConcepts(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=index(previous(FILES[1]));cls.new=index((R/FILES[1]).read_text())
 def test_entry_image_and_global_instruction_are_byte_identical(self):
  for name in [FILES[0],FILES[2],FILES[3]]:self.assertEqual(previous(name),(R/name).read_text())
 def test_existing_business_flow_preserved(self):
  from speed_scope import strip_formatting,retired
  self.assertTrue(all(retired(k)for k in set(self.old)-set(self.new)))
  self.assertEqual(strip_formatting(yaml.safe_load(previous(FILES[1]))),strip_formatting(yaml.safe_load((R/FILES[1]).read_text())))
 def test_pressure_measure_and_no_new_variables(self):
  expected={n['id']:n for n in validator()if 'P23'in n['id']}
  self.assertTrue(expected)
  for k,n in expected.items():self.assertEqual(n,self.new[k])
  self.assertEqual({n.get('variable')for n in self.old.values()},{n.get('variable')for n in self.new.values()})
 def test_concepts_reach_guide_and_ai_input_before_internal_contract(self):
  rules=(R/SOURCE).read_text().rstrip()
  guide=self.new['setVariable_priorityGuideFixed']['value'][2:-1].replace('""','"')
  prompt=self.new['setVariable_priorityPrompt']['value'].replace('""','"')
  self.assertIn(rules,guide);self.assertNotIn(rules,prompt)
  self.assertLess(prompt.index('Topic.優先度ガイド取得結果'),prompt.index('# 今回の内部出力契約'))
  self.assertIn('Topic.優先度判定プロンプト',self.new['answer_priority']['userInput'])
  self.assertIn('Topic.優先度ガイド取得結果',prompt)
if __name__=='__main__':unittest.main()
