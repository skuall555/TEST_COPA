"""Regression/preservation checks; no live AI scoring or safety-effectiveness claim."""
import subprocess,unittest,yaml
from pathlib import Path
from restart_build import FILES,R
from restart_support import nodes
BASE='713b81764fab08d3abe80247b07aebb6c33d50dd'
def prior(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def index(text):return {n['id']:n for n in nodes(yaml.safe_load(text))if 'id'in n and 'kind'in n}
class Additional(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=index(prior(FILES[1]));cls.new=index((R/FILES[1]).read_text())
 def test_three_prompt_fields_only_and_no_new_actions(self):
  self.assertEqual(set(self.old),set(self.new))
  def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
  changed={k for k in self.old if own(self.old[k])!=own(self.new[k])}
  self.assertEqual(changed,{'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority'})
  # main owns all nested actions; compare its non-action properties separately.
  self.assertEqual({k:v for k,v in self.old['main'].items()if k!='actions'},{k:v for k,v in self.new['main'].items()if k!='actions'})
  for ident,key in [('setVariable_priorityGuideFixed','value'),('setVariable_priorityPrompt','value'),('answer_priority','additionalInstructions')]:
   self.assertEqual({k:v for k,v in self.old[ident].items()if k!=key},{k:v for k,v in self.new[ident].items()if k!=key})
 def test_other_deliverables_byte_identical(self):
  for name in [FILES[0],FILES[2],FILES[3]]:self.assertEqual(prior(name),(R/name).read_text())
 def test_control_graph_schema_and_variable_bindings_identical(self):
  def strip(x):
   if isinstance(x,dict):
    ignore={'value'}if x.get('id')in ('setVariable_priorityGuideFixed','setVariable_priorityPrompt')else {'additionalInstructions'}if x.get('id')=='answer_priority'else set()
    return {k:strip(v)for k,v in x.items()if k not in ignore}
   return [strip(v)for v in x]if isinstance(x,list)else x
  self.assertEqual(strip(yaml.safe_load(prior(FILES[1]))),strip(yaml.safe_load((R/FILES[1]).read_text())))
 def test_output_sections_and_non_target_safety_sections_unchanged(self):
  a=self.old['setVariable_priorityGuideFixed']['value'];b=self.new['setVariable_priorityGuideFixed']['value']
  for start,end in [('# 窓等の開放・換気','# メーターガス栓閉止'),('# 避難誘導','# 周辺住戸・建物調査'),('# マンホール蓋開放・換気','# 場所別の基本判定'),('# 最重要','# 禁止事項')]:self.assertEqual(a[a.index(start):a.index(end)],b[b.index(start):b.index(end)])
 def test_original_fire_reassessment_and_equipment_rules_preserved(self):
  a=self.old['setVariable_priorityGuideFixed']['value'];b=self.new['setVariable_priorityGuideFixed']['value']
  for start,end in [('【高：消防・警察','【改善後の再評価】'),('【改善後の再評価】','# 立入禁止・保安柵・警戒区域')]:
   expected=a[a.index(start):a.index(end)]
   actual=b[b.index(start):b.index(end)]
   if start.startswith('【高：'):actual=actual[:actual.index('【都市ガス警報器と換気困難')]
   self.assertEqual(expected,actual)
  for start,end in [('【ポケット警報器】','【ガス検知調査】')]:self.assertEqual(a[a.index(start):a.index(end)],b[b.index(start):b.index(end)])
if __name__=='__main__':unittest.main()
