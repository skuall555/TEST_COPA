"""Build only the 2026-10-27 changes on the immutable 61e0c4a baseline."""
from pathlib import Path
import difflib,json,subprocess,yaml
from restart_support import edit,setv,cg,nodes
from restart_rules import MENU,PURPOSE,FIRE,URGENT,APPEARANCE,IMAGE_REPRESENTATION
R=Path(__file__).resolve().parents[1]
BASE='61e0c4a13b8c68c53947cb03a12d9b9d2d2221fa'
FILES=['1-マニュアル関連入口_optimized.yaml','3-9-緊急保安業務エージェント_optimized.yaml','4-9-画像分析エージェント_緊急保安_optimized.yaml','SUBARU_エージェント指示_optimized.txt']
def baseline(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def q(s):return '"'+s.replace('"','""')+'"'
def literal(s):return '='+q(s)
def append_literal(n,text):
 assert n['value'].endswith('"');n['value']=n['value'][:-1]+'\n'+text.replace('"','""')+'"'
def body(n):
 assert n['value'].startswith('="')and n['value'].endswith('"')
 return n['value'][2:-1].replace('""','"')
def goto(ident,target):return {'kind':'GotoAction','id':ident,'actionId':target}
def choice_condition(number):
 text='Topic.目的選択入力'
 forms=[str(number),'['+str(number)+']','［'+str(number)+'］',str(number)+'です',str(number)+'番',str(number)+'番です']
 return 'Or('+', '.join(text+' = '+q(s)for s in forms)+')'
MEANING='=Topic.追加情報履歴 & Char(10) & "選択した目的：" & If(Topic.目的分野 = "現場対応アドバイス", "現場対応アドバイス（ガス漏れ対応中）", Topic.目的分野)'
def main():
 for name in FILES:(R/name).write_text(baseline(name))
 entry=R/FILES[0]
 def detect(n):
  n['value']='=""'
  ai={'kind':'AnswerQuestionWithAI','id':'answer_inferPurposeFromText','autoSend':False,'variable':'Topic.目的分野',
   'userInput':'=If(Topic.目的再試行回数 > 0, "【元の依頼】" & Topic.初回入力 & Char(10) & "【目的選択への最新回答】" & Topic.目的回答, "【元の依頼】" & Topic.初回入力 & Char(10) & "【追加履歴】" & Topic.追加情報履歴)',
   'additionalInstructions':PURPOSE}
  canonical='=If(Or(Trim(Topic.目的分野) = "現場対応アドバイス", Trim(Topic.目的分野) = "マニュアル確認", Trim(Topic.目的分野) = "マニュアル改訂"), Trim(Topic.目的分野), "")'
  remember=cg('conditionGroup_rememberPurposeReply','=And(Topic.目的再試行回数 > 0, Topic.目的分野 <> "")',[setv('setVariable_rememberPurposeReply','Topic.追加情報履歴',MEANING)])
  return [n,ai,setv('setVariable_normalizeInferredPurpose','Topic.目的分野',canonical),remember]
 def choice(n):
  normalize='=Trim(Substitute(Substitute(Substitute(Substitute(Topic.目的回答, "１", "1"), "２", "2"), "３", "3"), "　", " "))'
  classify='=If('+choice_condition(1)+', "現場対応アドバイス", If('+choice_condition(2)+', "マニュアル確認", If('+choice_condition(3)+', "マニュアル改訂", "")))'
  field=[setv('setVariable_numberFieldFolder','Topic.対象フォルダ','="09_緊急保安_共通"'),goto('goto_numberFieldExistingDialog','64VMOA')]
  accepted=[setv('setVariable_rememberNumberPurpose','Topic.追加情報履歴',MEANING),cg('conditionGroup_numberPurposeIsField','=Topic.目的分野 = "現場対応アドバイス"',field,[goto('goto_numberManualExistingWorkflow','setVariable_classifyRetryCount')])]
  return [n,setv('setVariable_normalizePurposeNumber','Topic.目的選択入力',normalize),setv('setVariable_purposeFromNumber','Topic.目的分野',classify),cg('conditionGroup_purposeNumberAccepted','=Topic.目的分野 <> ""',accepted)]
 ops={
 'setVariable_buildVersion':lambda n:n.update(value='="巡回-restart-61e0c4a-20261027"'),
 'setVariable_purposeRetryCount':lambda n:[n,setv('setVariable_purposeReplyInit','Topic.目的回答','=""'),setv('setVariable_purposeChoiceInit','Topic.目的選択入力','=""')],
 'setVariable_purposeDetect':detect,
 'question_purposeMissing':lambda n:n.update(prompt=MENU),
 'setVariable_appendPurposeHistory':choice,
 'sendActivity_purposeGiveUp':lambda n:n.update(activity='3回の確認で目的を特定できなかったため、この確認を終了します。新しい会話で依頼内容と該当する番号を入力してください。\n\n'+MENU),
 'conditionGroup_probeMode':lambda n:n['conditions'][0].update(condition='=Or(Trim(Topic.初回入力) = "計測", StartsWith(Trim(Topic.初回入力), "計測 "), StartsWith(Trim(Topic.初回入力), "計測　"))'),
 'conditionGroup_probeFromPurpose':lambda n:n['conditions'][0].update(condition='=Or(Trim(Topic.目的回答) = "計測", StartsWith(Trim(Topic.目的回答), "計測 "), StartsWith(Trim(Topic.目的回答), "計測　"))'),
 }
 s=edit(entry,ops)
 anchor='  内部的にはユーザーの質問を「目的」と「対象フォルダ」に振り分ける。'
 s=s.replace(anchor,anchor+'\n  明示ラベルがなくても文章全体の意味から目的を判定し、不明時だけ番号で確認する。番号返信は質問中の本トピックが受け取り、1は既存の緊急保安トピックへ遷移する。')
 anchor='      - 計測\n'
 extra=['マンションの共用廊下でガス臭がする','警報器が鳴り続けていてガスを検知した','供給を止められないので対応を相談したい','ガス漏れ対応の社内基準を調べたい','手順書のこの規定はどうなっている','消防要請の基準に項目を追加したい','社内マニュアルの記載を削除したい','ガス業務について相談したい']
 assert s.count(anchor)==1;s=s.replace(anchor,anchor+''.join('      - '+x+'\n'for x in extra));entry.write_text(s)
 field=R/FILES[1]
 def priority_guide(n):
  text=body(n);a=text.index('# 消防・警察への要請');b=text.index('# 立入禁止・保安柵・警戒区域',a)
  text=text[:a]+FIRE+text[b:]
  text=text.replace('# 判定手順',URGENT+'# 判定手順',1)
  old='【ポケット警報器】\n        臭気・検知場所、天井付近、収納、排水口、PS、床下等、'
  # Literal contents have no YAML indentation once parsed.
  old=old.replace('        ','')
  assert old in text
  text=text.replace(old,'【ポケット警報器】\n\n床面、地面、棚、設備付近等に置く・設置して監視する機器。先端に細長い筒や検査プローブを付けた手持ち検査機器として説明しない。手持ちで筒状プローブを配管等へ向けて検査するものは、原則として可燃性ガス検知器として区別する。\n臭気・検知場所、天井付近、収納、排水口、PS、床下等、')
  n['value']=literal(text)
 def priority_prompt(n):
  n['value']=n['value'].replace('下記【ガイド抜粋】は初動措置_AI優先度判断ガイド.docxの内容です。','下記【ガイド抜粋】は既存の固定判断ルールに、今回指定された消防・警察の現在危険と改善後再評価の規則を反映したものです。')
  append_literal(n,'# 今回の消防・警察ルールの適用\n消防・警察への要請はガイドの同名節と判定順序の補足で評価し、過去と現在、停止操作と実際の止漏効果、優先度と要請の実施状況を区別する。未要請を低の理由にしない。高と判断した要請は高の見出しへ置く。明らかな緊急事態では質問の回答待ちで要請案内を遅らせない。既に報告された情報を繰り返し質問しない。\n他の処理・既存の8見出しの回答形式は維持する。')
 field.write_text(edit(field,{'setVariable_priorityGuideFixed':priority_guide,'setVariable_priorityPrompt':priority_prompt,'answer_priority':lambda n:n.update(additionalInstructions=n['additionalInstructions']+'\n消防・警察はガイドの同名節を適用する。継続性・影響範囲・制御可否・改善を最新報告で照合し、高条件が明示された場合や明らかな緊急事態では要請案内を先行する。要請の実施状況を理由に優先度を下げず、判断した高・中・低と表示見出しを一致させる。')}))
 photo=R/FILES[2]
 def facts(n):
  text=body(n);a=text.index('■ポケット警報器');b=text.index('■火気厳禁表示シート',a)
  text=text[:a]+APPEARANCE+text[b:]
  text=text.replace('機器の形状や同時テキストだけで機器を確定しない。','色だけ・箱形だけ・置いてあるだけ・同時テキストだけで機器を確定しない。本体・先端・配置など複数の画像根拠が一致すれば名称を記載し、候補・未確認と区別する。')
  n['value']=literal(text+'\n\n'+IMAGE_REPRESENTATION)
 def photo_prompt(n):
  text=body(n)
  old='・黄色い携帯機器が置かれている／ポケット警報器と思われる機器がある\n  → ポケット警報器。室内なら MS-007、屋内共用部なら MS-008、屋外なら MS-009。\n  ※設置位置の条件は下記【設置位置の判定】で確認する。'
  assert old in text
  new='・本体と配置を照合し、ポケット警報器として識別できる機器が置かれている\n  → ポケット警報器の設置候補。室内なら MS-007、屋内共用部なら MS-008、屋外なら MS-009。\n  ※置かれた未知の箱や検知器を警報器へ置換しない。手持ちで筒状プローブを向ける検査は可燃性ガス検知器として別に扱う。\n  ※本体の存在と設置条件への適合を分け、従来の【設置位置の判定】で確認する。'
  n['value']=literal(text.replace(old,new)+'\n\n【機器の描写の整合】\nポケット警報器は床面・地面・棚・設備付近等に置く監視機器で、細長い筒や検査プローブを付けた手持ち機器として説明しない。可燃性ガス検知器は筒状プローブ・吸引部を持ち、作業員が手に持って検査する機器として区別する。画像内の複数機器は別々に照合する。')
 photo.write_text(edit(photo,{'setVariable_prompt1':facts,'setVariable_prompt2':photo_prompt,'answer_photoGuidelineJudge':lambda n:n.update(additionalInstructions=n['additionalInstructions']+'\nポケット警報器と可燃性ガス検知器は機器ごとに区別する。先端の筒・プローブを向ける手持ち検査をポケット警報器設置へ取り違えない。未知の箱が置かれているだけでは警報器と確定しない。')}))
 instructions=R/FILES[3];text=instructions.read_text();text=text.replace('・数字だけの返信（1、2、0、[1] など）　修理方法の候補選択です。必ず実行中のトピックへ渡してください。','・数字だけの返信（1、2、3、１、２、３、0、[1] など）や「1です」「２番」　目的選択または修理候補選択への回答です。必ず質問中のトピックへ渡し、あなた自身で意味付けや別の選択肢を作らないでください。')
 text+='\n## 目的判定と番号選択（61e0c4a基準の追記）\n業務の自然文も「1-マニュアル関連入口」へ渡してください。目的の意味判定と不明時の番号質問は入口トピックが行います。番号の対応は1＝ガス漏れ対応中、2＝社内基準・マニュアル確認、3＝社内基準・マニュアル変更です。質問中はそのトピックへ返信を渡し、別エージェントへ接続するよう利用者に頼まず、既存トピック内の遷移に任せてください。\n'
 instructions.write_text(text)
 from additional_build import apply
 apply(field)
 folder=R/'diffs/restart_61e0c4a';folder.mkdir(parents=True,exist_ok=True)
 for name in FILES:(folder/(name+'.diff')).write_text(''.join(difflib.unified_diff(baseline(name).splitlines(True),(R/name).read_text().splitlines(True),fromfile='61e0c4a/'+name,tofile='restart_20261027/'+name)))
 # Keep original-to-current diffs coherent as well.
 origins=['1-マニュアル関連入口 (1).txt','3-9-緊急保安業務エージェント(2).txt','4-9-画像分析エージェント_緊急保安(1).txt','00_現行エージェント指示.txt']
 for src,dst in zip(origins,FILES):(R/'diffs'/(dst+'.diff')).write_text(''.join(difflib.unified_diff((R/'originals'/src).read_text().splitlines(True),(R/dst).read_text().splitlines(True),fromfile='originals/'+src,tofile=dst)))
 print('Built from',BASE)
 for name in FILES[:3]:print(name,len((R/name).read_text().splitlines()),'lines')
if __name__=='__main__':main()
