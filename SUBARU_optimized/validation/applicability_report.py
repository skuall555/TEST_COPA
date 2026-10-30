"""Latest release report, full YAML, incremental diff and unrun Studio cases."""
import csv,difflib,hashlib,json,re,subprocess
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
import yaml
BASE='9b2c7f107a0a8c16150f3b8a4fbcd4fbc8c80ec6'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def old(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def ix(s):return {n['id']:n for n in nodes(yaml.safe_load(s))if'id'in n and'kind'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','elseActions','conditions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if'conditions'in n else {})
CASES=[
('台所でガス臭気あり','基本措置は従来基準。P08・P11・P12は臭気だけで高にせず中・要確認、EMERGENCY通常。実施報告なしは要確認'),
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
('ガスが出ないだけ。臭気、検知反応、事故等は未報告','P23高と消防警察高を自動連動しない。後者の情報不足は判定保留と明示'),
('情報不足で現在の臭気・反応・影響範囲不明','P11・P12根拠と説明文に判定保留・追加確認が必要。内部中は暫定枠。低や安全としない'),
('室内臭気があり、2地点で実反応も出た','複数地点の実反応と臭気でE-02成立。高優先'),
('これまでの報告から判断に必要な情報は十分','不要な質問を作らず、未完了作業の実施を自然な文章で促す'),
('画像添付・マニュアル確認・目的番号選択の既存回帰','入口・4-9・全体指示・接続ID・質問・トピック間遷移は前版のまま。トピック外の作文なし'),
('浴室で臭気を感じるとの通報','P08・P11・P12を自動高にしない。中・要確認。強い臭気、反応、警報、換気不能、遮断不能を作らない'),
('換気したかも栓を閉めたかも未報告','未確認を換気不能・遮断不能と読み替えない'),
('隣室に入れず換気できない。ドアポストLEL1％検知、警報継続','E-01成立。要請・避難高を維持し、低濃度を理由に下げない'),
('3戸で反応、バルブがなく止められない','E-02成立。要請・避難高を維持'),
('火災発生、負傷者あり','追加確認待ちにせず、関係する要請・避難・救護等を高'),
('強いガス臭が継続し拡散範囲が拡大','明示された強臭気・拡散等の高を維持'),
('火気使用禁止は周知済み、メーター閉止済み。ほかは未報告','明確な実施済みは保持。他の実施状況は要確認。未実施と断定しない'),
('メーターはまだ閉めていない。消防も呼んでいない','明確に否定された実施状況は未実施。必要性の優先度とは別に扱う')]
def main():
    before=ix(old(FILES[1]));after=ix((R/FILES[1]).read_text())
    changed=[k for k in before if own(before[k])!=own(after[k])]
    assert set(before)==set(after)
    assert set(changed)=={'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority'}
    for name in [FILES[0],FILES[2],FILES[3]]:assert old(name)==(R/name).read_text()
    folder=R/'diffs/applicability_9b2c7f1';folder.mkdir(exist_ok=True)
    (folder/(FILES[1]+'.diff')).write_text(''.join(difflib.unified_diff(old(FILES[1]).splitlines(True),(R/FILES[1]).read_text().splitlines(True),fromfile='9b2c7f1/'+FILES[1],tofile='applicability/'+FILES[1])))
    native=json.loads((R/'validation/native_restart/results.json').read_text())
    assert all(x['success']for x in native['checks']+native['runs']+native['formats'])and native['imageFeatures']['success']
    for name in FILES[:3]:assert native['source_sha256'][name]==sha(R/name)
    log=(R/'validation/contract_tests.log').read_text();assert '\nOK\n'in log
    count=int(re.search(r'Ran (\d+) tests',log)[1])
    with (R/'validation/applicability_runtime_cases.csv').open('w',newline='')as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['ID','input_or_setup','expected','Studio_result'])
        for i,(a,b)in enumerate(CASES,1):w.writerow([f'A-{i:02}',a,b,'NOT_RUN'])
    text='''# 措置ごとの適用条件の修正とYAML全文

## 1. 修正内容の要約

9b2c7f1で追加した「室内臭気・反応だけで消防警察要請と避難を高」とする条件が広すぎた。さらに内部ひな形ではP01〜P13すべてに高・未実施の例を入れており、未知の状況を高・未実施へ寄せる要因となり得た。旧プロンプトには「実施報告なしは未実施」という指示も残っていた。今回これらを除去・修正した。

変更は3-9の既存3プロンプト欄だけ。新しいノード・変数・分岐・トピックは追加せず、既存ID、トピック間遷移、画像、入口、全体「指示」、接続、内部データ検証と表示式を維持した。前回の圧力・供給支障P23や画像の特徴別編集も維持している。

- 単独室の通常の臭気・反応、13Aのガス種確認だけで要請と避難を自動高にしない。
- 上流遮断の高には、その措置の条件が必要。建物・設備不明の初報は中の確認枠。基本措置の高を他の措置へ流用しない。
- 入室／換気不能＋実検知／継続警報のE-01、複数反応と臭気・流入・遮断不能等のE-02、事故・強臭気・広域拡散等の既存高は維持する。
- 実施済みは対応済み、明示的にまだ実施していない場合は未実施、不明なら要確認。高・要確認も完了にしない。
- 出力ひな形の優先度・状態は固定値をやめ、措置ごとに埋める形へ修正。

## 2. 条件分岐と変数の変更一覧

| 既存ノード | 変更内容 |
|---|---|
| setVariable_priorityGuideFixed | 過度な高条件の除去、適用条件分離、旧未実施指示の置換 |
| setVariable_priorityPrompt | 同じ適用条件、状態の扱い、値を固定しない内部ひな形 |
| answer_priority | 各措置固有の条件と実施状況の独立判定を補足 |

新しい変数、ノード、条件分岐はゼロ。内部EMERGENCYは従来どおり高／通常で、要請と避難の両方を高にする成立条件を確認した時だけ高。通常は安全や要請不要という意味ではなく、各措置の条件を別々に判断する。

## 3. 今回の「浴室で臭気を感じる」の期待判定

| 項目 | 期待する扱い |
|---|---|
| 分岐バルブ・引込管遮断等P08 | 建物・設備・追加危険条件不明のため中・要確認。確認が必要というだけで操作を高にしない |
| 消防・警察要請P11 | 単独の臭気だけで高にしない。中の暫定確認枠・要確認で危険条件を確認 |
| 避難誘導P12 | 同様に自動高にしない。入室・換気・検知・警報・影響範囲等を確認 |
| 実施状況 | 通報以外の報告がなければ要確認。未実施とは断定しない |

火気禁止、電気操作禁止、表示、ポケット警報器、検知調査の基本高、および屋内臭気時の換気・メーター閉止と臭気／反応箇所での消火器の高は、以前の指定に基づき維持している。このため高の項目数だけが少なくなる修正ではない。基本措置自体の条件を変更する場合は、その基準を別途見直す必要がある。臭気の種類が未確認ならガス臭かも確認し、報告のない強さ・範囲・濃度を作らない。

初報の確認文の例：

> 浴室で臭気があるとの通報は確認できていますが、現時点では広がりや遮断・換気の状況が分からないため、上流遮断や消防・警察への要請、避難誘導の必要性は確定できません。まず、ガスのような臭いか、強さや範囲が増していないか、検知器の反応や警報器の継続鳴動があるかを教えてください。入室や換気ができない場所で検知・継続警報がある場合などは、要請と避難の優先度が高になります。実施済みの基本措置があれば、その内容も教えてください。

これは期待例であり、実モデルで得た出力ではない。緊急条件が既に分かっている場合に、この質問を繰り返して対応を待たせない。

## 4. 修正後のYAML全文

今回の差し替えは3-9のみ。入口・画像分析は未変更だが、全文を比較用に収録する。

'''
    for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
    text+='## 5. 想定テストケースと期待結果\n\n全件Studio未実行（NOT_RUN）。\n\n| ID | 入力・条件 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'
    for i,(a,b)in enumerate(CASES,1):text+=f'| A-{i:02} | {a} | {b} | NOT_RUN |\n'
    text+=f'''\nオフライン回帰{count}件、Microsoft.PowerFx.Interpreter 1.8.1による{len(native['checks'])}式の構文・型、番号{len(native['runs'])}例、内部出力の表示・連動・拒否・完了判定{len(native['formats'])}ケース、画像11特徴の両段への受渡しに合格。今回は表示式を変更していない。既知の過度な高条件・高未実施の例・未報告を未実施とする旧指示が除去されたこと、既存の全制御構造が同じであることも確認した。\n\n'''
    text+='''これらは実AIの意味判断を試した結果ではない。実モデルで初報を正しく中の確認枠へ置くこと、高条件が加われば高へ上げることはStudioで確認が必要。CSVの期待結果をルール文の検査だけでPASSにしていない。

## 6. 人による確認が必要な箇所

Studioの保存・ホスト型推論、AIの条件適用、写真認識、実ナレッジ取得、応答時間は未確認。初報だけの会話と、E-01／E-02等を追加した会話を分けて試す。AIが返す判定値の意味はこの文字列検証器では保証できない。高の判定値を返した場合はYAMLが高へ配置するため、判定値と根拠、実際に使われたプロンプトを確認する。

配管区分、遮断・開管等の適用・権限と社内基準の照合は従来どおり担当者が確認する。

## 7. 導入・差分・編集元

20_条件適用修正の導入.mdを参照。3-9の全文のみ更新し、新しいテスト会話で確認する。入口や全体指示は触らない。差分はdiffs/applicability_9b2c7f1/、SHAと変更ノードはvalidation/applicability_manifest.json、実機計画はvalidation/applicability_runtime_cases.csv。

概念の編集元はfield_concepts/01_調査遮断供給支障.md。内部ひな形はvalidation/itemized_build.py、旧状態指示の置換はvalidation/field_concepts_build.py。GitHub上のMD変更だけではStudioへ反映されない。rebuild.pyで再生成・検証して全文を差し替える。
'''
    target=R/'19_条件適用修正_変更内容とYAML全文.md';target.write_text(text)
    blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S)
    assert len(blocks)==3
    for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
    manifest={'base_commit':BASE,'source':SOURCE,'source_sha256':sha(R/SOURCE),'files':{n:sha(R/n)for n in FILES},'changed_existing_action_ids':changed,'added_action_ids':[],'removed_action_ids':[],'new_variables':[],'full_yaml_blocks_match':True,'unchanged_entry_image_instructions':True,'unittest_count':count,'native_expression_checks':len(native['checks']),'native_number_cases':len(native['runs']),'native_pipeline_cases':len(native['formats']),'native_image_features':native['imageFeatures']['success'],'Studio_cases_NOT_RUN':len(CASES)}
    (R/'validation/applicability_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Applicability report:',count,'regressions;',len(CASES),'NOT_RUN Studio cases; full YAML blocks match')
if __name__=='__main__':main()
