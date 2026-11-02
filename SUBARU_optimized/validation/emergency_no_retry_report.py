"""Latest release report, full YAML, incremental diff and unrun Studio cases."""
import csv,difflib,hashlib,json,re,subprocess
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
import yaml
BASE='2ba669466e0bfaf4d51e40989930cc3eb4ab65f6'
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
CASES += [
 ('台所でガス臭い、設備・実施状況は未報告','P07・P09は高・要確認。設備や設置状況不明を理由に中にしない'),
 ('メーター閉止、共用部臭気、アパート2階','閉止操作は対応済み。階数から対象系統を推定しない。共用部のP10、第三者立入りがあるP13は実施状況不明でも高'),
 ('NEXTの生成','高の未完了作業と効果確認を先に示し、質問だけで埋めない'),
 ('生成結果が空','空の同じ処理を自動再実行せず停止。最初の失敗理由を記録'),
 ('必須措置が欠落した非空出力','AI再呼出しをせず直ちに停止。欠落した判定・事実は補わない'),
 ('目的・優先度判定で検索メッセージが出る','活動で発生元を確認。必要なら検索なしカスタムプロンプトへ置換。全体のマニュアル用ナレッジは残す')]
CASES += [
 ('EMERGENCYが「通常 理由」','通常という明示語と空白の境界が明確なら「通常|理由」へ正規化して表示。AI再生成なし'),
 ('EMERGENCYが「高　理由」','高と理由を保持し区切りを正規化。要請・避難の高連動と実施済みを維持'),
 ('EMERGENCYが「高ではない」「不明 理由」','判定を推測せず即停止。AIへの自動戻りなし'),
 ('追加報告で待ち続ける','診断v2のbeforeAI／afterAI／beforeCaseSave等で区間を特定。外部処理の実時間は活動で確認')]
def main():
    from speed_scope import strip_formatting
    before=ix(old(FILES[1]));after=ix((R/FILES[1]).read_text())
    assert strip_formatting(yaml.safe_load(old(FILES[1])))==strip_formatting(yaml.safe_load((R/FILES[1]).read_text()))
    retired=sorted(set(before)-set(after))
    assert set(retired)=={'conditionGroup_priorityFormatRetry','setVariable_priorityFormatRetryIncrement','goto_priorityFormatRetry'}
    assert {n.get('variable')for n in before.values()}=={n.get('variable')for n in after.values()}
    for name in [FILES[0],FILES[2],FILES[3]]:assert old(name)==(R/name).read_text()
    native=json.loads((R/'validation/native_restart/results.json').read_text())
    assert all(x['success']for x in native['checks']+native['runs']+native['formats'])and native['imageFeatures']['success']and native['fieldPrompts']['success']
    for name in FILES[:3]:assert native['source_sha256'][name]==sha(R/name)
    replay=next(x for x in native['formats']if x['name']=='reported missing EMERGENCY separator')
    assert replay['accepted']and replay['gateAccepted']and replay['previousAccepted']is False
    log=(R/'validation/contract_tests.log').read_text();assert '\nOK\n'in log
    count=int(re.search(r'Ran (\d+) tests',log)[1])
    folder=R/'diffs/no_retry_2ba6694';folder.mkdir(exist_ok=True)
    (folder/(FILES[1]+'.diff')).write_text(''.join(difflib.unified_diff(old(FILES[1]).splitlines(True),(R/FILES[1]).read_text().splitlines(True),fromfile='2ba6694/'+FILES[1],tofile='no_retry/'+FILES[1])))
    with (R/'validation/no_retry_runtime_cases.csv').open('w',newline='')as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['ID','input_or_setup','expected','Studio_result'])
        for i,(a,b)in enumerate(CASES,1):w.writerow([f'N-{i:02}',a,b,'NOT_RUN'])
    text='''# EMERGENCYの区切り欠落を正規化し、自動再生成を停止

## 1. 分かった原因と未特定のこと

今回提示された原文は、EMERGENCYが「通常|理由」ではなく「通常 理由」になっていた。旧版の実際のPower Fxで不合格を再現し、今回の式では判定語と理由を保持して読めることを確認した。

```text
旧：[[EMERGENCY]] 通常 共用部で臭気があり… [[/EMERGENCY]]
正規化：通常|共用部で臭気があり…
```

これは今回の itemEmergencyValid の不合格原因である。一方、**2時間処理が終わらない事象そのものは、この環境では再現していない**。旧コードの修復回数は最大1回であり、今回の値だけから無限ループや長時間待ちの全原因が確定したとはしない。進行中の変数がどの時点のものか、モデル・案件保存・ホスト等の実行時間はStudioの活動で確認が必要。

提示された原文には、メーター閉止だけで危険が一部解消とする推定、共用部調査・保安措置の優先度など、形式とは別の業務判断の問題も残る。正規化が成功したことを、その内容が正しいとの承認にはしない。

## 2. 修正内容

- EMERGENCYに区切りがあり判定語・理由が正しければ従来どおり受理。
- 区切りがなくても、先頭が明確な「通常」または「高」で、その後が半角／全角空白・改行・タブなら、判定語を変えず区切りだけ補う。元のAI出力は優先度判定結果に保持し、処理用の区分だけを正規化する。
- 「高ではない」「通常の…」「不明…」、理由がないもの、複数の区切りがある曖昧な出力は推測せず不合格。
- EMERGENCYが不正なら、残る措置の組立を続けず成功／失敗のゲートへ進み、停止する。
- **形式不正時のAI自動再生成を削除。** 条件・再試行回数加算・answer_priorityへのGotoを除去した。前回修正した再生成条件も今回の版にはない。
- 通常の追加報告は既存の質問待ちを経て次の判定へ進む。自動で同じ優先度AIへ戻る経路はない。追加情報確認の既存10回上限、修理・調査・画像のフローは維持。
- 同じStringの診断をv2へ更新し、AI呼出し前後・成功ゲート・案件保存前後・質問待ち・失敗側を記録する。

優先度・実施状況・実施済み範囲の判断、7見出し、要請・避難の高連動、必須措置の検証は変更していない。判定結果が空・欠落・曖昧なら、未検証の回答を送らない。新しい変数はゼロ。入口・画像分析・全体指示・外部接続は2ba6694と同一。

## 3. 変更した条件と変数

| 対象 | 変更 |
|---|---|
| setVariable_itemEmergencyNormalize | 判定語と理由の間の欠落区切りを限定的に正規化 |
| conditionGroup_itemEmergencyInvalid | 不正ならsetVariable_priorityGateSnapshotへ進んで停止 |
| conditionGroup_priorityFormatRetryほか | 自動再生成の条件・加算・Gotoを削除 |
| answer_priority.userInput | 既存の判定プロンプトだけを渡す。前回結果を付けた修復呼出しをしない |
| Topic.優先度経路診断 | 既存Stringのままv2に更新し、区間を記録 |

診断の版はsubaru-text-20261102-v2。beforeAIはモデル呼出し前、afterAIは出力受領後、gateは成功条件の直前、beforeCaseSave／afterCaseSaveは案件保存の前後、waitは質問待ち、failedは失敗側。保存前に長く止まる場合とモデルから返らない場合を分けて確認できる。

## 4. YAML全文

今回は3-9の全文だけを差し替える。入口・画像も比較のため全文収録。

'''
    for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
    text+='## 5. 検証と期待結果\n\n'
    text+=f'''回帰{count}件、Microsoft.PowerFx.Interpreter 1.8.1で{len(native['checks'])}式の構文・型、番号{len(native['runs'])}入力、内部形式・成功ゲート{len(native['formats'])}ケース、画像11特徴の受渡しに合格。今回提示された原文は旧版では拒否、今回版では受理され、メーター閉止済みも維持された。明確な高の区切り欠落は高を保持し、否定文・不明な判定・理由欠落は拒否した。\n\n'''
    text+='''Question／EndDialogを境界にした制御フローで、利用者の追加入力を待たずに優先度AIへ戻る経路がないことを確認した。自動再生成のGoto削除も確認した。これはモデルや外部サービスの完了時間・実機の処理時間に上限を設けた試験ではない。

以下は実機未実行の計画。AIの意味判断、2時間の待ち、外部処理時間、Studioの読込・実画像等は未検証。\n\n| ID | 入力・条件 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'''
    for i,(a,b)in enumerate(CASES,1):text+=f'| N-{i:02} | {a} | {b} | NOT_RUN |\n'
    text+='''
## 6. 導入と人による確認

27_追加報告の停止対策_導入.mdを参照。待ち続けている会話はリセットし、3-9を全文差し替えた後で新しい会話から試す。古い実行は保存だけで今回の版へ切り替わらない。

2時間の待ちが解消したことは未確認。モデル呼出しや外部フロー自体が返らない場合は、本体の再生成削除だけでは時間を保証できない。診断v2と同じ活動の実行時間を照合する。未確認のタイムアウト用YAML属性は追加していない。

過去に案内した検索なし専用Promptの接続は今回も別設定。入口・画像・ナレッジ設定は触っていない。今回の版を使う場合、古い修復用ConditionGroupを一部だけ残さず、同じ版の全文を使う。

差分：diffs/no_retry_2ba6694/、検証結果：validation/native_restart/results.json、validation/contract_tests.log、validation/no_retry_manifest.json、実機計画：validation/no_retry_runtime_cases.csv。
'''
    (R/'26_EMERGENCY正規化と自動再生成停止_YAML全文.md').write_text(text)
    blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
    for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
    manifest={'base_commit':BASE,'files':{n:sha(R/n)for n in FILES},'added_action_ids':sorted(set(after)-set(before)),'retired_automatic_repair_action_ids':retired,'new_variables':[],'entry_image_instructions_byte_identical':True,'full_yaml_blocks_match':True,'reported_missing_separator_replay':replay,'autonomous_priority_ai_cycle':'NONE before next Question/EndDialog','diagnostic_version':'subaru-text-20261102-v2','unittest_count':count,'native_expression_checks':len(native['checks']),'native_number_cases':len(native['runs']),'native_pipeline_cases':len(native['formats']),'Studio_cases_NOT_RUN':len(CASES),'Studio_two_hour_wait_NOT_REPRODUCED':True,'external_call_duration_NOT_BOUNDED':True}
    (R/'validation/no_retry_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Latest:',count,'regressions,',len(native['formats']),'native cases;',len(CASES),'NOT_RUN Studio cases; old rejected/user raw now accepted')
if __name__=='__main__':main()
