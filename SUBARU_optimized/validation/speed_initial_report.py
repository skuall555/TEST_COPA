"""Latest release report, full YAML, incremental diff and unrun Studio cases."""
import csv,difflib,hashlib,json,re,subprocess
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
import yaml
BASE='67165f85a61d0ff927e43b0715d701b3c38a4817'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def old(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def ix(s):return {n['id']:n for n in nodes(yaml.safe_load(s))if'id'in n and'kind'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','elseActions','conditions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if'conditions'in n else {})
CASES=[
('台所でガス臭気あり','基本措置は従来基準。P08は中・要確認。初報の通常の単独臭気のみならP11・P12は低・要確認、EMERGENCY通常。実施報告なしは要確認'),
('居室で検知器反応。値は不明','単一の実反応だけで両方高へ固定しない。測定値・広がり・警報・換気／遮断を確認'),
('灯内管検査異常なし、13A成分を検出','13Aはガス種。濃度や制御不能を作らず、成分検出だけで両方高にしない。管検査陰性で全原因を否定しない'),
('検知器のガス種設定は13A。検知反応は不明','設定・ラベルを成分検出と誤認しない。不明事項を確認'),
('集合住宅でメーター閉止済み。濃度が変わらない','P07対応済み保持。上流・別経路候補、P08高、P11・P12高'),
('メーター閉止済み。閉止後は未測定','操作済み保持。未測定を低下なしに変えない。他の高条件を照合'),
('室内1か所で反応。メーター閉止後に低下','灯内管・栓・接続具・機器は候補。確定しない。一時低下だけで低へ落とさない'),
('確実に止漏済み。全影響範囲で継続低下後に反応・臭気・警報消失。拡大なし。安全確認・監視継続。社内基準上要請・避難不要。事故等なし','過去の室内反応だけで高固定にしない。既存と今回の解除条件を照合して低への再評価が可能'),
('共用廊下で反応、集合住宅の分岐バルブあり','系統と位置・操作可否・範囲を確認。バルブ存在を操作可能や遮断済みとしない'),
('分岐バルブはないがマルサがある。漏れの特定に時間がかかる','適用範囲と権限確認の上で上流遮断検討高。存在しないバルブの操作を指示しない'),
('PE管で漏えい継続、メーター閉止後も反応継続','スクイズ適用を権限ある担当者の判断候補に。具体的圧着手順を生成しない'),
('管種は不明。止められない','PE管と仮定しない。有効な上流遮断方法確認、既存高を保持'),
('戸建て室内1か所臭気。閉止前で他の異常報告なし','メーター閉止優先。マルサ・スクイズを一律高にしない。室内臭気だけで要請・避難高にしない'),
('道路の下水マンホールと舗装の継ぎ目で反応','移動経路と周辺建物流入を確認。危険区域への進入・蓋開放を無条件に指示しない'),
('道路で反応、隣接宅の排水口は未調査','周辺排水口・床下・ピット等の追加調査を具体化。道路だけで安全としない'),
('通報宅の排水口検知済み。周辺建物は未調査','P05の実施済み保持。P20・P21の対象を分離'),
('ガス管漏えいなし。コンロ接続コード近くで反応','接続具と機器も原因候補。管検査陰性で安全断定しない'),
('コンロにつながるガス栓閉止後に反応が消えた','機器・接続具の可能性と根拠・反証条件。全体遮断や原因確定にしない'),
('機器ガス栓閉止後も変化なし','他機器・灯内管・上流・外部流入候補。実施済みを取消さない'),
('漏れ検査異常なし、隣家の給湯器使用時のみ臭気','排ガス流入と経路を候補に。自宅機器だけに限定しない。調査用再点火を勧めない'),
('燃焼機器近くで体調不良者あり。都市ガス検知器は反応なし','CO等も考慮。検知器の対象ガスを区別し、緊急支援を高。再運転せず適切な計測器・担当者確認'),
('ガスが出ない、火力が弱い','P23高。メーター表示・作動理由、供給圧力、影響戸数を確認。復帰・点火の指示をしない'),
('マイコン表示点滅。圧力異常かは未確認','点滅だけで圧力異常を断定しない。表示内容・遮断理由確認。条件成立した追加調査を整理'),
('供給圧力低下を測定、2軒でマイコン作動','P23高、水分流入・周辺圧力調査高。複数戸供給支障の可能性、原因断定なし'),
('管内水分が疑われる。作業資格・権限は不明','資格・権限・安全手順の確認。AIだけでメーター取り外し・開管を指示しない'),
('通報宅の圧力測定だけ完了、周辺表示と管内水分は未確認','P23の部分実施を根拠に保持し、全体対応済みにしない。高未完了'),
('圧力供給支障に必要な全初期確認・該当追加調査完了と報告','P23対応済み。その他の高が残れば全完了にしない'),
('ガスが出ないだけ。臭気、検知反応、事故等は未報告','P23高と消防警察高を自動連動しない。要請・避難の必要性は具体的な警戒兆候がなければ低。情報不足だけで中にしない'),
('情報不足で現在の臭気・反応・影響範囲不明','初報で具体的な警戒兆候がない場合は低。既往の高があれば未報告だけで下げない。低を安全確認済みとしない'),
('室内臭気があり、2地点で実反応も出た','複数地点の実反応と臭気でE-02成立。高優先'),
('これまでの報告から判断に必要な情報は十分','不要な質問を作らず、未完了作業の実施を自然な文章で促す'),
('画像添付・マニュアル確認・目的番号選択の既存回帰','入口・4-9・全体指示・接続ID・質問・トピック間遷移は前版のまま。トピック外の作文なし'),
('浴室で臭気を感じるとの通報','P08は中・要確認。P11・P12は初報に危険兆候の報告がないため低・要確認。強い臭気、反応、警報、換気不能、遮断不能を作らない'),
('換気したかも栓を閉めたかも未報告','未確認を換気不能・遮断不能と読み替えない'),
('隣室に入れず換気できない。ドアポストLEL1％検知、警報継続','E-01成立。要請・避難高を維持し、低濃度を理由に下げない'),
('3戸で反応、バルブがなく止められない','E-02成立。要請・避難高を維持'),
('火災発生、負傷者あり','追加確認待ちにせず、関係する要請・避難・救護等を高'),
('強いガス臭が継続し拡散範囲が拡大','明示された強臭気・拡散等の高を維持'),
('火気使用禁止は周知済み、メーター閉止済み。ほかは未報告','明確な実施済みは保持。他の実施状況は要確認。未実施と断定しない'),
('メーターはまだ閉めていない。消防も呼んでいない','明確に否定された実施状況は未実施。必要性の優先度とは別に扱う'),
('初報は浴室の臭気のみ、続報はまだ何も作業していない','要請・避難は情報不足だけで中に上げず低。実施状況は明確に未実施とされた範囲だけ未実施'),
('以前に換気不能＋検知＋継続警報。続報は消防未要請','要請・避難の既往高を維持。短い続報で危険履歴を忘れない'),
('以前に広範囲拡散、メーターは閉めたが濃度未測定','閉止操作は対応済み。効果未確認だけで既往高を低に戻さない'),
('単発のガス警報音を聞いたが継続・実検知は未確認','高条件がなければ、具体的に報告された警戒兆候として中。単なる情報不足との違いを説明')]
def main():
    from speed_scope import strip_formatting,retired
    from itemized_build import validator
    before=ix(old(FILES[1]));after=ix((R/FILES[1]).read_text())
    assert strip_formatting(yaml.safe_load(old(FILES[1])))==strip_formatting(yaml.safe_load((R/FILES[1]).read_text()))
    removed=sorted(set(before)-set(after));added=sorted(set(after)-set(before))
    assert all(retired(k)for k in removed)
    assert all(k.startswith('setVariable_item')for k in added)
    assert {n.get('variable')for n in before.values()}=={n.get('variable')for n in after.values()}
    for name in [FILES[0],FILES[2],FILES[3]]:assert old(name)==(R/name).read_text()
    ns={};exec(subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/validation/itemized_build.py']).decode(),ns)
    native=json.loads((R/'validation/native_restart/results.json').read_text())
    assert all(x['success']for x in native['checks']+native['runs']+native['formats'])and native['imageFeatures']['success']and native['fieldPrompts']['success']
    for name in FILES[:3]:assert native['source_sha256'][name]==sha(R/name)
    log=(R/'validation/contract_tests.log').read_text();assert '\nOK\n'in log
    count=int(re.search(r'Ran (\d+) tests',log)[1]);stats={x['name']:x for x in native['fieldPrompts']['items']}
    folder=R/'diffs/speed_initial_67165f8';folder.mkdir(exist_ok=True)
    (folder/(FILES[1]+'.diff')).write_text(''.join(difflib.unified_diff(old(FILES[1]).splitlines(True),(R/FILES[1]).read_text().splitlines(True),fromfile='67165f8/'+FILES[1],tofile='speed_initial/'+FILES[1])))
    with (R/'validation/speed_initial_runtime_cases.csv').open('w',newline='')as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['ID','input_or_setup','expected','Studio_result'])
        for i,(a,b)in enumerate(CASES,1):w.writerow([f'S-{i:02}',a,b,'NOT_RUN'])
    text='''# 初報の要請・避難の優先度と処理負荷の修正

## 1. 修正内容の要約

67165f8では情報不足を中の確認枠に置いたため、通常の単独臭気の初報でも要請・避難が中になっていた。今回、P11消防警察要請・P12避難誘導については、通常の単独臭気の初報で具体的な危険・警戒兆候が報告されていなければ低、具体的な警戒兆候または改善途上なら中、危険条件が成立すれば高とした。低は必要性の現時点の優先度であり、安全確認済みという意味ではない。

既に高の危険条件が報告された後は、短い続報に危険の記載がないだけで低へ戻さない。従来のE-01／E-02、強臭気・広域拡散・事故・制御不能等の高と、改善後再評価の条件を維持する。P08上流遮断の建物・設備不明時の中、以前指定された基本措置の高、実施状況不明なら要確認という扱いは維持した。

速度については、判定プロンプトの概念・Eルール等の重複を除去した。また、措置ごとに何度もTopic変数を更新して表示欄へ追記していた処理を、文字列へ蓄積して最後に3欄へまとめる形に変更した。必要のない任意措置P14〜P23は内部出力を省略できるようにし、必要な措置は従来どおり出力する。

## 2. 条件・変数・処理の変更

| 対象 | 今回の変更 |
|---|---|
| setVariable_priorityGuideFixed | 初報と既往危険の再評価を区別。通常臭気だけの初報では要請・避難を低 |
| setVariable_priorityPrompt | 固定ガイドは1回だけ参照。重複した長文と手順説明を削減 |
| answer_priority | 情報不足だけで要請・避難を中へ上げないことを明記 |
| 生成された措置別表示ノード | 同じ文字列変数を繰り返し使い、最後に高・中・低の欄と未完了を集計 |
| P14〜P23 | 不要時はブロックを省略可能。旧形式の対象外ブロックも引き続き受理 |

新しいTopic／Global変数はゼロ。TopicにTableやBooleanを新規代入しない。Split／Filterで作る表は式の中だけで使い、ConcatやIfで文字列に戻して代入する。式は短い段階に分け、巨大な入れ子の条件式には戻していない。

既存の業務トピック遷移、入力バインド、質問、修理・調査、画像割り込み、全体「指示」、外部接続・フローIDは維持。削減した165個のIDは今回以前に生成した表示用の一時処理だけで、業務側のGoto先は削除していない。置換用の集計ノードは4個。実施済みと未完了の区別、7見出し、要請・避難の高連動、内部形式検査、不正形式の最大1回再生成は維持した。

## 3. 初報と危険時の期待判定

| 報告内容 | 消防警察・避難 |
|---|---|
| 浴室で臭気あり、という通常の単独臭気の初報のみ | 低。実施状況不明なら要確認。情報不足だけで中へ上げない |
| 単発の警報音など、具体的な警戒兆候が報告されたが高条件は未成立 | 中。何を監視し、どうなれば高かを説明 |
| 入室／換気不能の空間で検知または継続警報、複数反応と臭気等、事故・強臭気・広域拡散・制御不能等 | 該当する既存条件により高。追加質問待ちで遅らせない |
| 既に高だったが、続報に危険の記載がない | 高を自動解除しない。改善後再評価の条件を確認 |

「浴室で臭気あり」だけの場合の確認文は、ガスのような臭いか、強さ・広がり、検知・警報など次の判定に効く点を簡潔に聞く。存在不明の事故や遮断不能を補わず、一度に全確認項目を羅列しない。低の要請・避難を直ちに実施するよう自動追記しない。

## 4. 処理負荷の比較と実測の限界

'''
    text+=f'''| 指標 | 67165f8 | 今回 |
|---|---:|---:|
| 判定結果の検証・表示処理（トップレベルノード数） | {len(ns['validator']())} | {len(validator())} |
| 上記SetVariable数 | {sum(n['kind']=='SetVariable'for n in ns['validator']())} | {sum(n['kind']=='SetVariable'for n in validator())} |
| 初報「浴室で臭気あり」、履歴空の実際の組立プロンプト文字数 | {stats['previous']['characters']:,} | {stats['current']['characters']:,} |
| 追加概念の長文が組立入力に現れる回数 | {stats['previous']['conceptHeadingCopies']} | {stats['current']['conceptHeadingCopies']} |
| 不要な任意措置の内部ブロック | 10個も必須 | 省略可能 |

'''
    text+='''文字数はPower Fxでガイドと入力を実際に結合して計測した値で、モデルのトークン数ではない。ノード数や文字数の削減率をそのまま時間短縮率とはしない。モデル呼出し、オーケストレーション、ネットワーク、外部フロー、ホストの各処理時間はこの環境では計測できない。1〜2分の主原因を特定した、十数秒に戻った、という結果ではない。

正常時の3-9の優先度AIは1回のまま、形式不正時だけ最大1回再生成する。入口の意味判定AIも変更していない。案件保存フローは結果表示前に1回呼ぶ従来の経路を維持しているため、ここが遅ければ本文・表示処理の削減だけでは解消しない。保存を省いたり、保存前の表示へ順序変更したりはしていない。

## 5. 修正後のYAML全文

今回差し替えるのは3-9だけ。入口と画像も比較用に全文を収録する。

'''
    for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
    text+='## 6. 想定テストケースと検証結果\n\n全件Studio未実行（NOT_RUN）の確認計画。期待結果を実機の合格結果にはしていない。\n\n| ID | 入力・条件 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'
    for i,(a,b)in enumerate(CASES,1):text+=f'| S-{i:02} | {a} | {b} | NOT_RUN |\n'
    compared=sum('previousMatches'in x and x['previousMatches'] for x in native['formats'])
    text+=f'''\nオフライン回帰{count}件、Microsoft.PowerFx.Interpreter 1.8.1で{len(native['checks'])}式の構文・型、番号{len(native['runs'])}例、内部データの表示・連動・完了・拒否{len(native['formats'])}ケース、画像11特徴の受渡しに合格。式数が減ったのは削除した表示ノード分であり、現在の変更・追加式を選別して省いた結果ではない。\n\n'''
    text+='''同じ完全形式の模擬AI出力は、前版と新版の実際のPower Fx式で受理／拒否と表示全文を比較し一致を確認した。任意ブロック省略という仕様変更ケースは新しい期待結果で別に検証した。欠落した必須措置、重複コード、片側だけの任意タグ、余分な内容、内部区切り文字の注入を拒否する。高の任意P23が未完了なら完了にしない。

実AIが初報を低、警戒兆候を中、危険を高と判断できるかは未検証。模擬データの配置検証でAIの意味判断の正解率を主張していない。Studioの型推論・読込・写真認識・実ナレッジ・応答速度も未検証。

## 7. 人による確認・導入

22_初報判定と速度改善の導入.mdを参照。3-9の全文を同じ版で更新する。少なくとも初報だけの会話、続報でE-01／E-02が成立する会話、既往高がある会話、テキストだけの連続報告と画像割り込みを確認する。

速度が遅い場合は活動の実行時間で入口AI→answer_priority→表示処理→invokeFlowAction_caseSaveFieldAdvice→question_priorityUpdateを分け、再生成が1回起きていないかも確認する。実測はvalidation/speed_timing_plan.csvへ記録できる。今回の計測欄は空で、架空の秒数は記入していない。

編集元はfield_concepts/01_調査遮断供給支障.md、実行時プロンプトの組立はvalidation/field_concepts_build.py、表示処理と内部契約はvalidation/itemized_build.py。MD編集だけではStudioに反映されない。差分はdiffs/speed_initial_67165f8/、変更ID・SHA・負荷比較はvalidation/speed_initial_manifest.json。
'''
    target=R/'21_初報判定と速度改善_YAML全文.md';target.write_text(text)
    blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
    for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
    manifest={'base_commit':BASE,'source':SOURCE,'files':{n:sha(R/n)for n in FILES},'added_action_ids':added,'retired_generated_action_ids':removed,'new_variables':[],'business_flow_preserved':True,'entry_image_instructions_byte_identical':True,'full_yaml_blocks_match':True,'formatter_nodes':{'previous':len(ns['validator']()),'current':len(validator())},'field_prompt_assembly':stats,'unittest_count':count,'native_expression_checks':len(native['checks']),'native_number_cases':len(native['runs']),'native_pipeline_cases':len(native['formats']),'Studio_cases_NOT_RUN':len(CASES),'Studio_latency_NOT_MEASURED':True}
    (R/'validation/speed_initial_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    timing=R/'validation/speed_timing_plan.csv'
    if not timing.exists():
        with timing.open('w',newline='')as f:
            w=csv.writer(f,lineterminator='\n');w.writerow(['version','scenario','trial','purpose_ai_ms','priority_ai_ms','priority_ai_retry_count','formatting_ms','case_save_flow_ms','total_to_reply_ms','notes'])
            for version in ['67165f8','current']:
                for scenario in ['initial_text','followup_text','image_interrupt']:
                    for trial in range(1,4):w.writerow([version,scenario,trial,'','','','','','','NOT_MEASURED'])
    print('Latest:',count,'tests;',len(CASES),'NOT_RUN Studio cases;',len(ns['validator']()),'->',len(validator()),'formatter nodes')
if __name__=='__main__':main()
