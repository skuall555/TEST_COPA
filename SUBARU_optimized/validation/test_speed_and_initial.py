"""Scope and resource-budget regressions; actual model latency is not tested."""
import subprocess,unittest,yaml
from restart_build import R,FILES
from restart_support import nodes
from speed_scope import strip_formatting,retired
from itemized_build import validator
BASE='67165f85a61d0ff927e43b0715d701b3c38a4817'
def old(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
class SpeedAndInitial(unittest.TestCase):
 def test_business_flow_and_variables_preserved_only_generated_steps_retired(self):
  a=yaml.safe_load(old(FILES[1]));b=yaml.safe_load((R/FILES[1]).read_text())
  ix=lambda doc:{n['id']:n for n in nodes(doc)if'id'in n and'kind'in n}
  before,after=ix(a),ix(b)
  self.assertTrue(all(retired(k)for k in set(before)-set(after)))
  self.assertEqual(strip_formatting(a),strip_formatting(b))
  self.assertEqual({n.get('variable')for n in before.values()},{n.get('variable')for n in after.values()})
 def test_formatter_step_budget_and_prompt_duplication(self):
  ns={};exec(subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/validation/itemized_build.py']).decode(),ns)
  self.assertLessEqual(len(validator()),len(ns['validator']())//2)
  ix={n['id']:n for n in nodes(yaml.safe_load((R/FILES[1]).read_text()))if'id'in n and'kind'in n}
  self.assertEqual(ix['setVariable_priorityGuideFixed']['value'].count('# 現場調査・遮断・供給支障の追加概念'),1)
  self.assertNotIn('# 現場調査・遮断・供給支障の追加概念',ix['setVariable_priorityPrompt']['value'])
  self.assertEqual(ix['setVariable_priorityPrompt']['value'].count('Topic.優先度ガイド取得結果'),1)
if __name__=='__main__':unittest.main()
