"""Merge the user's field concepts into existing prompts, before the output contract."""
from pathlib import Path
from restart_support import edit
from itemized_build import protocol,lit
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
        text=text.replace('原則として「中（条件確認が必要）」として不足情報を明示してください。','原則として「中（条件確認が必要）」として不足情報を明示してください。ただし消防警察・避難は通常の単独臭気のみの初報では低。情報不足だけで中に上げない。')
        a=text.index('【中：状況を継続監視し、悪化時は直ちに要請する】')
        b=text.index('【情報不足時に必要な項目だけ確認する】',a)
        text=text[:a]+"""【中：具体的な警戒兆候、または改善途上】
高条件には至らない具体的な警戒兆候が報告された場合、または高から改善して残留ガス・影響範囲の確認が残る場合。未報告・設備不明だけを中の根拠にしない。

【低：初報の通常の単独臭気、または安全確認後の再評価】
初報が通常の単独臭気だけで要請・避難を上げる具体的な危険兆候が報告されていない場合は低。危険なし・安全確認済みという意味ではなく、必要な確認・監視を続け、危険情報が入れば昇格する。
既に危険条件が判明していた場合は、確実な止漏、全影響範囲の継続改善と安全確認、拡大なし、避難等の必要性解消を確認してから低下させる。短い続報で以前の危険を忘れない。
未要請だから低、要請済みだから低とはしない。既にした要請の取消しを指示しない。高と判断した項目は高に表示する。

"""+text[b:]
        text=text.replace(marker,rules+'\n\n'+marker,1)
        n['value']='="'+text.replace('"','""')+'"'
    def prompt(n):
        # Read the guide once; do not inline the same concepts and E-rules again.
        n['value']='="緊急保安トピックとして、固定ガイドと報告された事実だけで再判定する。一般知識や未報告の危険を補わない。\n【ガイド】\n" & Topic.優先度ガイド取得結果 & "\n【初回の現場報告】\n" & Topic.初回入力 & "\n【追加報告・画像結果】\n" & Topic.追加情報履歴 & "\n最新の明示報告を優先する。以前のAIの優先度・状態は事実ではない。ユーザーの操作・設置・調査の実施事実を取り消さず、対象と効果・未調査範囲を分ける。\n履歴の写真有の実施措置は確認された範囲で対応済みとし、要確認項目は必要な次行動・確認文に反映する。画像を参照できない場合は見たふりをせず、写らないことだけで未実施にしない。初報の通常臭気だけならP11・P12低。具体的危険や既往の高はガイドの条件で判断する。\n'+protocol().replace('"','""')+'"'
    def answer(n):
        n['additionalInstructions']+='\n各措置固有の適用条件を現場事実と照合する。単独室の臭気・反応だけで上流遮断・要請・避難を高にしない。両方高の成立条件が確認できた時だけEMERGENCY高とする。実施状況不明は要確認とする。遮断後の変化、配管範囲、機器・排ガス、道路流入、圧力・供給支障を対象ごとに照合する。P23は供給支障の必要な確認・調査をまとめ、途中なら対応済みにしない。消防警察・避難は通常の単独臭気の初報なら低。具体的な警戒兆候で中、危険条件で高。情報不足だけで中に上げず、既知の高は改善条件の確認まで保持する。添付の10章形式には変更しない。'
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer}))
