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
        # Retire incompatible old status instructions instead of stacking an override.
        replacements={
            '既存の高欄の書式では「未実施（設置報告なし・要確認）」として、実際に未設置であるとの事実を作らない。':'設置報告がない場合の実施状況は「要確認」とする。',
            '実施したとの情報がないものは「未実施」とする。':'実施したとの情報がないものは「要確認」とする。未実施は、まだ実施していないとの明確な報告がある場合に限る。',
            '対応済みか未実施かを必ず明示する。':'対応済み／未実施／要確認のいずれかを、報告された実施状況に応じて明示する。',
            '高優先度項目が1つでも未実施の場合、':'高優先度項目が1つでも未実施または要確認の場合、',
        }
        for before,after in replacements.items():
            assert text.count(before)==1,before
            text=text.replace(before,after)
        text=text.replace(marker,rules+'\n\n'+marker,1)
        n['value']='="'+text.replace('"','""')+'"'
    def prompt(n):
        # This expression also concatenates runtime inputs. Preserve those bindings.
        marker='# 今回の内部出力契約'
        assert n['value'].count(marker)==1
        n['value']=n['value'].replace('実施済みと確認できないものは「未実施」として扱う。未確認を実施済みにしない。','未実施との明確な報告があれば未実施、実施報告がなく不明なら要確認とする。未確認を対応済みとも未実施とも断定しない。')
        n['value']=n['value'].replace(marker,rules.replace('"','""')+'\n\n'+marker,1)
    def answer(n):
        n['additionalInstructions']+='\n各措置固有の適用条件を現場事実と照合する。単独室の臭気・反応だけで上流遮断・要請・避難を高にしない。両方高の成立条件が確認できた時だけEMERGENCY高とする。実施状況不明は要確認とする。遮断後の変化、配管範囲、機器・排ガス、道路流入、圧力・供給支障を対象ごとに照合する。P23は供給支障の必要な確認・調査をまとめ、途中なら対応済みにしない。情報不足の判定保留は中の暫定確認枠で根拠とCHECKに明示し、既知の高を下げない。添付の10章形式には変更しない。'
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer}))
