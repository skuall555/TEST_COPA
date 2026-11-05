"""Route explicit field reports BEFORE the AI purpose classifier.
Document questions and ambiguous requests retain all existing manual flows.
"""
from pathlib import Path
import difflib,yaml
from yaml_edit import edit,setv,cg
ROOT=Path(__file__).resolve().parents[1]
REPORT=['ガス臭','ガスくさ','ガスが臭','ガスが漏','ガス漏れ','ガス漏えい','漏洩','漏えい','臭気','異臭','検知器反応','検知器が反応','検知反応','ガスを検知','ガスが検知','lel','警報器が鳴','警報器鳴動','警報が鳴','鳴り止まない','ガスが噴','ガスを止め','ガスが止ま','供給を止められ']
DOCUMENT=['マニュアル','基準','規定','要領','手順','文書','規程','ルール','条項','条文','規則']
THEORY=['とは','仕組み','原理','意味','定義','教科書','用語','場合','とき','時の','時は']
def any_word(words):return 'Or('+', '.join('"'+w+'" in Topic.入口入力小文字'for w in words)+')'
def guard():return '=And(Topic.目的再試行回数 = 0, '+any_word(REPORT)+', Not('+any_word(DOCUMENT)+'), Not('+any_word(THEORY)+'))'
def build():
 p=ROOT/'source/変更前_1.yaml'
 def early(n):return [n,setv('setVariable_fieldFirstNormalize','Topic.入口入力小文字','=Lower(Substitute(Topic.初回入力, "　", " "))'),cg('conditionGroup_fieldBeforePurposeAI',guard(),[setv('setVariable_fieldFirstPurpose','Topic.目的分野','="現場対応アドバイス"'),setv('setVariable_fieldFirstFolder','Topic.対象フォルダ','="09_緊急保安_共通"'),{'kind':'SendActivity','id':'sendActivity_fieldFirstReceived','activity':'現場報告を受け付けました。初動措置を判定します。'},{'kind':'GotoAction','id':'goto_fieldBeforePurposeAI','actionId':'64VMOA'}])]
 def version(n):n['value']='="entry-field-first-20261105-v1"'
 s=edit(p,{'setVariable_purposeDetect':early,'setVariable_buildVersion':version})
 for ext in ['yaml','txt']:(ROOT/('1_貼り替え用.'+ext)).write_text(s)
 (ROOT/'YAML全文.md').write_text('# 入口トピック修正後全文\n\n```yaml\n'+s.rstrip()+'\n```\n')
 (ROOT/'validation/変更差分.diff').write_text(''.join(difflib.unified_diff(p.read_text().splitlines(True),s.splitlines(True),fromfile='変更前_1.yaml',tofile='1_貼り替え用.yaml')))
if __name__=='__main__':build()
