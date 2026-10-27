"""Bounded scalar format validation and explicit linked emergency rules."""
from restart_support import edit,setv,cg
HEADINGS=['確認できた事実','初動措置　優先度：高','初動措置　優先度：中','初動措置　優先度：低','高優先度の完了状況','ネクストアクション','確認したいこと']
EMERGENCY='''# 避難誘導と消防・警察要請の連動条件（今回の最優先補足）
以下のE-01、E-02のいずれかが現在の報告と累積した現場事実から成立すれば、避難誘導と消防・警察への出動要請の両方を高とする。事故・人身被害の既発生を待たない。未要請・未避難という実施状況、建物種別やバルブ有無の未確認を優先度を下げる理由にしない。
E-01：入室不能または換気不能の部屋・住戸・空間で、ガス濃度・検知反応がある、またはガス警報器が鳴り続ける。濃度と警報の両方が報告されれば当然該当するが、両方の報告が揃うまで待たない。不在・施錠・立入不能等で室内確認や換気ができず、ドアポスト・開口部で検知され警報が継続する事例を含む。「喚起できない」も文脈が換気なら換気不能の意味として読む。LEL3％やLEL1％という開口部の値だけで危険を下げず、室内全体の濃度と同一視しない。LEL10％以上を追加条件にしない。
E-02：いくつかの部屋・家・施設・地点など複数の場所で検知器反応があり、かつ（a）臭気または高濃度がある、（b）排水口・排水ます・側溝・目地・貫通部等から不特定多数の需要家宅内への流入可能性が報告・確認される、（c）3つ以上の家等で反応がありバルブがなく有効に遮断できない、のいずれかに該当する。これらの組合せで両方を高とする。既存の「複数地点で検知器・警報器反応なら要請高」「遮断・排出不能なら避難・要請高」等のより厳しい条件も維持し、3か所揃うまで他の高を保留しない。「他の家で一台の警報器が鳴った」だけで警報器の台数や鳴動住戸を増やさない。
明示された広範囲拡散・複数住戸への影響拡大も、現場だけで安全確保できない危険として避難誘導と要請を高とする。過去の噴出・拡散と現在の継続は分け、改善後の再評価は既存の確実な止漏・継続低下・影響範囲全体の安全確認条件を適用する。
両方が高なら、既存の「初動措置　優先度：高」欄へ別々に列挙し、未実施ならネクストアクションの先頭に要請と避難・立入防止を示す。要請済み・避難済みの明確な報告は対応済みとして保持する。実施済みでも危険が残れば優先度と必要な追加措置を別に評価する。
避難の範囲は現場の影響範囲と社内基準で確認し、未報告の「周辺数軒」「半径何m」や一律の範囲を創作しない。入室できない部屋に入って換気・避難させる案内や、危険区域での換気扇・電気スイッチ操作は勧めない。安全な場所から関係者と連携する。既に換気不能・不在と報告済みなら同じ可否質問を繰り返さず、必要な支援・止漏・影響範囲等の未確認事項だけを示す。
警報を他の家で聞いたという報告だけで「周辺住戸・建物調査は全て対応済み」にしない。実際に確認した場所・方法・結果の範囲だけを対応済みとし、範囲拡大時の追加調査を高・未完了で示す。表示シート設置だけから火気使用禁止の周知徹底まで対応済みと推測しない。

'''
FORMAT='''# 出力様式の厳守
危険が増しても見出し・順序・行書式を変更しない。「危険度判定」「直近の対応措置」「最優先」「次の行動」「確認事項」という別様式や絵文字を作らない。
指定の7見出しを各1回ずつ出力し、各本文行は必ず└から始める。一つの項目は一行にし、本文内に追加の【見出し】を作らない。該当項目がない本文は└なしとする。高・中・低の措置行は└措置名：対応済み／未実施／要確認のいずれか一つを実際の状態に応じて記載し、その後に根拠・必要な確認を続ける。「措置名：高」等の優先度を実施状況の位置に書かない。高と判断した措置を中・低へ入れない。
完了状況の本文は└全て対応済みまたは└未完了ありの一行だけ。全て対応済みという語はこの完了欄以外に書かない。出力前に各措置の判定と配置を照合する。最新の原文と報告履歴から再判定し、前回のAI出力の配置ミスを引き継がない。
'''
CONTINUITY='''
## 現場続報の受け取りと回答権限（今回の補足）
実行中トピックの質問待ちを最優先する。「広範囲に拡散している」「まだ入れない」「換気できない」「鳴り止まない」「3軒で反応」「バルブがない」等の短い現場続報は、目的を再選択する新規依頼にせず、質問中の緊急保安トピックへ渡す。ガス等の語が省略されても、会話文脈の現場情報として扱う。
緊急保安の追加情報待ちでは、添付画像は既存の画像割り込みへ、それ以外の続報は元の質問へ返す。修理方法・目的変更は既存トピック内の分岐が処理する。親エージェントは危険度、優先度、避難範囲、初動措置、別様式の回答を生成しない。トピックの出力を要約・装飾・補足しない。検索不成立時も現場対応の独自回答で埋め合わせない。
指定の見出しや定型文が出なくなったときは、自由回答へ切り替えずトピックの処理に任せる。内部のexplanation_of_tool_call等を業務回答として表示しない。これらは指示であり、環境の生成オーケストレーション・システムトピック設定そのものを変更するものではない。
'''
def q(s):return '"'+s.replace('"','""')+'"'
def lit(s):return '='+q(s)
def extract(index):
    head='【'+HEADINGS[index]+'】'
    if index==6:return 'Trim(Last(Split(Topic.優先度表示原文, '+q(head)+')).Value)'
    return 'Trim(First(Split(Last(Split(Topic.優先度表示原文, '+q(head)+')).Value, '+q('【'+HEADINGS[index+1]+'】')+')).Value)'
def validator():
    result=[setv('setVariable_priorityFormatRaw','Topic.優先度表示原文','=Topic.優先度判定結果'),setv('setVariable_priorityFormatAssembleInit','Topic.優先度表示組立','=""')]
    checks=['StartsWith(Trim(Topic.優先度表示原文), '+q('【'+HEADINGS[0]+'】')+')']+['CountRows(Split(Topic.優先度表示原文, '+q('【'+h+'】')+')) = 2'for h in HEADINGS]
    result.append(setv('setVariable_priorityFormatEnvelope','Topic.優先度表示検証','=If(And('+', '.join(checks)+'), "合格", "不合格")'))
    for i,head in enumerate(HEADINGS):
        section='Topic.優先度表示区分'
        if i==4:shape='Or('+section+' = "└全て対応済み", '+section+' = "└未完了あり")'
        else:
            line=r'└[^\r\n]+'if i not in (1,2,3)else r'(└なし|└[^：\r\n]+：(対応済み|未実施|要確認)[^\r\n]*)'
            shape='IsMatch('+section+', '+q(line+r'(\r?\n[ \t]*'+line+r')*')+', MatchOptions.Complete)'
        result.extend([
            setv('setVariable_priorityFormatSection'+str(i),'Topic.優先度表示区分','='+extract(i)),
            setv('setVariable_priorityFormatCheck'+str(i),'Topic.優先度表示検証','=If(And(Topic.優先度表示検証 = "合格", Not("【" in '+section+'), '+shape+'), "合格", "不合格")'),
            setv('setVariable_priorityFormatAppend'+str(i),'Topic.優先度表示組立','=Topic.優先度表示組立 & '+q(('\n\n'if i else '')+'【'+head+'】\n')+' & '+section),
        ])
    retry=[setv('setVariable_priorityFormatRetryIncrement','Topic.優先度様式再試行回数','=Topic.優先度様式再試行回数 + 1'),{'kind':'GotoAction','id':'goto_priorityFormatRetry','actionId':'answer_priority'}]
    result.append(cg('conditionGroup_priorityFormatRetry','=And(Topic.優先度表示検証 <> "合格", Topic.優先度様式再試行回数 < 1)',retry))
    result.append(cg('conditionGroup_priorityFormatAccepted','=Topic.優先度表示検証 = "合格"',[setv('setVariable_priorityFormatUseAssembled','Topic.優先度判定結果','=Topic.優先度表示組立')]))
    return result
def apply(field,instructions):
    def guide(n):
        s=n['value'][2:-1].replace('""','"')
        s=s.replace('# 避難誘導\n','# 避難誘導\n\n今回のE-01／E-02および明示された広範囲拡散の場合も高。人身被害の既発生を必要条件にしない。\n',1)
        s=s.replace('# 判定手順',EMERGENCY+'# 判定手順',1)
        n['value']=lit(s)
    def prompt(n):
        n['value']=n['value'][:-1]+'\n'+EMERGENCY.replace('"','""')+'\n'+FORMAT.replace('"','""')+'"'
        return [n,setv('setVariable_priorityFormatRetryInit','Topic.優先度様式再試行回数','=0')]
    def answer(n):
        n['userInput']='=Topic.優先度判定プロンプト & If(Topic.優先度様式再試行回数 > 0, Char(10) & "【様式の再生成】直前の回答は見出し・行・実施状況・完了欄の様式検査に不合格でした。同じ現場事実を再評価し、指定の7見出し・各行の└・措置の実施状況を厳守して回答を新しく生成し直してください。", "")'
        n['additionalInstructions']+='\n'+FORMAT
        return [n]+validator()
    def failed(n):
        n['activity']='優先度回答の生成結果が空、または指定の出力様式を確認できなかったため、未検証の業務回答の送信を停止しました。報告履歴と実施済み報告を未実施へ変更したものではありません。現場の安全対応は止めず、社内の連絡・緊急対応手順に従ってください。'
    field.write_text(edit(field,{
        'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer,
        'conditionGroup_prioritySucceeded':lambda n:n['conditions'][0].update(condition='=Topic.優先度表示検証 = "合格"'),
        'conditionGroup_priorityLoopNeeded':lambda n:n['conditions'][0].update(condition='='+extract(4).replace('Topic.優先度表示原文','Topic.優先度判定結果')+' <> "└全て対応済み"'),
        'sendActivity_priorityFailed':failed,
    }))
    instructions.write_text(instructions.read_text()+CONTINUITY)
