"""Preserve the deployed flow while retiring the known overbroad prompt causes."""
import subprocess,unittest,yaml
from restart_build import R,FILES
from restart_support import nodes
BASE='9b2c7f107a0a8c16150f3b8a4fbcd4fbc8c80ec6'
def previous(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
class Applicability(unittest.TestCase):
 def test_no_flow_or_node_or_variable_changes(self):
  a=yaml.safe_load(previous(FILES[1]));b=yaml.safe_load((R/FILES[1]).read_text())
  def erase_prompts(x):
   if isinstance(x,list):return [erase_prompts(v)for v in x]
   if isinstance(x,dict):return {k:erase_prompts(v)for k,v in x.items()if not((x.get('id')in ('setVariable_priorityGuideFixed','setVariable_priorityPrompt')and k=='value')or(x.get('id')=='answer_priority'and k=='additionalInstructions'))}
   return x
  self.assertEqual(erase_prompts(a),erase_prompts(b))
  for name in [FILES[0],FILES[2],FILES[3]]:self.assertEqual(previous(name),(R/name).read_text())
 def test_known_positive_odor_only_rule_and_all_high_template_are_removed(self):
  text=(R/FILES[1]).read_text()
  self.assertNotIn('臭気だけでも該当し、複数地点・警報・換気不能との併存を必須にしない',text)
  self.assertNotIn('室内臭気・実反応等では要請と避難を両方高',text)
  for code in range(1,14):self.assertNotIn(f'[[P{code:02}]]高|未実施|根拠となる対象・事実・条件',text)
 def test_old_missing_report_means_not_done_instructions_are_removed(self):
  text=(R/FILES[1]).read_text()
  for phrase in ['実施したとの情報がないものは「未実施」とする。','実施済みと確認できないものは「未実施」として扱う。','未実施（設置報告なし・要確認）']:
   self.assertNotIn(phrase,text)
if __name__=='__main__':unittest.main()
