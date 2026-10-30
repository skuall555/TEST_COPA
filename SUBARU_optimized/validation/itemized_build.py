"""Item-level scalar protocol: priority drives placement; no Table/Boolean topic variables."""
from restart_support import setv,cg,edit
MEASURES=[
 ('P01','火気使用禁止の徹底'),('P02','電気スイッチ等の操作禁止'),('P03','火気厳禁表示シート'),('P04','ポケット警報器等の設置'),('P05','流入ガス・滞留ガスの検知器調査'),('P06','換気'),('P07','メーターガス栓閉止'),('P08','分岐バルブ・引込管ガス遮断装置等'),('P09','消火器設置'),('P10','周辺住戸・建物調査'),('P11','消防・警察への要請'),('P12','避難誘導'),('P13','保安柵または同等措置'),('P14','高濃度ガス識別検知器による濃度確認'),('P15','進入禁止措置'),('P16','保安範囲の拡大または再設置'),('P17','マンホール蓋開放・換気'),('P18','救護・専門対応'),('P19','空気呼吸器等の確認'),('P20','未確認範囲の追加検知器調査'),('P21','周辺調査の拡大・再調査'),('P22','追加対象の供給遮断'),('P23','圧力・供給支障の確認と調査')]
STRING_VARS=['優先度表示原文','優先度表示組立','優先度表示検証','優先度表示区分','判定残余','判定事実','判定次行動','判定確認文','判定連動','判定連動理由','判定高欄','判定中欄','判定低欄','判定未完了','判定優先度','判定状態','判定根拠','判定表示行','判定要請優先度','判定要請状態','判定避難状態']
def q(s):return '"'+s.replace('"','""')+'"'
def lit(s):return '='+q(s)
def get(tag):return 'First(Split(Last(Split(Topic.優先度表示原文, '+q('[['+tag+']]')+')).Value, '+q('[[/'+tag+']]')+')).Value'
def unique(tag):return 'And(CountRows(Split(Topic.優先度表示原文, '+q('[['+tag+']]')+')) = 2, CountRows(Split(Topic.優先度表示原文, '+q('[[/'+tag+']]')+')) = 2)'
def check(ident,expr):return setv(ident,'Topic.優先度表示検証','=If(And(Topic.優先度表示検証 = "合格", '+expr+'), "合格", "不合格")')
def remove(tag):return setv('setVariable_itemRemove'+tag,'Topic.判定残余','=Substitute(Topic.判定残余, '+q('[['+tag+']]')+' & Topic.優先度表示区分 & '+q('[[/'+tag+']]')+', "")')
def protocol():
    rows='\n'.join('[['+code+']]'+('高|未実施|根拠となる対象・事実・条件'if i<13 else '対象外|対象外|今回必要でない理由')+'[[/'+code+']]'for i,(code,_)in enumerate(MEASURES))
    names='\n'.join(code+'：'+name+('（必要時のみ。不要なら対象外）'if i>=13 else '')for i,(code,name)in enumerate(MEASURES))
    return '''# 今回の内部出力契約（従来の見出し指定より優先）
ユーザー用の高・中・低の見出しをあなたが作文しない。措置ごとに一つの優先度・実施状況・根拠を返し、YAMLがその優先度だけを使って表示欄を決める。
以下のブロックを各1回、順番どおり出力する。コードブロック、前置き、見出し、追加マーカーは禁止。本文には区切り文字の半角縦棒|や[[、]]、【、】を含めない。行内の情報を勝手に省略せず、入力事実以外は作らない。
[[FACTS]]確認できた事実を└から始まる行で記載[[/FACTS]]
[[EMERGENCY]]高または通常|E-01／E-02・現状の危険条件・再評価の根拠[[/EMERGENCY]]
'''+rows+'''
[[NEXT]]必要な次の行動を└から始まる行で記載[[/NEXT]]
[[CHECK]]判断に必要な情報と理由を、利用者への自然な文章で記載[[/CHECK]]

上の行は書式例であり、優先度・状態・根拠を今回の現場事実とガイドに応じた値に置き換える。優先度は高／中／低、状態は対応済み／未実施／要確認の一つずつ。P14〜P23だけは今回必要なければ対象外|対象外を許す。未知の設備や未確認の実施状況はないと決めつけない。根拠は必須。根拠に「高と判断」等と書く場合は優先度も高にする。
EMERGENCYはE-01／E-02・広範囲拡散・遮断排出不能などにより避難と消防警察の両方を高とする場合に高、それ以外を通常とする。高ならYAMLがP11・P12を高に統一する。通常は両措置が不要・低という意味ではなく、それぞれのガイド条件で判断する。
措置コードと名称：
'''+names+'''

# 実施済みと範囲・効果
排水口や玄関隙間等の検知結果があれば、その場所のP05は対応済み。全域が未確認という理由で既に行った調査を未実施へ戻さない。残る調査はP20に対象場所を明記して別に示す。P10も実際の調査範囲だけを対応済みとし、必要な追加範囲はP21へ示す。メーター閉止済みは対象を明記してP07で保持し、別の部屋・設備への追加遮断はP22で示す。
画像に写っていないことは未実施の証拠ではない。明確なユーザー報告を画像の不鮮明さで取り消さず、実施状況不明なら要確認と明示する。設置済みの写真や報告の対象範囲を勝手に他室へ広げない。
屋外から臭気が入るため窓を閉めたという報告は、換気を試みた事実と流入防止の閉止措置を保持する。単なる未実施に書き戻さず、漏えい源・流入方向を照合し、その窓からの換気継続を無条件に勧めない。未入室の別室の換気不能と、通報宅で実施した窓操作は別の対象として扱う。

# CHECKは説明文にする
質問の羅列や「建物種別は何か」の箇条書きにしない。①どの情報が未確認か、②その情報でどの判断が変わるか、③危険条件が成立する場合に何が高になるか、④何を教えてほしいかを、既報を繰り返さず必要な点だけ自然な文章で伝える。
既に高と判断できる事項を判断不能に戻さず「この状況から避難と要請は高です。追加回答を待たず提示した措置を進めてください。上流遮断の方法を確認するため…を教えてください」のように、結論と残る確認を分ける。判断に必要な報告が十分なら「優先度を判断するための情報は確認できています。追加の報告を待たず、提示した未完了の高優先度の作業を進めてください」と案内する。作業自体が未完了なのに安全確認完了としない。
'''
def validator():
    out=[setv('setVariable_priorityFormatRaw','Topic.優先度表示原文','=Topic.優先度判定結果')]
    for index,var in enumerate(STRING_VARS):
        if var!='優先度表示原文':out.append(setv('setVariable_itemInit'+str(index).zfill(2),'Topic.'+var,lit('合格'if var=='優先度表示検証'else 'なし'if var=='判定未完了'else '')))
    out.append(setv('setVariable_itemRemainingInit','Topic.判定残余','=Topic.優先度表示原文'))
    out.append(check('setVariable_priorityFormatEnvelope','And(StartsWith(Trim(Topic.優先度表示原文), "[[FACTS]]"), EndsWith(Trim(Topic.優先度表示原文), "[[/CHECK]]"))'))
    for tag,var in [('FACTS','判定事実'),('EMERGENCY','判定連動'),('NEXT','判定次行動'),('CHECK','判定確認文')]:
        out += [setv('setVariable_itemSection'+tag,'Topic.優先度表示区分','='+get(tag)),check('setVariable_itemUnique'+tag,unique(tag)),remove(tag)]
        if tag=='EMERGENCY':
            out += [setv('setVariable_itemEmergency','Topic.判定連動','=Trim(First(Split(Topic.優先度表示区分, "|")).Value)'),setv('setVariable_itemEmergencyReason','Topic.判定連動理由','=Trim(Last(Split(Topic.優先度表示区分, "|")).Value)'),check('setVariable_itemEmergencyValid','And(CountRows(Split(Topic.優先度表示区分, "|")) = 2, Or(Topic.判定連動 = "高", Topic.判定連動 = "通常"), Len(Topic.判定連動理由) > 0, Not("[[" in Topic.判定連動理由), Not("【" in Topic.判定連動理由))')]
        else:
            out.append(setv('setVariable_itemBody'+tag,'Topic.'+var,'=Trim(Topic.優先度表示区分)'))
            shape='StartsWith(Topic.'+var+', "└")'if tag!='CHECK'else 'And(Topic.'+var+' <> "なし", Not(StartsWith(Topic.'+var+', "└")), Not(StartsWith(Topic.'+var+', "・")), Not(StartsWith(Topic.'+var+', "-")))'
            out.append(check('setVariable_itemBodyValid'+tag,'And(Len(Topic.'+var+') > 0, Not("[[" in Topic.'+var+'), Not("【" in Topic.'+var+'), '+shape+')'))
    for i,(code,name)in enumerate(MEASURES):
        out += [setv('setVariable_itemRaw'+code,'Topic.優先度表示区分','='+get(code)),remove(code),
                setv('setVariable_itemPriority'+code,'Topic.判定優先度','=Trim(First(Split(Topic.優先度表示区分, "|")).Value)'),
                setv('setVariable_itemStatus'+code,'Topic.判定状態','=Trim(Last(FirstN(Split(Topic.優先度表示区分, "|"), 2)).Value)'),
                setv('setVariable_itemReason'+code,'Topic.判定根拠','=Trim(Last(Split(Topic.優先度表示区分, "|")).Value)')]
        valid='And(Or(Topic.判定優先度 = "高", Topic.判定優先度 = "中", Topic.判定優先度 = "低"), Or(Topic.判定状態 = "対応済み", Topic.判定状態 = "未実施", Topic.判定状態 = "要確認"))'
        if i>=13:valid='Or('+valid+', And(Topic.判定優先度 = "対象外", Topic.判定状態 = "対象外"))'
        out.append(check('setVariable_itemValid'+code,'And('+unique(code)+', CountRows(Split(Topic.優先度表示区分, "|")) = 3, '+valid+', Len(Topic.判定根拠) > 0, Not("[[" in Topic.判定根拠), Not("【" in Topic.判定根拠))'))
        if code in ('P11','P12'):
            out += [setv('setVariable_itemLink'+code,'Topic.判定優先度','=If(Topic.判定連動 = "高", "高", Topic.判定優先度)'),setv('setVariable_itemLinkReason'+code,'Topic.判定根拠','=If(Topic.判定連動 = "高", Topic.判定連動理由, Topic.判定根拠)')]
            out.append(setv('setVariable_itemStoreStatus'+code,'Topic.判定要請状態'if code=='P11'else 'Topic.判定避難状態','=Topic.判定状態'))
            if code=='P11':out.append(setv('setVariable_itemStoreRequestPriority','Topic.判定要請優先度','=Topic.判定優先度'))
        out.append(setv('setVariable_itemLine'+code,'Topic.判定表示行','='+q('└'+name+'：')+' & Topic.判定状態 & "　根拠：" & Topic.判定根拠'))
        for priority,bucket,suffix in [('高','判定高欄','High'),('中','判定中欄','Medium'),('低','判定低欄','Low')]:out.append(setv('setVariable_itemBucket'+code+suffix,'Topic.'+bucket,'=If(Topic.判定優先度 = '+q(priority)+', Topic.'+bucket+' & If(IsBlank(Topic.'+bucket+'), "", Char(10)) & Topic.判定表示行, Topic.'+bucket+')'))
        out.append(setv('setVariable_itemIncomplete'+code,'Topic.判定未完了','=If(And(Topic.判定優先度 = "高", Topic.判定状態 <> "対応済み"), "あり", Topic.判定未完了)'))
    out.append(check('setVariable_itemNoRemainder','IsBlank(Trim(Topic.判定残余))'))
    out.append(setv('setVariable_itemUrgentEvacuation','Topic.判定次行動','=If(And(Topic.判定連動 = "高", Topic.判定避難状態 <> "対応済み"), "└避難誘導の実施状況を確認し、未対応の範囲は安全な場所から関係者と連携して優先的に対応してください。" & Char(10) & Topic.判定次行動, Topic.判定次行動)'))
    out.append(setv('setVariable_itemUrgentRequest','Topic.判定次行動','=If(And(Topic.判定要請優先度 = "高", Topic.判定要請状態 <> "対応済み"), "└消防・警察への出動要請の実施状況を確認し、未要請なら追加回答を待たず要請を優先してください。" & Char(10) & Topic.判定次行動, Topic.判定次行動)'))
    expr='Topic.判定事実'
    expr=q('【確認できた事実】\n')+' & '+expr
    for label,var in [('初動措置　優先度：高','判定高欄'),('初動措置　優先度：中','判定中欄'),('初動措置　優先度：低','判定低欄')]:expr+=' & '+q('\n\n【'+label+'】\n')+' & If(IsBlank(Topic.'+var+'), "└なし", Topic.'+var+')'
    expr+=' & '+q('\n\n【高優先度の完了状況】\n')+' & If(Topic.判定未完了 = "あり", "└未完了あり", "└全て対応済み") & '+q('\n\n【ネクストアクション】\n')+' & Topic.判定次行動 & '+q('\n\n【確認したいこと】\n')+' & Topic.判定確認文'
    out.append(setv('setVariable_itemRender','Topic.優先度表示組立','='+expr))
    out.append(cg('conditionGroup_priorityFormatRetry','=And(Topic.優先度表示検証 <> "合格", Topic.優先度様式再試行回数 < 1)',[setv('setVariable_priorityFormatRetryIncrement','Topic.優先度様式再試行回数','=Topic.優先度様式再試行回数 + 1'),{'kind':'GotoAction','id':'goto_priorityFormatRetry','actionId':'answer_priority'}]))
    out.append(cg('conditionGroup_priorityFormatAccepted','=Topic.優先度表示検証 = "合格"',[setv('setVariable_priorityFormatUseAssembled','Topic.優先度判定結果','=Topic.優先度表示組立')]))
    return out
def apply(field):
    contract=protocol()
    def guide(n):
        s=n['value'][2:-1].replace('""','"')
        a=s.index('# 出力フォーマット');b=s.index('# 禁止事項',a)
        s=s[:a]+'# ユーザーへの表示\n高・中・低の見出しと完了欄はYAMLが組み立てる。モデルは末尾の内部出力契約に従って返す。\n\n'+s[b:]
        n['value']=lit(s)
    def prompt(n):
        # Earlier rules remain business guidance; this explicit contract controls only internal output.
        s=n['value']
        a=s.index('# 出力フォーマット（このフォーマット以外は出力しないこと）');b=s.index('# 今回の消防・警察ルールの適用',a)
        s=s[:a]+s[b:]
        a=s.index('# 出力様式の厳守');s=s[:a]+'"'
        n['value']=s[:-1]+'\n'+contract.replace('"','""')+'"'
    def answer(n):
        n['userInput']='=Topic.優先度判定プロンプト & If(Topic.優先度様式再試行回数 > 0, Char(10) & "前回は内部ブロック形式が不正でした。指定コードの優先度・状態・根拠を正しい内部形式で生成し直してください。", "")'
        n['additionalInstructions']='固定ガイドと現場事実だけを根拠にする。末尾の内部出力契約に厳密に従い、ユーザー用見出しは出力しない。各措置の優先度は一つだけ、状態・根拠とは別に返す。CHECKは理由と判断への影響が伝わる文章にする。実施済みの範囲と追加作業、換気を試みた事実と流入防止の閉窓を区別する。'
    def limit(n):
        n['conditions'][0]['actions'].append({'kind':'EndDialog','id':'endDialog_priorityRetryLimit','clearTopicQueue':True})
    field.write_text(edit(field,{'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':answer,'conditionGroup_priorityRetryLimit':limit}))
