"""Execute saved renderer formulas with synthetic model rows, not a model/runtime test."""
import unittest,re,yaml
from validate import R,flat,walk
from powerfx_subset import evaluate
from priority_revision import BASIC,RISKS
REPORT='''通報内容：マンションの一室で臭気を感じる。
到着時臭気なし。
調査中に別の部屋から都市ガス警報器が鳴動した。
分岐バルブは図面ではあるが見つからない。
消防・警察は要請していない。
警報器鳴動宅のドアポストからLEL1％検知。
警報器が鳴りやまない。
警報器が鳴っている部屋のメーターガス栓を閉めたが濃度変わらず、警報も鳴りやまない。'''
CLOSED='警報器が鳴っている部屋のメーターガス栓を閉めたが濃度変わらず、警報も鳴りやまない'
def row(name,scope='現場',priority='高',status='要確認',effect='対象外',source='なし',proof='なし',reason='現場条件と固定ガイド',next_action='なし',question='なし'):
 return '|'.join([name,scope,priority,status,effect,source,proof,reason,next_action,question])
def base():return [row(n)for n in BASIC]+[row(n,priority='低',status='未実施')for n in ['消防への要請','警察への要請']]
def risk(active=True):
 return [k+'|'+('あり|'+({'継続警報':'警報器が鳴りやまない','ガス検知':'ドアポストからLEL1％検知'}[k])if active and k in RISKS[:2]else '不明|なし')for k in RISKS]
def result(rows=None,risks=None,facts='└入力された現場事実'):
 return '\n'.join(['[[FACTS]]',facts,'[[END_FACTS]]','[[RISK]]',*(risk()if risks is None else risks),'[[END_RISK]]','[[MEASURES]]',*(base()if rows is None else rows),'[[END_MEASURES]]'])
class PriorityState(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.doc=yaml.safe_load((R/'3-9-緊急保安業務エージェント_optimized.yaml').read_text());cls.ix=flat(cls.doc)
  for n in walk(cls.doc):
   actions=n.get('actions')
   if isinstance(actions,list)and any(a.get('id')=='setVariable_priorityRaw'for a in actions):
    a=next(i for i,x in enumerate(actions)if x.get('id')=='setVariable_priorityRaw');b=next(i for i,x in enumerate(actions)if x.get('id')=='conditionGroup_prioritySucceeded');cls.pipeline=actions[a:b];break
 def render(self,raw,report=REPORT,repair_outputs=None):
  values={'優先度判定結果':raw,'初回入力':report,'追加情報履歴':'','優先度形式修復回数':0,'優先度初回構造化結果':'','_repair_calls':0}
  outputs=iter([raw] if repair_outputs is None else repair_outputs)
  class Jump(Exception):pass
  def run(actions):
   for n in actions:
    if n['kind']=='SetVariable':values[n['variable'][6:]]=evaluate(n['value'],values)
    elif n['kind']=='ConditionGroup':run(next((c['actions']for c in n['conditions']if evaluate(c['condition'],values)),n.get('elseActions',[])))
    elif n['kind']=='AnswerQuestionWithAI':
     self.assertEqual(n['id'],'answer_priorityFormatRepair');self.assertFalse(n['autoSend'])
     values['_repair_calls']+=1;values[n['variable'][6:]]=next(outputs,'')
    elif n['kind']=='GotoAction':raise Jump(n['actionId'])
    else:self.fail(n['kind'])
  start=0
  for _ in range(3):
   try:run(self.pipeline[start:]);break
   except Jump as jump:start=next(i for i,n in enumerate(self.pipeline)if n['id']==str(jump))
  else:self.fail('Unbounded internal repair')
  return values
 def complete(self,effect='対象外'):
  return [row(n,status='実施済み',effect=effect,source='報告',proof='全措置実施済み')for n in BASIC+['消防への要請','警察への要請']]
 def test_closed_valve_and_unresolved_effect_are_both_preserved(self):
  v=self.render(result(base()+[row('メーターガス栓閉止','警報器鳴動宅',status='実施済み',effect='未解決',source='報告',proof=CLOSED,next_action='遮断効果と上流側対応を確認')]))
  self.assertTrue(v['措置状態妥当']);self.assertIn('メーターガス栓閉止（警報器鳴動宅）：実施済み　効果：未解決',v['優先度判定結果']);self.assertFalse(v['高優先度完了'])
 def test_lel_one_and_continuing_alarm_force_requests_high(self):
  v=self.render(result(base()+[row('メーターガス栓閉止')]))
  self.assertTrue(v['消防警察強制高'])
  for name in ['消防への要請','警察への要請']:
   self.assertIn(name+'（現場）：未実施',v['措置表示High']);self.assertNotIn(name,v['措置表示Low'])
  self.assertTrue(v['要請次対応'].startswith('└消防への要請'));self.assertIn('警察への要請',v['要請次対応'])
 def test_completed_request_remains_high_and_is_not_requested_again(self):
  rows=base();rows[-2]=row('消防への要請',priority='低',status='実施済み',source='報告',proof='消防は要請済み')
  v=self.render(result(rows+[row('メーターガス栓閉止')]),REPORT+'\n消防は要請済み')
  self.assertIn('消防への要請（現場）：実施済み',v['措置表示High']);self.assertNotIn('消防への要請',v['要請次対応']);self.assertIn('警察への要請',v['要請次対応'])
 def test_target_scope_does_not_spread_completion_to_other_room(self):
  v=self.render(result(base()+[row('メーターガス栓閉止','警報器鳴動宅',status='実施済み',effect='未解決',source='報告',proof=CLOSED),row('メーターガス栓閉止','別の住戸',status='要確認')]))
  self.assertIn('メーターガス栓閉止（警報器鳴動宅）：実施済み',v['措置表示High']);self.assertIn('メーターガス栓閉止（別の住戸）：要確認',v['措置表示High'])
 def test_unknown_is_not_rendered_as_explicitly_not_done(self):
  v=self.render(result(base()+[row('メーターガス栓閉止')]))
  self.assertIn('火気使用禁止の徹底（現場）：要確認',v['措置表示High'])
 def test_completed_investigation_is_not_reset_by_unreadable_number(self):
  rows=base();rows[4]=row(BASIC[4],'排水口',status='実施済み',source='報告',proof='排水口を検知器で調査済み。数値は不明')
  v=self.render(result(rows+[row('メーターガス栓閉止')]),REPORT+'\n排水口を検知器で調査済み。数値は不明')
  self.assertIn('排水口）：実施済み',v['措置表示High'])
 def test_unverified_completion_proof_holds_result(self):
  v=self.render(result(base()+[row('メーターガス栓閉止',status='実施済み',source='報告',proof='全戸閉止済み')]))
  self.assertFalse(v['措置状態妥当']);self.assertFalse(v['高優先度完了']);self.assertNotIn('全戸閉止済み',v['優先度判定結果'])
 def test_photo_completion_needs_adopted_photo_marker(self):
  for proof,valid in [('【写真有】ポケット警報器の設置（MS-007）',True),('機器が置かれている可能性がある',False)]:
   rows=base();rows[3]=row(BASIC[3],status='実施済み',source='写真',proof=proof)
   v=self.render(result(rows+[row('メーターガス栓閉止')]),REPORT+'\n'+proof);self.assertEqual(v['措置状態妥当'],valid)
 def test_missing_risk_block_or_bad_columns_fail_closed(self):
  for raw in [result(base()+[row('メーターガス栓閉止')],risk()[:-1]),result(base()+['誤った|列数']),result().replace('[[END_MEASURES]]','')]:
   v=self.render(raw);self.assertFalse(v['措置状態妥当']);self.assertFalse(v['高優先度完了'])
 def test_duplicate_action_and_scope_fail_closed(self):
  v=self.render(result(base()+[row(BASIC[0]),row('メーターガス栓閉止')]));self.assertFalse(v['措置状態妥当'])
 def test_all_actions_done_but_effect_unresolved_is_incomplete(self):
  rows=self.complete()+[row('メーターガス栓閉止',status='実施済み',effect='未解決',source='報告',proof=CLOSED)]
  v=self.render(result(rows),REPORT+'\n全措置実施済み');self.assertTrue(v['措置状態妥当']);self.assertFalse(v['高優先度完了']);self.assertIn('メーターガス栓閉止',v['措置次対応'])
 def test_confirmed_completed_actions_can_finish(self):
  v=self.render(result(self.complete(),risk(False)), '全措置実施済み')
  self.assertTrue(v['措置状態妥当']);self.assertTrue(v['高優先度完了']);self.assertEqual(v['措置確認質問'],'')
 def test_completion_keyword_inside_fact_does_not_end_loop(self):
  v=self.render(result(base()+[row('メーターガス栓閉止')],facts='└以前のAIは全て対応済みと書いた'))
  self.assertFalse(v['高優先度完了']);self.assertEqual(self.ix['conditionGroup_priorityLoopNeeded']['conditions'][0]['condition'],'=Not(Topic.高優先度完了)')
 def test_improvement_reassessment_is_not_permanently_forced_high(self):
  rows=base()+[row('メーターガス栓閉止')];risks=[k+'|なし|改善確認'for k in RISKS]
  v=self.render(result(rows,risks),REPORT+'\n改善確認：有効止漏済み、影響範囲全体の濃度反応臭気が消失、他の危険なし')
  self.assertFalse(v['消防警察強制高']);self.assertIn('消防への要請',v['措置表示Low'])
 def test_later_reopening_can_replace_earlier_closed_state(self):
  rows=base()+[row('メーターガス栓閉止','警報器鳴動宅',status='未実施',reason='同じ栓を再開したと最新報告')]
  v=self.render(result(rows),REPORT+'\n同じ栓を再開した')
  self.assertIn('メーターガス栓閉止（警報器鳴動宅）：未実施',v['措置表示High'])
 def test_nonexistent_positive_risk_quote_is_not_accepted(self):
  risks=risk();risks[0]='継続警報|あり|架空の警報報告';v=self.render(result(base()+[row('メーターガス栓閉止')],risks));self.assertFalse(v['措置状態妥当'])
 def test_detected_gas_and_alarm_enforce_existing_other_high_rules(self):
  v=self.render(result(base()+[row('消火器設置',priority='中'),row('メーターガス栓閉止',priority='中')]))
  for name in ['消火器設置','メーターガス栓閉止']:
   self.assertIn(name,v['措置表示High']);self.assertNotIn(name,v['措置表示Middle'])
 def test_invalid_measure_rows_do_not_hide_verified_request_risk(self):
  v=self.render(result(base()+['誤った|列数']))
  self.assertFalse(v['措置状態妥当']);self.assertIn('消防への要請（現場）：未実施',v['措置表示High'])
 def test_all_new_formulas_have_shallow_calls(self):
  for n in walk(self.pipeline):
   for expr in ([n.get('value','')]if n.get('kind')=='SetVariable'else[c['condition']for c in n.get('conditions',[])]):
    clean=re.sub(r'"(?:[^"]|"")*"','',expr);depth=peak=0
    for c in clean:
     if c=='(':depth+=1;peak=max(peak,depth)
     elif c==')':depth-=1
    self.assertEqual(depth,0,n.get('id'));self.assertLessEqual(peak,8,n.get('id'))
 def test_only_one_conditional_repair_model_call_is_added(self):
  old=yaml.safe_load((R/'originals/3-9-緊急保安業務エージェント(2).txt').read_text())
  self.assertEqual(sum(n.get('kind')=='AnswerQuestionWithAI'for n in walk(old))+1,sum(n.get('kind')=='AnswerQuestionWithAI'for n in walk(self.doc)))
  self.assertEqual(self.render(result(base()+[row('メーターガス栓閉止')]))['_repair_calls'],0)
 def test_main_and_repair_instructions_have_one_output_contract(self):
  for key in ['answer_priority','answer_priorityFormatRepair']:
   text=self.ix[key]['additionalInstructions']
   self.assertIn('[[FACTS]]',text);self.assertNotIn('見出し名・順序をそのまま守って',text)
  self.assertNotIn('# 出力フォーマット（このフォーマット以外',self.ix['setVariable_priorityPrompt']['value'])
  self.assertNotIn('必ず以下の見出し名・順序だけで',self.ix['setVariable_priorityGuideFixed']['value'])
 def test_legacy_text_is_repaired_without_asking_user_to_repeat(self):
  raw='【確認できた事実】\n└ガスを検知\n【初動措置　優先度：高】\n└メーターガス栓閉止：未実施'
  fixed=result(base()+[row('メーターガス栓閉止','警報器鳴動宅',status='実施済み',effect='未解決',source='報告',proof=CLOSED)])
  v=self.render(raw,repair_outputs=[fixed])
  self.assertEqual(v['_repair_calls'],1);self.assertTrue(v['措置状態妥当']);self.assertEqual(v['優先度初回構造化結果'],raw)
  self.assertIn('警報器鳴動宅）：実施済み',v['優先度判定結果']);self.assertNotIn('判定保留',v['優先度判定結果'])
 def test_repair_failure_is_bounded_and_does_not_blank_all_headings(self):
  v=self.render('旧形式も不完全',repair_outputs=['修復も形式不正'])
  self.assertEqual(v['_repair_calls'],1);self.assertEqual(v['優先度形式修復回数'],1);self.assertFalse(v['高優先度完了'])
  self.assertNotIn('└判定保留',v['優先度判定結果']);self.assertIn(BASIC[0],v['措置表示High'])
 def test_one_bad_action_keeps_other_completed_actions_and_high_requests(self):
  rows=base()+[row('メーターガス栓閉止','警報器鳴動宅',status='実施済み',effect='未解決',source='報告',proof=CLOSED),'消火器設置|列数不正']
  v=self.render(result(rows));self.assertFalse(v['措置状態妥当'])
  self.assertIn('メーターガス栓閉止（警報器鳴動宅）：実施済み',v['措置表示High']);self.assertIn('消防への要請',v['措置表示High'])
 def test_missing_other_risk_does_not_hide_independently_proven_alarm_and_detection(self):
  v=self.render(result(base()+[row('メーターガス栓閉止')],risk()[:-1]))
  self.assertFalse(v['措置状態妥当']);self.assertTrue(v['消防警察強制高']);self.assertIn('消防への要請',v['措置表示High'])
 def test_conflicting_risk_does_not_create_a_positive_flag(self):
  risks=risk()+['継続警報|なし|なし']
  v=self.render(result(base()+[row('メーターガス栓閉止')],risks))
  self.assertFalse(v['現危険Alarm']);self.assertFalse(v['消防警察強制高'])
  self.assertNotIn('消防への要請',v['措置表示Low']);self.assertIn('消防への要請',v['措置表示Middle'])
 def test_empty_primary_and_repair_responses_do_not_cause_unbounded_retry(self):
  v=self.render(None,repair_outputs=[None])
  self.assertEqual(v['_repair_calls'],1);self.assertFalse(v['高優先度完了']);self.assertNotIn('└判定保留',v['優先度判定結果'])
 def test_wrong_block_order_cannot_declare_complete(self):
  raw=result(self.complete(),risk(False));a=raw.index('[[RISK]]');b=raw.index('[[MEASURES]]')
  raw=raw[:a]+raw[b:]+raw[a:b]
  v=self.render(raw,'全措置実施済み');self.assertFalse(v['措置状態妥当']);self.assertFalse(v['高優先度完了'])
 def test_wrappers_crlf_fullwidth_pipes_and_outer_spaces_are_format_only(self):
  raw='```text\r\n'+result(base()+[row('メーターガス栓閉止')]).replace('|',' ｜ ').replace('\n','\r\n')+'\r\n```'
  v=self.render(raw);self.assertTrue(v['措置状態妥当']);self.assertEqual(v['_repair_calls'],0)
 def test_internal_spaces_in_verbatim_evidence_are_preserved(self):
  proof='A室の栓を  閉めた';report=REPORT+'\n'+proof
  v=self.render(result(base()+[row('メーターガス栓閉止','A室',status='実施済み',source='報告',proof=proof)]),report)
  self.assertTrue(v['措置状態妥当']);self.assertIn(proof,v['優先度判定結果']);self.assertEqual(v['_repair_calls'],0)
 def test_status_and_action_aliases_do_not_rewrite_evidence(self):
  proof='A室メーターガス栓の閉止';rows=base()+[row('メーターガス栓の閉止','A室',status='対応済み',source='報告',proof=proof)]
  v=self.render(result(rows),REPORT+'\n'+proof)
  self.assertTrue(v['措置状態妥当']);self.assertIn('メーターガス栓閉止（A室）：実施済み',v['優先度判定結果']);self.assertIn(proof,v['優先度判定結果'])
 def test_concrete_format_example_is_accepted_by_saved_parser(self):
  from priority_recovery import FORMAT
  example='[[FACTS]]'+FORMAT.split('[[FACTS]]',1)[1].split('[[END_MEASURES]]',1)[0]+'[[END_MEASURES]]'
  v=self.render(example,'現場情報はまだ未報告。')
  self.assertTrue(v['措置状態妥当']);self.assertEqual(v['_repair_calls'],0)
 def test_duplicate_action_targets_are_not_displayed_as_conflicting_states(self):
  rows=base()+[row('メーターガス栓閉止','A室',status='実施済み',source='報告',proof=CLOSED),row('メーターガス栓閉止','A室',status='未実施')]
  v=self.render(result(rows));self.assertFalse(v['措置状態妥当']);self.assertNotIn('メーターガス栓閉止（A室）',v['優先度判定結果'])
if __name__=='__main__':unittest.main()
