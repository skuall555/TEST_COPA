"""Use the readable field display on every channel, retaining the save text."""
from pathlib import Path
import difflib,re,yaml
from yaml_edit import edit,nodes
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/変更前_3-9.yaml'
YAML=ROOT/'3-9_貼り替え用.yaml'
DISPLAY='Topic.Teams現場表示'
def index(data):return {n['id']:n for n in nodes(data)if'id'in n and'kind'in n}
def display_steps():return [n for n in index(yaml.safe_load(YAML.read_text())).values()if n['id'].startswith('setVariable_teamsDisplay')]
def measures():
 return [(m[1],re.search(r'└([^"：]+)：',n['value'])[1])for n in index(yaml.safe_load(YAML.read_text())).values()if(m:=re.fullmatch('setVariable_itemLine(P[0-9]{2})',n['id']))]
OLD='{If(Topic.Teams表示チャネル = "msteams", Topic.Teams現場表示, Topic.優先度判定結果)}'
def build():
 def template(n):
  key='prompt'if n['kind']=='Question'else'activity';assert OLD in n[key];n[key]=n[key].replace(OLD,'{Topic.Teams現場表示}')
 def case_label(n):
  assert n['value'].startswith('="📍 現場アドバイス"');n['value']=n['value'].replace('="📍 現場アドバイス"','="📍 現場アドバイス" & If(IsBlank(Topic.Teams現在案件ID), "", "｜案件 " & Topic.Teams現在案件ID)',1)
 p=ROOT/'source/変更前_3-9.yaml';s=edit(p,{'question_priorityUpdate':template,'sendActivity_priorityDone':template,'sendActivity_priorityGiveUp':template,'setVariable_teamsDisplayRender':case_label})
 for suffix in ['yaml','txt']:(ROOT/('3-9_貼り替え用.'+suffix)).write_text(s)
 (ROOT/'YAML全文.md').write_text('# 修正後YAML全文\n\n```yaml\n'+s.rstrip()+'\n```\n')
 (ROOT/'validation/変更差分.diff').write_text(''.join(difflib.unified_diff(p.read_text().splitlines(True),s.splitlines(True),fromfile='変更前_3-9.yaml',tofile='3-9_貼り替え用.yaml')))
if __name__=='__main__':build()
