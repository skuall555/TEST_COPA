"""Render priority/status/effect separately from one structured model result."""
SCHEMA = r"""# 実施状態と効果の独立管理（旧出力規則より優先）
この呼出しは内部データ生成。前述の人向け見出し形式はここでは出力しない。後段が表示を組み立てる。AI呼出しは増やさない。
各措置について、対象場所／設備、優先度、操作の実施状況、効果を独立して記録する。
・優先度は危険条件で決める。未実施・未要請だから低、実施済みだから低、という分類は禁止。
・明示された実施報告は実施済み。効果が出ていないことを理由に未実施へ戻さない。
・例『警報器が鳴っている部屋のメーターガス栓を閉めたが濃度変わらず、警報も鳴りやまない』は、その部屋のメーターガス栓閉止＝実施済み／効果＝未解決。ガス漏れ停止済みではない。ネクストアクションは閉止済みの同じ栓を未実施としてやり直させず、遮断効果・流入元・上流側対応の確認を既存ガイドの範囲で示す。
・『消防・警察は要請していない』は実施状況＝未実施。継続警報とガス検知等があれば優先度＝高。高の根拠を書いた措置を低へ置くな。
・『ドアポストからLEL1％検知』はガス検知あり。LEL10％以上ではないが、継続する都市ガス警報器＋ガス検知による要請高の条件に濃度10％の閾値を追加しない。
・『到着時臭気なし』を、その後の別室の検知・警報継続が消えた根拠にしない。
・『ドアポストからLEL1％検知』は、そのドアポストで検知器調査・濃度測定を行った報告として扱う。他の場所の調査完了や全体調査完了とはしない。
・図面に分岐バルブがあるが現場で見つからない報告は、図面上の記載と現物未発見を区別し、存在を一切未報告とはしない。操作場所・操作可否を確認する。
・調査・濃度測定が実施された報告は、その測定箇所の実施済みとして保持。測定値不明、調査継続中、漏えい源未特定でも、既に行った調査を未実施へ戻さない。新しい対象箇所の追加調査は別の対象として記録する。
・対象を混同しない。別室・別戸・別設備は別行。同じ対象について最新の明示更新を採用する。ある部屋の閉止済みを全戸の閉止済みにしない。『その栓を再開した』『撤去した』等の最新報告がある場合は最新状態を反映し、過去の実施済みを永久固定しない。
・消防と警察は別行。消防だけ要請済みなら警察まで実施済みにしない。両方要請済みという明示なら両方を実施済みにする。
・実施済みの根拠は、利用者の実施報告、または画像トピックが採用した【写真有】行だけ。AIの以前の回答、＜要確認＞行、機器候補の存在、画像に写っていないことは実施根拠にならない。写真の設置場所が不明でも、別の明示された利用者の実施報告を消さない。
・未実施は『まだしていない』等の明示がある場合。実施報告が無いだけなら要確認。実施済みを再質問せず、効果が未解決・未確認なら効果について尋ねる。
・実施と効果の未解決は両立する。高の操作を実施しただけで、継続する危険が解消したことにしない。
・廃止MS-018は出力しない。ガイドにない操作手順を作らない。

# 内部出力形式（厳守）
以下の3ブロックだけ。コードフェンス・前置き禁止。区切りは半角|。各行の値に|、改行、ブロック記号を入れない。値なしは『なし』。事実は利用者報告と採用済み画像事実だけで整理する。
[[FACTS]]
└事実を1行ずつ
[[END_FACTS]]
[[RISK]]
継続警報|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
ガス検知|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
継続噴出|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
複数住戸影響|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
強臭等と遮断不能|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
その他要請高条件|あり／なし／不明|根拠となる入力の正確な部分引用、またはなし
[[END_RISK]]
[[MEASURES]]
措置名|対象場所・設備|高／中／低|実施済み／未実施／要確認|確認済み／未解決／未確認／対象外|報告／写真／なし|入力の実施根拠の正確な部分引用、またはなし|優先度と効果の根拠|次の対応、またはなし|確認質問、またはなし
[[END_MEASURES]]
RISKは6行を各1回。あり／なし／不明は1つだけを出す。『あり』は今も継続している明示事実だけで、過去・仮定・否定・疑問文を肯定にしない。現在のガス検知には報告された正のLEL測定も含む。『継続警報』は都市ガス警報器の継続鳴動。『その他要請高条件』は人身被害・火災・有効遮断不能等の既存の要請高条件。なしは明示的に否定された場合、不明は未報告・確認不足。ありの根拠引用は入力中に存在する文字列を使い、否定を切り落として反転しない。改善と新たな悪化は時系列・影響範囲を区別する。全域の改善が明示された後に古い危険を現在ありにしない。
MEASURESは1対象1行、10列。上記説明の選択肢をそのまま列挙しない。対象不明は『対象未特定』。同じ措置名と対象の重複禁止。全現場共通の基本高5項目、消防への要請、警察への要請を必ず含め、他はガイドに照らして該当する措置を漏らさない。メーターガス栓に言及があれば対象を分けて必ず含める。調査・濃度測定の実施報告も落とさない。
消火器の措置名は『消火器設置』とする。ガス検知ありなら固定ガイドに従い消火器設置は高。都市ガス警報器継続鳴動ならメーターガス栓閉止は高。事故発生前というだけで下げない。
消防・警察の措置名は正確に『消防への要請』『警察への要請』とする。メーターガス栓閉止は正確に『メーターガス栓閉止』とする。基本5項目の名称は『火気使用禁止の徹底』『電気スイッチ等の操作禁止』『火気厳禁表示シート設置』『ポケット警報器等の設置』『流入ガス・滞留ガスの検知器調査』。
実施済み行は6列目が報告または写真、7列目が入力に存在する正確な実施根拠引用で必須。写真の根拠引用は【写真有】を含む採用済み行。未実施／要確認では実施根拠はなしでよい。対象に対する完了報告の引用を使い、別対象の引用・一般的な『済み』だけの引用・未実施報告を実施済みの証拠にしない。
効果の『確認済み』は必要な効果・状態が確認された場合、『未解決』は効果なし・危険継続、『未確認』は効果不明。設置・周知・要請・調査の実施そのものを確認し、別途の効果判定が不要な行は『対象外』。閉止・換気で危険継続なら未解決。
実施済みかつ効果が確認済み／対象外なら次の対応と確認質問はなし。実施済みかつ効果未解決／未確認なら、実施したか再質問せず残る効果・対象の確認だけ。未実施の高措置と効果未解決の高措置を優先し、消防・警察の要請が高で未実施なら次の対応へ必ず入れる。
"""
RISKS=['継続警報','ガス検知','継続噴出','複数住戸影響','強臭等と遮断不能','その他要請高条件']
BASIC=['火気使用禁止の徹底','電気スイッチ等の操作禁止','火気厳禁表示シート設置','ポケット警報器等の設置','流入ガス・滞留ガスの検知器調査']

def apply(R,edit,setv,cg,nodes):
 p=R/'3-9-緊急保安業務エージェント_optimized.yaml'
 def f(k):return 'Trim(Last(FirstN(Split(Value, "|"), '+str(k)+')).Value)'
 def q(s):return '"'+s.replace('"','""')+'"'
 def oneof(expr,items):return 'Or('+', '.join(expr+' = '+q(s)for s in items)+')'
 fire=oneof(f(1),['消防への要請','警察への要請'])
 priority='If(And('+fire+', Topic.消防警察強制高), "高", '+f(3)+')'
 def prompt(n):
  # This node is a concatenated Power Fx string; append within its final literal.
  n['value']=n['value'][:-1]+'\n\n'+SCHEMA.replace('"','""')+'"'
  n['value']=n['value'].replace('全履歴を現場事実として再評価','全履歴を時系列で照合し、ユーザー報告と採用済み画像事実を再評価')
  n['value']=n['value'].replace('実施済みと確認できないものは「未実施」として扱う。未確認を実施済みにしない。','実施報告がないものは「要確認」、明示的な未実施報告があるものだけ「未実施」。実施済みと効果未解決を分ける。')
 def result(n):
  t='Topic.措置状態監査行';rt='Topic.現危険監査行'
  acts=[n,setv('setVariable_priorityRaw','Topic.優先度構造化結果','=Topic.優先度判定結果'),setv('setVariable_priorityEvidenceInput','Topic.措置状態根拠入力','=Topic.初回入力 & Char(10) & Topic.追加情報履歴')]
  markers=['[[FACTS]]','[[END_FACTS]]','[[RISK]]','[[END_RISK]]','[[MEASURES]]','[[END_MEASURES]]']
  checks=['StartsWith(Trim(Topic.優先度構造化結果), "[[FACTS]]")','EndsWith(Trim(Topic.優先度構造化結果), "[[END_MEASURES]]")']+['CountRows(Split(Topic.優先度構造化結果, '+q(m)+')) = 2'for m in markers]
  acts.append(setv('setVariable_priorityEnvelope','Topic.優先度構造妥当','=And('+', '.join(checks)+')'))
  for code,var,left,right in [('Facts','Topic.措置確認事実','[[FACTS]]','[[END_FACTS]]'),('Risk','Topic.現危険監査本文','[[RISK]]','[[END_RISK]]'),('Rows','Topic.措置状態監査本文','[[MEASURES]]','[[END_MEASURES]]')]:
   acts.append(setv('setVariable_priorityExtract'+code,var,'=Trim(First(Split(Last(Split(Topic.優先度構造化結果, '+q(left)+')).Value, '+q(right)+')).Value)'))
  acts +=[setv('setVariable_priorityRiskRows',rt,'=Filter(Split(Topic.現危険監査本文, Char(10)), Not(IsBlank(Trim(Value))))'),setv('setVariable_priorityRiskCount','Topic.現危険元件数','=CountRows('+rt+')'),setv('setVariable_priorityRiskColumns',rt,'=Filter('+rt+', CountRows(Split(Value, "|")) = 3)'),setv('setVariable_priorityRiskKeys',rt,'=Filter('+rt+', '+oneof(f(1),RISKS)+')'),setv('setVariable_priorityRiskValues',rt,'=Filter('+rt+', '+oneof(f(2),['あり','なし','不明'])+')'),setv('setVariable_priorityRiskProof',rt,'=Filter('+rt+', Or('+f(2)+' <> "あり", And('+f(3)+' <> "なし", '+f(3)+' <> "", '+f(3)+' in Topic.措置状態根拠入力)))')]
  acts.append(setv('setVariable_priorityRiskUnique','Topic.現危険妥当','=And(Topic.現危険元件数 = 6, CountRows('+rt+') = 6, '+', '.join('CountRows(Filter('+rt+', '+f(1)+' = '+q(s)+')) = 1'for s in RISKS)+')'))
  for code,name in [('Alarm','継続警報'),('Detected','ガス検知')]:
   acts.append(setv('setVariable_priorityRisk'+code,'Topic.現危険'+code,'=CountRows(Filter('+rt+', And('+f(1)+' = '+q(name)+', '+f(2)+' = "あり"))) = 1'))
  acts.append(setv('setVariable_priorityRiskPositive','Topic.現危険肯定行','=Filter('+rt+', '+f(2)+' = "あり")'))
  acts.append(setv('setVariable_priorityFireHigh','Topic.消防警察強制高','=Or(And(Topic.現危険Alarm, Topic.現危険Detected), CountRows(Filter(Topic.現危険肯定行, '+oneof(f(1),RISKS[2:])+')) > 0)'))
  acts +=[setv('setVariable_priorityMeasureRows',t,'=Filter(Split(Topic.措置状態監査本文, Char(10)), Not(IsBlank(Trim(Value))))'),setv('setVariable_priorityMeasureCount','Topic.措置状態元件数','=CountRows('+t+')'),setv('setVariable_priorityMeasureColumns',t,'=Filter('+t+', CountRows(Split(Value, "|")) = 10)')]
  for name,k,choices in [('Priority',3,['高','中','低']),('Status',4,['実施済み','未実施','要確認']),('Effect',5,['確認済み','未解決','未確認','対象外']),('Source',6,['報告','写真','なし'])]:
   acts.append(setv('setVariable_priorityMeasure'+name,t,'=Filter('+t+', '+oneof(f(k),choices)+')'))
  acts.append(setv('setVariable_priorityMeasureNonempty',t,'=Filter('+t+', And(Not(IsBlank('+f(1)+')), Not(IsBlank('+f(2)+'))))'))
  acts.append(setv('setVariable_priorityMeasureRetired',t,'=Filter('+t+', Not("ホワイトシート" in Value) && Not("MS-018" in Value))'))
  acts.append(setv('setVariable_priorityMeasureProof',t,'=Filter('+t+', Or('+f(4)+' <> "実施済み", And('+oneof(f(6),['報告','写真'])+', '+f(7)+' <> "なし", '+f(7)+' <> "", '+f(7)+' in Topic.措置状態根拠入力)))'))
  acts.append(setv('setVariable_priorityMeasurePhotoProof',t,'=Filter('+t+', Or('+f(6)+' <> "写真", "【写真有】" in '+f(7)+'))'))
  acts.append(setv('setVariable_priorityMeasureUnique','Topic.措置状態一意','=CountRows(Distinct('+t+', '+f(1)+' & "@" & '+f(2)+')) = CountRows('+t+')'))
  required=BASIC+['消防への要請','警察への要請']
  acts.append(setv('setVariable_priorityMeasureRequired','Topic.措置状態必須行','=And('+', '.join('CountRows(Filter('+t+', '+f(1)+' = '+q(s)+')) > 0'for s in required)+', Or(Not("メーターガス栓" in Topic.措置状態根拠入力), CountRows(Filter('+t+', '+f(1)+' = "メーターガス栓閉止")) > 0))'))
  acts.append(setv('setVariable_priorityDataValid','Topic.措置状態妥当','=And(Topic.優先度構造妥当, Topic.現危険妥当, Topic.措置状態一意, Topic.措置状態必須行, CountRows('+t+') = Topic.措置状態元件数, Not(IsBlank(Topic.措置確認事実)))'))
  # Basic five remain high independent of completion. Each target remains an independent row.
  basic=oneof(f(1),BASIC)
  active='Or('+f(4)+' <> "実施済み", '+f(5)+' = "未解決", '+f(5)+' = "未確認")'
  high='Topic.優先度高行'
  extinguisher='And('+f(1)+' = "消火器設置", Topic.現危険Detected)'
  meter='And('+f(1)+' = "メーターガス栓閉止", Topic.現危険Alarm)'
  good=[setv('setVariable_priorityHighRows',high,'=Filter('+t+', Or('+f(3)+' = "高", '+basic+', And('+fire+', Topic.消防警察強制高), '+extinguisher+', '+meter+'))')]
  for code,rank in [('Middle','中'),('Low','低')]:
   table='Topic.優先度'+code+'行'
   good +=[setv('setVariable_priority'+code+'Rows',table,'=Filter('+t+', '+f(3)+' = '+q(rank)+')'),setv('setVariable_priority'+code+'NotBasic',table,'=Filter('+table+', Not('+basic+'))'),setv('setVariable_priority'+code+'NotFire',table,'=Filter('+table+', Or(Not('+fire+'), Not(Topic.消防警察強制高)))')]
  for code in ['Middle','Low']:
   table='Topic.優先度'+code+'行'
   good +=[setv('setVariable_priority'+code+'NotExtinguisher',table,'=Filter('+table+', Not('+extinguisher+'))'),setv('setVariable_priority'+code+'NotMeter',table,'=Filter('+table+', Not('+meter+'))')]
  good +=[setv('setVariable_priorityPendingHigh','Topic.高優先度未完了行','=Filter('+high+', '+active+')'),setv('setVariable_priorityAllDone','Topic.高優先度完了','=And(CountRows(Topic.高優先度未完了行) = 0, CountRows('+high+') > 0)')]
  # Render from columns: status and effect can never select the priority heading.
  display='"└" & '+f(1)+' & "（" & '+f(2)+' & "）：" & '+f(4)+' & "　効果：" & '+f(5)+' & "　根拠：" & '+f(8)+' & If('+f(4)+' = "実施済み", "　実施根拠：" & '+f(7)+', "") & If(And('+fire+', Topic.消防警察強制高), "　現在の危険条件により要請は高。実施状況とは別に判定。", "")'
  for code,rank in [('High','高'),('Middle','中'),('Low','低')]:
   good.append(setv('setVariable_priorityRender'+code,'Topic.措置表示'+code,'=Concat('+({'High':high,'Middle':'Topic.優先度Middle行','Low':'Topic.優先度Low行'}[code])+', '+display+', Char(10))'))
  # Fire/police next actions are rendered first, without re-asking a known completed request.
  fire_next='If('+f(4)+' = "未実施", "└" & '+f(1)+' & "（" & '+f(2)+' & "）を優先して実施してください。", "└" & '+f(1)+' & "（" & '+f(2)+' & "）の実施状況を確認し、未実施なら優先して要請してください。")'
  good +=[setv('setVariable_priorityFirePendingRows','Topic.要請未完了行','=Filter(Topic.高優先度未完了行, '+fire+')'),setv('setVariable_priorityFireNotDoneRows','Topic.要請未完了行','=Filter(Topic.要請未完了行, '+f(4)+' <> "実施済み")'),setv('setVariable_priorityOtherPendingRows','Topic.他措置未完了行','=Filter(Topic.高優先度未完了行, Or(Not('+fire+'), '+f(4)+' = "実施済み"))')]
  good.append(setv('setVariable_priorityRenderFireNext','Topic.要請次対応','=Concat(Topic.要請未完了行, '+fire_next+', Char(10))'))
  good.append(setv('setVariable_priorityRenderNext','Topic.措置次対応','=Concat(Topic.他措置未完了行, If('+f(9)+' = "なし", "└" & '+f(1)+' & "（" & '+f(2)+' & "）：実施状況または未解決の効果を確認してください。", "└" & '+f(9)+'), Char(10))'))
  good.append(setv('setVariable_priorityRenderQuestions','Topic.措置確認質問','=Concat(Filter('+t+', And('+active+', '+f(10)+' <> "なし")), "└" & '+f(10)+', Char(10))'))
  final='="【確認できた事実】" & Char(10) & Topic.措置確認事実'
  for code,rank in [('High','高'),('Middle','中'),('Low','低')]:final+=' & Char(10) & "【初動措置　優先度：'+rank+'】" & Char(10) & If(IsBlank(Topic.措置表示'+code+'), "└該当なし", Topic.措置表示'+code+')'
  final+=' & Char(10) & "【高優先度の完了状況】" & Char(10) & If(Topic.高優先度完了, "└全て対応済み", "└未完了あり") & Char(10) & "【ネクストアクション】" & Char(10) & If(Topic.高優先度完了, "└高優先度の操作実施と必要な効果を確認しました。残る条件確認を継続してください。", Topic.要請次対応 & Char(10) & Topic.措置次対応) & Char(10) & "【確認したいこと】" & Char(10) & If(IsBlank(Topic.措置確認質問), "└なし", Topic.措置確認質問)'
  good.append(setv('setVariable_priorityRenderedResult','Topic.優先度判定結果',final))
  fallback='="【確認できた事実】" & Char(10) & "└ご報告の実施状況を確認しきれないため、完了判定を保留しています。実施済みのご報告を未実施へ変更しません。" & Char(10) & "【初動措置　優先度：高】" & Char(10) & If(And(Topic.現危険妥当, Topic.消防警察強制高), "└消防・警察への要請：高　実施状況：要確認　根拠：現在の危険条件が確認されています。", "└判定保留") & Char(10) & "【初動措置　優先度：中】" & Char(10) & "└判定保留" & Char(10) & "【初動措置　優先度：低】" & Char(10) & "└判定保留" & Char(10) & "【高優先度の完了状況】" & Char(10) & "└未完了あり" & Char(10) & "【ネクストアクション】" & Char(10) & If(And(Topic.現危険妥当, Topic.消防警察強制高), "└未要請であれば消防・警察への要請を優先してください。", "└未解決の状況と、実施した措置の効果を確認してください。") & Char(10) & "【確認したいこと】" & Char(10) & "└対象の部屋・設備、実施した操作、その後の濃度・警報の変化を補足してください。"'
  bad=[setv('setVariable_priorityInvalidDone','Topic.高優先度完了','=false'),setv('setVariable_priorityInvalidResult','Topic.優先度判定結果',fallback)]
  acts.append(cg('conditionGroup_priorityStructuredValid','=Topic.措置状態妥当',good,bad))
  return acts
 def instructions(n):n['additionalInstructions']+='\nこの呼出しでは、プロンプト末尾の内部出力形式[[FACTS]]、[[RISK]]、[[MEASURES]]のみを優先する。人向けの見出しは後段が生成する。実施済みと効果未解決を同時に記録し、実施状況で優先度を下げない。'
 def guide(n):n['value']=n['value'][:-1]+'\n実施状況と効果を分離する。実施報告なしは要確認。実施済みの操作でも効果未解決なら危険は継続し、必要な対応を高に保つ。未要請は消防・警察の優先度を下げる理由にならない。"'
 ops={'setVariable_priorityGuideFixed':guide,'setVariable_priorityPrompt':prompt,'answer_priority':lambda n:(instructions(n),result(n))[1],'conditionGroup_priorityLoopNeeded':lambda n:n['conditions'][0].update(condition='=Not(Topic.高優先度完了)')}
 p.write_text(edit(p,ops))
