import copy,json,tempfile,unittest
from pathlib import Path
from fixtures import config,request,snap,LEGACY,ROOT
from wdl_runner import Flow,Wdl
from flow_definition import generate,validate_config
class SharePointAdapter(unittest.TestCase):
 def setUp(self):self.c,self.fields=config();self.template=generate(self.c,self.fields)['properties']['definition'];self.flow=Flow(self.template,self.c)
 def test_first_field_keeps_legacy_bytes_and_teams_sections(self):
  out=self.flow.run(request());self.assertEqual(out['status'],'saved');self.assertNotIn('【①',out['teams_text']);self.assertLess(out['teams_text'].index('【②'),out['teams_text'].index('【③'));self.assertLess(out['teams_text'].index('【③'),out['teams_text'].index('【④'))
  self.assertEqual(self.flow.records[0][self.c['field_map']['legacy_text']],LEGACY)
 def test_second_field_compares_priority_not_words(self):
  self.flow.run(request());out=self.flow.run(request('e2',text=LEGACY.replace('室内臭気','報告された室内臭気')));self.assertIn('前回から優先度の変更なし',out['teams_text'])
  out=self.flow.run(request('e3',snapshot=snap({'P08':'高'})));self.assertIn('中 → 高',out['teams_text'])
 def test_state_change_and_missing_item_are_separate(self):
  self.flow.run(request(snapshot=snap(optional=True)));out=self.flow.run(request('e2',snapshot=snap(states={'P07':'対応済み'})));self.assertIn('状態 要確認 → 対応済み',out['teams_text']);self.assertIn('今回は未判定（解消とは判定しません）',out['teams_text'])
 def test_repair_text_is_exact_and_does_not_overwrite_legacy(self):
  self.flow.run(request());repair='根拠を確認した修理回答\n文書名・節は確認済みのものだけ。';out=self.flow.run(request('r1',kind='repair_guidance',text=repair,snapshot=''));self.assertEqual(out['teams_text'],repair)
  row=self.flow.records[-1];self.assertEqual(row[self.c['field_map']['repair_text']],repair);self.assertNotIn(self.c['field_map']['legacy_text'],row)
  out=self.flow.run(request('e2',snapshot=snap({'P08':'高'})));self.assertIn('中 → 高',out['teams_text'])
 def test_duplicate_uses_saved_canonical_text(self):
  first=self.flow.run(request());dup=self.flow.run(request(text='regenerated text must not replace saved answer'));self.assertEqual(dup['status'],'duplicate');self.assertEqual(dup['teams_text'],first['teams_text']);self.assertEqual(len(self.flow.records),1)
 def test_cases_and_owners_do_not_mix(self):
  self.flow.run(request());other=self.flow.run(request('e2',case='case-B',snapshot=snap({'P08':'高'})));self.assertNotIn('【①',other['teams_text'])
  loaded=self.flow.run(request('load',owner='owner-B',operation='load'));self.assertEqual(loaded['status'],'failed');self.assertEqual(loaded['case_facts'],'')
 def test_load_returns_latest_field_not_repair(self):
  self.flow.run(request());self.flow.run(request('r1',kind='repair_guidance',text='修理回答',snapshot=''));out=self.flow.run(request('load',operation='load'));self.assertEqual(out['status'],'loaded');self.assertEqual(out['case_facts'],request()['facts_history']);self.assertEqual(out['previous_snapshot'],snap())
 def test_failure_never_claims_saved(self):
  for op in ['GetItems','PostItem']:
   f=Flow(self.template,self.c,fail_operation=op);out=f.run(request());self.assertEqual(out['status'],'failed');self.assertEqual(len(f.records),0)
 def test_invalid_snapshot_or_headers_not_saved(self):
  for text,ss in [(LEGACY,'P01|高|要確認'),(LEGACY,snap()+'\nP01|高|要確認'),('wrong legacy',snap())]:
   f=Flow(self.template,self.c);out=f.run(request(text=text,snapshot=ss));self.assertEqual(out['status'],'failed');self.assertEqual(len(f.records),0)
 def test_filter_escapes_quotes(self):
  self.flow.run(request(case="case'X"));out=self.flow.run(request('e2',case="case'X",snapshot=snap({'P08':'高'})));self.assertIn('中 → 高',out['teams_text'])
 def test_missing_identity_or_unverified_schema_blocks_generation(self):
  for key in ['identity_binding_verified','powerapps_repair_filter_verified']:
   c=copy.deepcopy(self.c);c[key]=False
   with self.assertRaises(ValueError):generate(c,self.fields)
  fields=copy.deepcopy(self.fields);next(x for x in fields if x['InternalName']==self.c['field_map']['case_id'])['EnforceUniqueValues']=True
  with self.assertRaises(ValueError):generate(self.c,fields)
 def test_unfilled_real_configuration_cannot_generate_flow(self):
  with self.assertRaises(ValueError):generate(json.loads((ROOT/'contracts/deployment.example.json').read_text()),self.fields)
 def test_old_record_without_snapshot_is_not_no_change(self):
  for old in ['', 'P01|高|要確認',snap()+'\nP01|高|要確認','broken row']:
   f=Flow(self.template,self.c);f.run(request());f.records[0][self.c['field_map']['current_snapshot']]=old
   out=f.run(request('e2'));self.assertIn('前回比較は現在できません',out['teams_text']);self.assertNotIn('前回から優先度の変更なし',out['teams_text']);self.assertEqual(out['previous_status'],'unavailable')
if __name__=='__main__':unittest.main()
