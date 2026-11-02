"""Latest release report, full YAML, incremental diff and unrun Studio cases."""
import csv,difflib,hashlib,json,re,subprocess
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
import yaml
BASE='11682e9bd5effefcb5755562b663008793dd6f46'
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
 ('必須措置が欠落した非空出力','最初の不合格箇所と原文を渡して最大1回修復。再度不正なら停止'),
 ('目的・優先度判定で検索メッセージが出る','活動で発生元を確認。必要なら検索なしカスタムプロンプトへ置換。全体のマニュアル用ナレッジは残す')]
def main():
    from speed_scope import strip_formatting
    from itemized_build import validator
    before=ix(old(FILES[1]));after=ix((R/FILES[1]).read_text())
    assert strip_formatting(yaml.safe_load(old(FILES[1])))==strip_formatting(yaml.safe_load((R/FILES[1]).read_text()))
    assert not set(before)-set(after)
    for name in [FILES[0],FILES[2],FILES[3]]:assert old(name)==(R/name).read_text()
    oldvars={n.get('variable')for n in before.values()};newvars={n.get('variable')for n in after.values()}
    assert newvars-oldvars=={'Topic.優先度経路診断'}
    native=json.loads((R/'validation/native_restart/results.json').read_text())
    assert all(x['success']for x in native['checks']+native['runs']+native['formats']+native['retryGates'])and native['imageFeatures']['success']and native['fieldPrompts']['success']
    for name in FILES[:3]:assert native['source_sha256'][name]==sha(R/name)
    replay=next(x for x in native['formats']if x['name']=='reported 20261102 raw protocol already valid')
    assert replay['accepted']and replay['gateAccepted']and replay['previousMatches']
    log=(R/'validation/contract_tests.log').read_text();assert '\nOK\n'in log
    count=int(re.search(r'Ran (\d+) tests',log)[1]);stats={x['name']:x for x in native['fieldPrompts']['items']}
    folder=R/'diffs/response_11682e9';folder.mkdir(exist_ok=True)
    (folder/(FILES[1]+'.diff')).write_text(''.join(difflib.unified_diff(old(FILES[1]).splitlines(True),(R/FILES[1]).read_text().splitlines(True),fromfile='11682e9/'+FILES[1],tofile='response_reliability/'+FILES[1])))
    with (R/'validation/response_runtime_cases.csv').open('w',newline='')as f:
        w=csv.writer(f,lineterminator='\n');w.writerow(['ID','input_or_setup','expected','Studio_result'])
        for i,(a,b)in enumerate(CASES,1):w.writerow([f'R-{i:02}',a,b,'NOT_RUN'])
    text='''# 検索表示・停止の調査と実行プロンプトの整理（2026年11月2日）

## 1. 分かったことと未特定のこと

利用者が提示した変数では優先度表示検証が合格で、優先度判定結果は既に7見出しへ組み立てられていた。優先度表示区分が空なのは、不要な任意措置の後なら正常。提供された優先度表示原文を再生すると、11682e9と今回の実際のPower Fx処理の両方が受理し、成功条件も真になる。**この原文による停止は再現していない。** 合格という形式の状態を、判定内容そのものが正しいことと混同しない。

提示された停止メッセージと、この合格状態が同じ実行なのか、保存済みStudioの条件がリポジトリと同じか、別の実行状態が表示されたのかは未確定。実際の停止原因を形式不正や長文だけと断定しない。Studioの成功条件と実行履歴を照合する必要がある。

「役立つ情報が見つからない」表示は検索が関与したことを示すが、どのノードから出たかは会話文だけでは特定できない。通常経路には目的と優先度のAIノードがあるが、その表示が2件だから各々1件と断定はしない。今回、根拠のないYAMLプロパティを足して検索が止まったことにはしていない。

## 2. 今回の修正

- 実行用ルールをruntime_prompts/01_緊急保安_判定ルール.mdへ一本化し、重複した設計説明・基本表をモデル入力から外した。以前の詳細資料は履歴・参照として保持する。
- 屋内・共用部臭気のP07メーター閉止と、臭気／反応箇所のP09消火器は、設備や実施状況が不明でも高・要確認。P10共用部調査とP13危険＋第三者立入りも、設置や調査状況不明を理由に中へ下げない。
- 階数・部屋名から閉止したメーターの系統を推定しない。閉止操作は対応済みのまま保持し、効果と追加対象を分ける。
- NEXTには高の未完了作業と効果確認を優先して示す。質問の羅列はCHECKへも持ち込まず、結論が変わる点を1〜3点の短い説明文にする。
- 明白な単一の外側テキストフェンス、全角区切り、実施済み／完了・未確認／不明の状態表記、箇条書き記号等を限定的に正規化。必須項目欠落・重複・曖昧な状態は許容しない。
- 最初の不合格箇所を優先度表示検証へ保持する。非空の形式不正はその箇所と原文を渡して最大1回修復。空の結果は同じ処理を自動再実行せず停止する。
- 成功判定直前・質問待ち・失敗時のスナップショットを、文字列のTopic.優先度経路診断に保存する。業務回答へ内部診断を追加しない。

## 3. 分岐・変数・互換性

成功分岐は従来どおり Topic.優先度表示検証 = "合格"。形式検証を無効にしたり、不完全な内容を組み立てて送ったりはしない。P11/P12の高連動、全高の完了判定、目的メニュー、修理・調査、トピック遷移、画像・接続・外部案件保存は維持。入口・画像・全体「指示」は11682e9とバイト単位で同一。

新しい本体変数はTopic.優先度経路診断というStringだけ。既存の優先度判定結果と優先度表示検証を新しい判定の前で明示初期化し、修復時は初期化を迂回して前回データを渡す。新しいTable／Boolean変数はない。任意の省略項目、未知の状態や根拠欠落を勝手に作って合格にしない。

診断の例：

```text
subaru-text-20261102-v1|stage=gate|validation=合格|rawChars=1414|displayChars=1275|retry=0
```

gateは成功判定直前、waitは質問待ち、failedは失敗側へ進んだ時点。まずこの版の診断があることを確認する。合格なのに停止した場合は活動の同じ実行とノード・条件を照合する。古い表示や別実行との混在を、この値だけで断定しない。

## 4. 入力長と検索なし構成

'''
    text+=f'''| 同一の初報で組み立てた入力 | 11682e9 | 今回 |
|---|---:|---:|
| 文字数 | {stats['previous']['characters']:,} | {stats['current']['characters']:,} |

'''
    text+='''これはPower Fxで組み立てた本文の文字数で、トークン数や秒数ではない。正常時の優先度AIは1回のまま。形式不正時のみ最大1回で、今回は空出力を再実行しない。実機の速度は計測していない。表示前の案件保存フローも維持しており、そちらが遅ければ文章の短縮だけでは解消しない。

ナレッジ照合をしない専用プロンプトへの切替は24の手順を参照。2つの実在するPromptをStudioで作成し、その環境のaIModelIdを使う必要がある。本体YAMLへ架空のIDや未確認の検索無効化プロパティは入れていない。入力ContextTextが1個・テキスト出力の2Promptについて、実IDで入口と3-9のコピーを作るvalidation/bind_text_prompts.pyも用意した。未接続の本体YAMLだけで検索が無効になったとは主張しない。システムや別ノードからの検索表示なら、その発生元を別に確認する。

## 5. YAML全文

本体の差し替え対象は3-9だけ。検索なしPromptへ切り替える場合は実IDをバインドした入口と3-9を一緒に使う。以下は実ID未設定の現行接続を保った本体の全文。入口と画像も省略せず収録する。

'''
    for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
    text+='## 6. 検証結果と実機計画\n\n'
    text+=f'''オフライン回帰{count}件、Microsoft.PowerFx.Interpreter 1.8.1の{len(native['checks'])}式、番号{len(native['runs'])}入力、内部形式・表示・成功ゲート{len(native['formats'])}ケース、再試行条件{len(native['retryGates'])}ケース、画像11特徴の受渡しに合格。提供された原文は前版と今回の両方で受理・成功ゲート真・同じ表示となり、停止を再現しなかった。最初の失敗理由保持、空結果を再試行しないこと、修復が1回までであることも実際の式で確認した。\n\n'''
    text+='''任意のPromptバインドは、テスト専用IDを使った一時ファイルだけで構造・Goto維持・.text転記を検証し、そのファイルは削除している。接続成功やStudioでの型推論を検証したものではない。テストID入りの配置用YAMLは保存していない。

実AIが各措置を正しく高・中・低へ分類すること、実ナレッジ・画像、実機の型推論・停止・速度・検索表示は未検証。特に提示された原文にはP10/P13の優先度やメーター対象の推定という業務内容の問題が残る。形式テスト合格を、その内容への承認にしない。

以下はStudio未実行の期待結果。\n\n| ID | 入力・条件 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'''
    for i,(a,b)in enumerate(CASES,1):text+=f'| R-{i:02} | {a} | {b} | NOT_RUN |\n'
    text+='''
## 7. 導入と人による確認

24_検索表示と停止の切り分け_導入.mdを参照。今回の3-9全文を新しい会話で試し、版・診断・実行条件を確認する。検索なし化は実在する2Promptと実IDが必要。文章や生成スクリプトを作っただけでStudioを変更・公開はしていない。

最新の編集元はruntime_prompts/01_緊急保安_判定ルール.md。field_concepts/01_調査遮断供給支障.mdは詳細設計資料で、そこだけを変更しても今回の実行ルールは変わらない。画像の特徴別MDと読み込みフローは従来のまま。

差分：diffs/response_11682e9/。結果：validation/contract_tests.log、validation/native_restart/results.json、validation/response_reliability_manifest.json。実機計画：validation/response_runtime_cases.csv。
'''
    target=R/'23_検索表示と停止の検証_YAML全文.md';target.write_text(text)
    blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
    for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
    manifest={'base_commit':BASE,'runtime_rule_source':'runtime_prompts/01_緊急保安_判定ルール.md','runtime_rule_sha256':sha(R/'runtime_prompts/01_緊急保安_判定ルール.md'),'files':{n:sha(R/n)for n in FILES},'new_variables':['Topic.優先度経路診断 (String)'],'added_action_ids':sorted(set(after)-set(before)),'retired_action_ids':[],'entry_image_instructions_byte_identical':True,'business_flow_preserved_except_bounded_repair_policy':True,'full_yaml_blocks_match':True,'field_prompt_assembly':stats,'user_raw_replay':replay,'unittest_count':count,'native_expression_checks':len(native['checks']),'native_number_cases':len(native['runs']),'native_pipeline_cases':len(native['formats']),'native_retry_cases':len(native['retryGates']),'Studio_cases_NOT_RUN':len(CASES),'Studio_stop_NOT_REPRODUCED':True,'Studio_latency_NOT_MEASURED':True,'knowledge_message_source_NOT_IDENTIFIED':True,'search_free_binding_requires_actual_model_ids':True}
    (R/'validation/response_reliability_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print('Latest report:',count,'tests;',len(CASES),'NOT_RUN Studio cases; provided raw accepted in both versions; 3 full YAML blocks match')
if __name__=='__main__':main()
