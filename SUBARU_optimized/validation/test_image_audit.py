"""Tests actual saved audit expressions with synthetic observations; not image/model accuracy tests."""
import unittest,yaml
from validate import R,flat,walk
from powerfx_subset import evaluate
DEFAULT={
 '写真の場所区分':'室内','周辺住戸の明示':'なし','ポケット警報器本体':'確認','ポケット警報器配置':'置かれている','ポケット警報器位置関係':'確認',
 '火気厳禁表示シート本体':'確認','火気厳禁表示シート掲示':'掲示','火気厳禁表示シート位置関係':'確認','可燃性ガス検知器本体':'確認','検知器の測定動作':'確認'}
def facts(**overrides):
 d={**DEFAULT,**overrides};return '\n'.join('・'+k+'：'+v for k,v in d.items())
class ImageAudit(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=yaml.safe_load((R/'4-9-画像分析エージェント_緊急保安_optimized.yaml').read_text());cls.ix=flat(cls.doc)
  for n in walk(cls.doc):
   actions=n.get('actions')
   if isinstance(actions,list)and any(a.get('id')=='setVariable_photoEvidence_room'for a in actions):
    a=next(i for i,x in enumerate(actions)if x.get('id')=='setVariable_photoEvidence_room');b=next(i for i,x in enumerate(actions)if x.get('id')=='setVariable_globalDone');cls.audit=actions[a:b];break
 def run_audit(self,observations,done,extra='',check='',unknown=''):
  values={'画像事実':observations,'措置済み部':done,'追加情報部':extra,'要確認部':check,'判定なし部':unknown}
  def run(actions):
   for n in actions:
    if n['kind']=='SetVariable':values[n['variable'][6:]]=evaluate(n['value'],values)
    elif n['kind']=='ConditionGroup':
     branch=next((c['actions']for c in n['conditions']if evaluate(c['condition'],values)),n.get('elseActions',[]));run(branch)
    else:self.fail('Unsupported audit action '+n['kind'])
  run(self.audit);return values
 def test_two_independent_devices_can_both_be_adopted(self):
  done='・【写真有】警報器配置（MS-007）根拠：排水口脇に置かれている\n・【写真有】検知器調査（MS-011）根拠：手持ちでプローブを当てている'
  v=self.run_audit(facts(),done);self.assertEqual(v['措置済み部'],done);self.assertIn('ポケット警報器本体を確認',v['追加情報部'])
 def test_unknown_location_cannot_be_assigned_any_site(self):
  v=self.run_audit(facts(写真の場所区分='不明'),'・【写真有】表示（MS-003）\n・【写真有】調査（MS-011）');self.assertEqual(v['措置済み部'],'・なし')
 def test_alternative_ms_ids_are_rejected(self):
  for ids in ['MS-003/MS-004/MS-005','MS-011／MS-012','MS-003/004/005']:
   with self.subTest(ids=ids):self.assertEqual(self.run_audit(facts(),'・【写真有】措置（'+ids+'）')['措置済み部'],'・なし')
 def test_placed_detector_does_not_prove_investigation(self):
  v=self.run_audit(facts(検知器の測定動作='未確認'),'・【写真有】調査（MS-011）\n・【写真有】警報器配置（MS-007）');self.assertNotIn('MS-011',v['措置済み部']);self.assertIn('MS-007',v['措置済み部'])
 def test_handheld_alarm_is_not_installed(self):self.assertEqual(self.run_audit(facts(ポケット警報器配置='手持ち'),'・【写真有】警報器（MS-007）')['措置済み部'],'・なし')
 def test_candidate_device_is_not_confirmed_presence(self):
  v=self.run_audit(facts(ポケット警報器本体='候補'),'・【写真有】警報器（MS-007）');self.assertEqual(v['措置済み部'],'・なし');self.assertNotIn('本体を確認',v['追加情報部'])
 def test_unreadable_value_does_not_invalidate_visible_action(self):
  done='・【写真有】検知器調査（MS-011）根拠：手持ち検査。表示数値は不明'
  self.assertEqual(self.run_audit(facts()+'\n・数値は判読できない',done)['措置済み部'],done)
 def test_missing_or_copied_observation_fields_fail_closed(self):
  for obs in ['・配管の近くに黒い機器がある',facts(ポケット警報器本体='確認／候補／未確認')]:self.assertEqual(self.run_audit(obs,'・【写真有】警報器（MS-007）')['措置済み部'],'・なし')
 def test_conflicting_duplicate_observation_is_not_positive(self):
  obs=facts()+'\n・ポケット警報器本体：未確認';self.assertEqual(self.run_audit(obs,'・【写真有】警報器（MS-007）')['措置済み部'],'・なし')
 def test_retired_item_is_removed_from_every_section(self):
  for code in ['MS-018','MS-001']:
   v=self.run_audit(facts(),'・【写真有】ホワイトシート（'+code+'）',extra='・ホワイトシートを確認',check='・ホワイトシートを撮り直す',unknown='・MS-018 不明')
   for key in ['措置済み部','追加情報部','要確認部','判定なし部']:self.assertNotIn('ホワイトシート',v[key]);self.assertNotIn('MS-018',v[key])
   self.assertNotIn('保留しています',v['要確認部'])
 def test_neighbor_requires_current_photo_scope(self):
  done='・【写真有】調査（MS-013）'
  self.assertEqual(self.run_audit(facts(),done)['措置済み部'],'・なし');self.assertEqual(self.run_audit(facts(周辺住戸の明示='あり'),done)['措置済み部'],done)
 def test_wrong_location_id_is_removed_without_losing_valid_one(self):
  v=self.run_audit(facts(写真の場所区分='屋内共用部'),'・【写真有】室内調査（MS-011）\n・【写真有】共用部調査（MS-012）');self.assertNotIn('MS-011',v['措置済み部']);self.assertIn('MS-012',v['措置済み部'])
 def test_no_completion_does_not_create_a_retaking_request(self):
  v=self.run_audit('', '・なし');self.assertEqual(v['措置済み部'],'・なし');self.assertEqual(v['要確認部'],'')
 def test_selected_md_definition_is_included_verbatim(self):
  text=self.ix['setVariable_prompt1']['value'][2:-1].replace('""','"');reference=(R/'references/対象物認識定義_MD原文.txt').read_text().strip();self.assertIn(reference,text)
  self.assertEqual((R/'AIBuilder_第1段画像認識_ContextText全文.txt').read_text(),text+'\n')
 def test_retired_target_not_requested_by_prompts(self):
  for k in ['setVariable_prompt1','setVariable_prompt2']:
   self.assertNotIn('ホワイトシート',self.ix[k]['value']);self.assertNotIn('MS-018',self.ix[k]['value'])
  self.assertIn('MS-001〜MS-017',self.ix['search_photoGuidelineRetrieve']['userInput'])
  import re
  self.assertRegex(self.ix['search_photoGuidelineRetrieve']['additionalInstructions'],re.compile(r'^="(?:[^"]|"")*"$',re.S))
 def test_image_diagnostics_are_explicitly_requested(self):self.assertIn('画像診断',self.ix['setVariable_debugMode']['value'])
 def test_new_audit_expressions_are_shallow(self):
  import re
  for n in walk(self.audit):
   for expr in ([n.get('value','')]if n.get('kind')=='SetVariable'else[c['condition']for c in n.get('conditions',[])]):
    clean=re.sub(r'"(?:[^"]|"")*"','',expr);depth=peak=0
    for char in clean:
     if char=='(':depth+=1;peak=max(peak,depth)
     elif char==')':depth-=1
    self.assertLessEqual(peak,8,n.get('id'))
if __name__=='__main__':unittest.main()
