"""Baseline preservation and routing with mocked classifier replies; not live AI/Studio tests."""
import re,unittest,yaml
from validate import R,flat,walk,own,dependencies
from restart_build import FILES,baseline
from restart_rules import MENU,POCKET_ILLUSTRATION,DETECTOR_ILLUSTRATION
from restart_scalar import evaluate
class Restart(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.before=[yaml.safe_load(baseline(n))for n in FILES[:3]];cls.after=[yaml.safe_load((R/n).read_text())for n in FILES[:3]]
  cls.old=[flat(x)for x in cls.before];cls.new=[flat(x)for x in cls.after]
 def simulate(self,replies,classes):
  state={'初回入力':'通報内容：共用廊下で臭気を感じる','追加情報履歴':'','目的再試行回数':0,'目的回答':'','目的選択入力':'','目的分野':''};replies=iter(replies);labels=iter(classes);questions=[];route=None;ai_calls=0;ix=self.new[0]
  class Jump(Exception):pass
  class Stop(Exception):pass
  def run(actions):
   nonlocal route,ai_calls
   for n in actions:
    kind=n['kind']
    if kind=='SetVariable':state[n['variable'][6:]]=evaluate(n['value'],state)
    elif kind=='AnswerQuestionWithAI':
     self.assertEqual(n['id'],'answer_inferPurposeFromText');self.assertFalse(n['autoSend']);ai_calls+=1;state[n['variable'][6:]]=next(labels,'不明')
    elif kind=='ConditionGroup':run(next((c['actions']for c in n['conditions']if evaluate(c['condition'],state)),n.get('elseActions',[])))
    elif kind=='Question':questions.append(n['prompt']);state[n['variable'][6:]]=next(replies)
    elif kind=='GotoAction':raise Jump(n['actionId'])
    elif kind=='EndDialog':route='終了';raise Stop()
    elif kind!='SendActivity':self.fail(kind)
  for _ in range(8):
   run([ix[k]for k in ['setVariable_purposeDetect','answer_inferPurposeFromText','setVariable_normalizeInferredPurpose','conditionGroup_rememberPurposeReply']])
   if state['目的分野']!='':route=state['目的分野'];break
   try:run([ix['conditionGroup_purposeMissing']])
   except Jump as jump:
    target=str(jump)
    if target=='setVariable_purposeDetect':continue
    if target=='64VMOA':route='現場対応アドバイス';break
    if target=='setVariable_classifyRetryCount':route=state['目的分野'];break
    self.fail(target)
   except Stop:break
  else:self.fail('Unbounded loop')
  return state,questions,route,ai_calls
 def test_existing_ids_and_connector_dependencies_preserved(self):
  for old,new in zip(self.old,self.new):self.assertLessEqual(set(old),set(new));self.assertEqual(dependencies(old),{k:v for k,v in dependencies(new).items()if k in old})
 def test_only_authorized_existing_nodes_change(self):
  allowed=[{'main','setVariable_buildVersion','setVariable_purposeDetect','question_purposeMissing','sendActivity_purposeGiveUp','conditionGroup_probeMode','conditionGroup_probeFromPurpose'},{'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority','conditionGroup_prioritySucceeded','conditionGroup_priorityLoopNeeded','sendActivity_priorityFailed'},{'setVariable_prompt1','setVariable_prompt2','answer_photoGuidelineJudge'}]
  for old,new,permit in zip(self.old,self.new,allowed):self.assertLessEqual({k for k in old if own(old[k])!=own(new[k])},permit)
  self.assertEqual({k:v for k,v in own(self.old[0]['main']).items()if k!='intent'},{k:v for k,v in own(self.new[0]['main']).items()if k!='intent'})
  original=self.old[0]['main']['intent']['triggerQueries'];self.assertEqual(self.new[0]['main']['intent']['triggerQueries'][:len(original)],original)
 def test_unrelated_manual_nodes_identical(self):
  for k,n in self.old[0].items():
   if any(x in k.lower()for x in ['manualcheck','manualrevise','repairrow','formatrow']):self.assertEqual(own(n),own(self.new[0][k]),k)
 def test_one_new_string_variable_no_new_table_expressions(self):
  def variables(tree):return {n['variable']for n in walk(tree)if isinstance(n.get('variable'),str)}
  self.assertEqual(variables(self.after[0])-variables(self.before[0]),{'Topic.目的選択入力'})
  for old,new in zip(self.old,self.new):
   for k in set(new)-set(old):self.assertFalse(any(x in new[k].get('value','')for x in ['Filter(','Concat(','Distinct(',' As ']),k)
 def test_half_full_width_and_suffixes_choose_correct_routes(self):
  for text,want in [('1','現場対応アドバイス'),('１','現場対応アドバイス'),('1です','現場対応アドバイス'),('１番です','現場対応アドバイス'),('2','マニュアル確認'),('２番','マニュアル確認'),('[2]','マニュアル確認'),('３','マニュアル改訂'),('３番','マニュアル改訂'),('［３］','マニュアル改訂')]:
   with self.subTest(text=text):
    s,q,route,calls=self.simulate([text],['不明']);self.assertEqual(route,want);self.assertEqual(calls,1);self.assertEqual(q,[MENU]);self.assertIn(text,s['追加情報履歴']);self.assertEqual(s['初回入力'],'通報内容：共用廊下で臭気を感じる')
 def test_clear_natural_reply_does_not_ask_again(self):
  for text,label in [('マニュアルを確認したい','マニュアル確認'),('規定を変更したい','マニュアル改訂'),('1番でお願いします','現場対応アドバイス')]:
    s,q,route,calls=self.simulate([text],['不明',label]);self.assertEqual(route,label);self.assertEqual(len(q),1);self.assertEqual(calls,2);self.assertIn('選択した目的：',s['追加情報履歴'])
 def test_invalid_reply_repeats_same_menu(self):
  s,q,route,calls=self.simulate(['9','２'],['不明','不明']);self.assertEqual(q,[MENU,MENU]);self.assertEqual(route,'マニュアル確認')
 def test_invalid_replies_stop_after_three_questions(self):
  s,q,route,calls=self.simulate(['9','0','1と2'],['不明']*4);self.assertEqual(q,[MENU]*3);self.assertEqual(route,'終了');self.assertEqual(s['目的再試行回数'],3)
 def test_clear_third_reply_is_accepted(self):
  s,q,route,calls=self.simulate(['9','0','３'],['不明']*3);self.assertEqual(len(q),3);self.assertEqual(route,'マニュアル改訂')
 def test_unexpected_classifier_output_is_not_an_intent(self):
  s,q,route,calls=self.simulate(['2'],['たぶん現場対応アドバイスです']);self.assertEqual(route,'マニュアル確認');self.assertEqual(q,[MENU])
 def test_clear_initial_intent_skips_menu(self):
  for label in ['現場対応アドバイス','マニュアル確認','マニュアル改訂']:
   s,q,route,calls=self.simulate([],[label]);self.assertEqual(route,label);self.assertEqual(q,[])
 def test_one_jumps_to_existing_dialog_with_same_bindings(self):
  self.assertEqual(self.new[0]['goto_numberFieldExistingDialog']['actionId'],'64VMOA');self.assertEqual(self.old[0]['64VMOA'],self.new[0]['64VMOA']);self.assertEqual(self.new[0]['setVariable_numberFieldFolder']['value'],'="09_緊急保安_共通"')
 def test_measurement_word_in_manual_question_does_not_trigger_probe(self):
  for key,var in [('conditionGroup_probeMode','初回入力'),('conditionGroup_probeFromPurpose','目的回答')]:
   expr=self.new[0][key]['conditions'][0]['condition']
   for text,want in [('計測',True),('計測 ガス臭',True),('計測　検知器',True),('計測基準を確認したい',False),('ガス濃度の計測手順を変更したい',False)]:self.assertEqual(evaluate(expr,{var:text}),want)
 def test_initial_message_writers_unchanged(self):
  self.assertEqual({k:n for k,n in self.old[0].items()if n.get('variable')=='Topic.初回入力'},{k:n for k,n in self.new[0].items()if n.get('variable')=='Topic.初回入力'})
 def test_later_broken_parsers_are_not_inherited(self):
  for doc in self.after:
   for n in walk(doc):self.assertFalse(n.get('id','').startswith(('setVariable_p5','setVariable_photoAudit','setVariable_priorityMeasure','answer_priorityFormatRepair')))
  self.assertNotIn('[[MEASURES]]',self.new[1]['setVariable_priorityPrompt']['value'])
 def test_questions_image_trigger_and_return_preserved(self):
  for old,new in zip(self.old,self.new):
   for k,n in old.items():
    if n['kind']=='Question'and k!='question_purposeMissing':self.assertEqual(n,new[k])
  for key in ['inputType','outputType']:self.assertEqual(self.before[1][key],self.after[1][key])
  for key in ['kind','id','condition','priority','type']:self.assertEqual(self.before[2]['beginDialog'][key],self.after[2]['beginDialog'][key])
  for k in ['setVariable_appendImageResultToGlobalHistory','setVariable_globalDone','setVariable_globalCheck']:self.assertEqual(self.old[2][k],self.new[2][k])
 def test_image_specs_are_verbatim_and_not_photo_facts(self):
  s=self.new[2]['setVariable_prompt1']['value'];self.assertIn(POCKET_ILLUSTRATION,s);self.assertIn(DETECTOR_ILLUSTRATION,s);self.assertIn('今回の写真にその機器が写っているという事実ではない',s);self.assertNotIn('置いてあるだけならポケット警報器',s)
 def test_other_safety_rules_and_human_output_format_unchanged(self):
  a=self.old[1]['setVariable_priorityGuideFixed']['value'];b=self.new[1]['setVariable_priorityGuideFixed']['value'];self.assertEqual(a[a.index('# 最重要'):a.index('# 禁止事項')],b[b.index('# 最重要'):b.index('# 禁止事項')]);self.assertIn('LEL1％',b);self.assertIn('一時的な反応消失',b);self.assertIn('未要請だから低',b)
 def test_new_control_expressions_short_and_shallow(self):
  for old,new in zip(self.old,self.new):
   for k in set(new)-set(old):
    n=new[k]
    for expr in [n.get('value','')]+[c['condition']for c in n.get('conditions',[])]:
     clean=re.sub(r'"(?:[^"]|"")*"','',expr);depth=peak=0
     for x in clean:
      if x=='(':depth+=1;peak=max(peak,depth)
      elif x==')':depth-=1
     self.assertEqual(depth,0,k);self.assertLessEqual(peak,8,k)
     if expr:self.assertLessEqual(len(expr),1000,k)
if __name__=='__main__':unittest.main()
