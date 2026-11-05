"""Display-only patch of the user's live 2026-11-05 field topic.
No flow contract, storage, model, priority rule or image routing changes.
"""
from pathlib import Path
import difflib,json,re,yaml
from yaml_edit import edit,setv,nodes
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/変更前_3-9.yaml'
YAML=ROOT/'3-9_貼り替え用.yaml'
TEXT=ROOT/'3-9_貼り替え用.txt'

def q(s):return '"'+s.replace('"','""')+'"'
def call(name,*args):return name+'('+', '.join(args)+')'
def w(fields,body):return call('With','{'+', '.join(k+': '+v for k,v in fields.items())+'}',body)
def index(data):return {n['id']:n for n in nodes(data)if'id'in n and'kind'in n}
def measures():
 old=index(yaml.safe_load(SOURCE.read_text()));out=[]
 for ident,n in old.items():
  match=re.fullmatch('setVariable_itemLine(P[0-9]{2})',ident)
  if match:out.append((match[1],re.search(r'└([^"：]+)：',n['value'])[1]))
 assert len(out)==23
 return out
def label(code):return call('Switch',code,*[q(x)for pair in measures()for x in pair],code)
def snapshot():
 mapping=call('Switch','true',*[x for code,name in measures()for x in [call('StartsWith','labelText',q('└'+name+'：')),q(code)]],'""')
 return '=Concat(Filter(Split(Topic.判定表示行, Char(30)), Not(IsBlank(Value))), '+w({'parts':'Split(Value, "|")'},w({'labelText':'Last(parts).Value'},mapping+' & "|" & First(parts).Value & "|" & Last(FirstN(parts, 2)).Value'))+', Char(10))'
def differences():
 def rows(var):return 'Filter(Split('+var+', Char(10)), Not(IsBlank(Value)))'
 previous='First(Filter(Split(Topic.Teams前回判定, Char(10)), StartsWith(Value, code & "|"))).Value'
 oldp='Last(FirstN(Split(previous, "|"), 2)).Value';olds='Last(Split(previous, "|")).Value'
 prefix='"・" & '+label('code')+' & "："'
 both=call('If','priority <> '+oldp,prefix+' & '+oldp+' & " → " & priority & Char(10)','""')+' & '+call('If','state <> '+olds,prefix+' & "実施状況 " & '+olds+' & " → " & state & Char(10)','""')
 line=call('If','IsBlank(previous)',prefix+' & "新たに判定（" & priority & "／" & state & "）" & Char(10)',both)
 current=call('Concat',rows('Topic.Teams今回判定'),w({'parts':'Split(Value, "|")'},w({'code':'First(parts).Value','priority':'Last(FirstN(parts, 2)).Value','state':'Last(parts).Value'},w({'previous':previous},line))))
 removed=call('Concat',rows('Topic.Teams前回判定'),w({'code':'First(Split(Value, "|")).Value'},call('If','IsBlank(First(Filter(Split(Topic.Teams今回判定, Char(10)), StartsWith(Value, code & "|"))).Value)',prefix+' & "今回は未判定（解消とは判断しません）" & Char(10)','""')))
 compare=w({'changes':'Trim('+current+' & '+removed+')'},'If(IsBlank(changes), "前回から優先度・実施状況の変更はありません。", changes)')
 return '=If(Topic.Teams比較区分 = "比較可", '+compare+', If(Topic.Teams比較区分 = "初回", "", "前回比較は現在できません。過去情報を確認できていないため、変更なしとは判断していません。"))'
def render():
 s='"📍 現場アドバイス" & Char(10) & If(Topic.Teams比較区分 = "初回", "", Char(10) & "【① 前回報告からの変更点】" & Char(10) & Topic.Teams変更点 & Char(10)) & Char(10) & "【② 初動措置の優先度】"'
 for title,var in [('🔴 高','判定高欄'),('🟠 中','判定中欄'),('🟢 低','判定低欄')]:
  s+=' & Char(10) & '+q(title)+' & Char(10) & If(IsBlank(Topic.'+var+'), "・該当なし", Substitute(Topic.'+var+', "└", "・"))'
 s+=' & Char(10) & Char(10) & "【③ 確認したいこと】" & Char(10) & Topic.判定確認文 & Char(10) & Char(10) & "【④ ネクストアクション】" & Char(10) & Substitute(Topic.判定次行動, "└", "・")'
 return '='+s

DISPLAY='If(Topic.Teams表示チャネル = "msteams", Topic.Teams現場表示, Topic.優先度判定結果)'
def display_steps():
 same='And(Not(IsBlank(Topic.Teams現在案件ID)), Not(IsBlank(System.User.Id)), Global.Teams表示前回案件ID = Topic.Teams現在案件ID, Global.Teams表示前回会話ID = System.Conversation.Id, Global.Teams表示前回利用者ID = System.User.Id, Global.Teams表示前回チャネル = Topic.Teams表示チャネル)'
 specs=[('Channel','Topic.Teams表示チャネル','=Lower(Coalesce(System.Activity.ChannelId, ""))'),('Case','Topic.Teams現在案件ID','=Coalesce(Topic.案件ID, "")'),('Snapshot','Topic.Teams今回判定',snapshot()),('Previous','Topic.Teams前回判定','=If('+same+', Coalesce(Global.Teams表示前回判定, ""), "")'),('Compare','Topic.Teams比較区分','=If(Or(IsBlank(Topic.Teams現在案件ID), IsBlank(System.Conversation.Id), IsBlank(System.User.Id)), "比較不可", If('+same+', If(IsBlank(Topic.Teams前回判定), "比較不可", "比較可"), "初回"))'),('Changes','Topic.Teams変更点',differences()),('Render','Topic.Teams現場表示',render())]
 out=[setv('setVariable_teamsDisplay'+suffix,var,expr)for suffix,var,expr in specs]
 # Shallow substitutions avoid a deeply nested formula and leave Apps text intact.
 out += [setv('setVariable_teamsDisplayName'+code,'Topic.Teams現場表示','=Substitute(Topic.Teams現場表示, '+q(code)+', '+q(name)+')')for code,name in reversed(measures())]
 for suffix,var,expr in [('Case','Global.Teams表示前回案件ID','=Topic.Teams現在案件ID'),('Conversation','Global.Teams表示前回会話ID','=System.Conversation.Id'),('User','Global.Teams表示前回利用者ID','=System.User.Id'),('Channel','Global.Teams表示前回チャネル','=Topic.Teams表示チャネル'),('Snapshot','Global.Teams表示前回判定','=Topic.Teams今回判定')]:out.append(setv('setVariable_teamsDisplayCache'+suffix,var,expr))
 return out

def build():
 ops={'invokeFlowAction_caseSaveFieldAdvice':lambda n:[n]+display_steps()}
 def prompt(n):
  n['prompt']=n['prompt'].replace('{Topic.優先度判定結果}','{'+DISPLAY+'}')
 def activity(n):n['activity']=n['activity'].replace('{Topic.優先度判定結果}','{'+DISPLAY+'}')
 ops['question_priorityUpdate']=prompt
 for ident in ['sendActivity_priorityDone','sendActivity_priorityGiveUp']:ops[ident]=activity
 text=edit(SOURCE,ops);YAML.write_text(text);TEXT.write_bytes(YAML.read_bytes())
 (ROOT/'YAML全文.md').write_text('# 3-9 修正後YAML全文\n\n```yaml\n'+text.rstrip()+'\n```\n')
 before=SOURCE.read_text();(ROOT/'validation/変更差分.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),text.splitlines(True),fromfile='変更前_3-9.yaml',tofile='3-9_貼り替え用.yaml')))
 (ROOT/'validation/measures.json').write_text(json.dumps(measures(),ensure_ascii=False,indent=2)+'\n')
 print('Built one display-only topic from current uploaded YAML')
if __name__=='__main__':build()
