"""Merge the user's field concepts into existing prompts, before the output contract."""
from pathlib import Path
from restart_support import edit
ROOT=Path(__file__).resolve().parents[1]
SOURCE='field_concepts/01_調査遮断供給支障.md'

def apply(field):
    rules=(ROOT/SOURCE).read_text().rstrip()
    def guide(n):
        text=n['value'][2:-1].replace('""','"')
        marker='# 判定手順'
        assert text.count(marker)==1
        text=text.replace(marker,rules+'\n\n'+marker,1)
        n['value']='="'+text.replace('"','""')+'"'
    def prompt(n):
        # This expression also concatenates runtime inputs. Preserve those bindings.
        marker='# 今回の内部出力契約'
        assert n['value'].count(marker)==1
        n['value']=n['value'].replace(marker,rules.replace('"','""')+'\n\n'+marker,1)
    def answer(n):
        n['additionalInstructions']+='\n追加概念の現在の高条件を優先し、室内臭気・実反応等では要請と避難を両方高、EMERGENCYを高とする。遮断後の変化、配管範囲、機器・排ガス、道路流入、圧力・供給支障を対象ごとに照合する。P23は供給支障の必要な確認・調査をまとめ、途中なら対応済みにしない。情報不足の判定保留は中の暫定確認枠で根拠とCHECKに明示し、既知の高を下げない。添付の10章形式には変更しない。'
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer}))
