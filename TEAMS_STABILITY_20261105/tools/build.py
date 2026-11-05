"""Bounded re-generation after a failed validation; skip guide search only after
purpose classification AND an explicit emergency-field signal. Never accept invalid advice.
"""
from pathlib import Path
import difflib,yaml
from yaml_edit import edit,setv,cg,nodes
ROOT=Path(__file__).resolve().parents[1]
SIGNALS=['ガス臭','ガス漏','ガスが噴','ガスを止め','ガスが止ま','ガスが出','臭気','臭い','におい','異臭','漏えい','漏洩','検知','警報','LEL','一酸化炭素','CO中毒','爆発','火災','供給支障','供給を止め']
def guard():return '=And(Topic.目的分野 = "現場対応アドバイス", Or('+', '.join('"'+s+'" in Topic.初回入力'for s in SIGNALS)+'))'
RETRY='=And(Topic.優先度表示検証 <> "合格", Topic.優先度様式再試行回数 < 1)'
def go(i,target):return {'kind':'GotoAction','id':i,'actionId':target}
def build():
 p=ROOT/'source/変更前_1.yaml'
 def shortcut(n):return [n,cg('conditionGroup_runtimeDirectEmergency',guard(),[setv('setVariable_runtimeEmergencyFolder','Topic.対象フォルダ','="09_緊急保安_共通"'),go('goto_runtimeDirectEmergency','64VMOA')])]
 s=edit(p,{'setVariable_normalizeInferredPurpose':shortcut});(ROOT/'1_貼り替え用.txt').write_text(s);(ROOT/'1_貼り替え用.yaml').write_text(s)
 p=ROOT/'source/変更前_3-9.yaml'
 def bounded(n):
  retry=cg('conditionGroup_runtimePriorityRetry',RETRY,[setv('setVariable_runtimePriorityRetryCount','Topic.優先度様式再試行回数','=Topic.優先度様式再試行回数 + 1'),setv('setVariable_runtimeClearFailedResult','Topic.優先度判定結果','=""'),go('goto_runtimePriorityRetry','answer_priority')])
  return [n,retry]
 def diagnostic(n):n['activity']+='\n\n確認用コード：{Topic.優先度経路診断}'
 ops={'setVariable_priorityGateSnapshot':bounded,'sendActivity_priorityFailed':diagnostic}
 def version(n):n['value']=n['value'].replace('subaru-text-20261102-v2','subaru-runtime-20261105-v1')
 for n in nodes(yaml.safe_load(p.read_text())):
  if n.get('kind')=='SetVariable'and n.get('variable')=='Topic.優先度経路診断'and n['id']!='setVariable_priorityGateSnapshot':ops[n['id']]=version
 def gate(n):version(n);return bounded(n)
 ops['setVariable_priorityGateSnapshot']=gate
 s=edit(p,ops);(ROOT/'3-9_貼り替え用.txt').write_text(s);(ROOT/'3-9_貼り替え用.yaml').write_text(s)
 for src,dest in [('変更前_1.yaml','1_貼り替え用.yaml'),('変更前_3-9.yaml','3-9_貼り替え用.yaml')]:
  before=(ROOT/'source'/src).read_text();after=(ROOT/dest).read_text();(ROOT/'validation'/(dest+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile=src,tofile=dest)))
 print('Built two targeted patches, retaining the existing Teams display and save contract')
if __name__=='__main__':build()
