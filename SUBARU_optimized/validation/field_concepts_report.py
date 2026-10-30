"""Latest release report, full YAML, incremental diff and unrun Studio cases."""
import csv,difflib,hashlib,json,re,subprocess
from pathlib import Path
from restart_build import R,FILES
from restart_support import nodes
from field_concepts_build import SOURCE
import yaml
BASE='ae67e129b5b2c8469d5f70f58c3c719393ef535f'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def old(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def ix(s):return {n['id']:n for n in nodes(yaml.safe_load(s))if'id'in n and'kind'in n}
def own(n):return {k:v for k,v in n.items()if k not in ('actions','elseActions','conditions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if'conditions'in n else {})
CASES=[
('台所でガス臭気あり','現在の室内臭気だけでP11・P12高、EMERGENCY高。事故や複数箇所の確認を待たない'),
('居室で検知器反応。値は不明','室内実反応で両方高。測定値を創作しない'),
('灯内管検査異常なし、13A成分を検出','成分検出という現場報告で両方高。管検査陰性で全原因を否定しない'),
('検知器のガス種設定は13A。検知反応は不明','設定・ラベルを成分検出と誤認しない。不明事項を確認'),
('集合住宅でメーター閉止済み。濃度が変わらない','P07対応済み保持。上流・別経路候補、P08高、P11・P12高'),
('メーター閉止済み。閉止後は未測定','操作済み保持。未測定を低下なしに変えない。他の高条件を照合'),
('室内1か所で反応。メーター閉止後に低下','灯内管・栓・接続具・機器は候補。確定しない。一時低下だけで低へ落とさない'),
('確実に止漏済み。全影響範囲で継続低下後に反応・臭気・警報消失。拡大なし。安全確認・監視継続。社内基準上要請・避難不要。事故等なし','過去の室内反応だけで高固定にしない。既存と今回の解除条件を照合して低への再評価が可能'),
('共用廊下で反応、集合住宅の分岐バルブあり','系統と位置・操作可否・範囲を確認。バルブ存在を操作可能や遮断済みとしない'),
('分岐バルブはないがマルサがある。漏れの特定に時間がかかる','適用範囲と権限確認の上で上流遮断検討高。存在しないバルブの操作を指示しない'),
('PE管で漏えい継続、メーター閉止後も反応継続','スクイズ適用を権限ある担当者の判断候補に。具体的圧着手順を生成しない'),
('管種は不明。止められない','PE管と仮定しない。有効な上流遮断方法確認、既存高を保持'),
('戸建て室内1か所臭気。閉止前で他の異常報告なし','メーター閉止優先。マルサ・スクイズを一律高にしない。室内臭気による要請・避難高は別に適用'),
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
('室内臭気あり、新しい地点で実反応も出た','中の例で上書きせず高優先'),
('これまでの報告から判断に必要な情報は十分','不要な質問を作らず、未完了作業の実施を自然な文章で促す'),
('画像添付・マニュアル確認・目的番号選択の既存回帰','入口・4-9・全体指示・接続ID・質問・トピック間遷移は前版のまま。トピック外の作文なし')]
def main():
 diffdir=R/'diffs/field_concepts_ae67e12';diffdir.mkdir(parents=True,exist_ok=True)
 for name in FILES:
  if old(name)!=(R/name).read_text():
   (diffdir/(name+'.diff')).write_text(''.join(difflib.unified_diff(old(name).splitlines(True),(R/name).read_text().splitlines(True),fromfile='ae67e12/'+name,tofile='field_concepts/'+name)))
 before=ix(old(FILES[1]));after=ix((R/FILES[1]).read_text());changed=[k for k in before if own(before[k])!=own(after[k])];added=sorted(set(after)-set(before))
 assert set(changed)=={'setVariable_priorityGuideFixed','setVariable_priorityPrompt','answer_priority'}
 assert all('P23'in k for k in added)
 assert not set(before)-set(after)
 for name in [FILES[0],FILES[2],FILES[3]]:assert old(name)==(R/name).read_text()
 native=json.loads((R/'validation/native_restart/results.json').read_text())
 assert all(x['success']for x in native['checks']+native['runs']+native['formats'])and native['imageFeatures']['success']
 for name in FILES[:3]:assert native['source_sha256'][name]==sha(R/name)
 log=(R/'validation/contract_tests.log').read_text();assert '\nOK\n'in log
 count=int(re.search(r'Ran (\d+) tests',log)[1])
 with (R/'validation/field_concepts_runtime_cases.csv').open('w',newline='')as f:
  w=csv.writer(f,lineterminator="\n");w.writerow(['ID','input_or_setup','expected','Studio_result'])
  for i,(a,b)in enumerate(CASES,1):w.writerow([f'C-{i:02}',a,b,'NOT_RUN'])
 manifest={'base_commit':BASE,'source':SOURCE,'source_sha256':sha(R/SOURCE),'original_attachment':'originals/20261030_調査遮断供給支障_追加概念.txt','original_attachment_sha256':sha(R/'originals/20261030_調査遮断供給支障_追加概念.txt'),'files':{n:sha(R/n)for n in FILES},'changed_existing_action_ids':changed,'added_action_ids':added,'removed_action_ids':[],'new_variables':[],'unchanged_entry_image_instructions':True,'unittest_count':count,'native_expression_checks':len(native['checks']),'native_number_cases':len(native['runs']),'native_pipeline_cases':len(native['formats']),'native_image_features':native['imageFeatures']['success'],'Studio_cases_NOT_RUN':len(CASES)}
 text='''# 調査・遮断・供給支障の概念追加（2026年10月30日）

## 1. 修正内容の要約

直前に納品したae67e12を基準に、今回の添付「貼り付けたテキスト.txt」の概念を現場アドバイスの判定へ追加した。添付は要望資料として読み、既存の構造を全面置換するシステム指示にはしていない。変更するトピックは3-9だけ。入口、画像分析、全体「指示」はae67e12とバイト単位で同一。

- 配管の区分と上流下流、メーター・機器ガス栓閉止後の変化による原因候補と反証条件。
- 建物・系統・管種に応じた分岐バルブ、引込管遮断装置、マルサ、PE管スクイズの適用確認。
- 道路の開口部から周辺建物・排水口・地下空間へ及ぶ流入調査。
- 現在の室内臭気／実反応、13A成分検出、遮断・換気後の低下なし等による避難と消防警察要請の高条件。
- 接続具、機器本体、隣家・上下階を含む燃焼排ガス、CO等の別の危険の調査候補。
- ガス不出・弱火・圧力低下の初期確認、水分流入と周辺供給支障の追加調査。
- 事実と推定、未測定と陰性、操作と効果、設備の存在と操作可否の区別。

## 2. 変更した条件分岐と変数

既存の入力、トピック間遷移、質問、確認上限、再生成上限、接続・モデル・フローID、画像特徴ノードは変更していない。新しいTopic／Global変数は追加していない。

| 既存ノード | 変更 |
|---|---|
| setVariable_priorityGuideFixed | 固定ガイドの判定手順の前へ追加概念を挿入 |
| setVariable_priorityPrompt | 同じ概念をAIへの実行時入力へ挿入。末尾の内部出力契約は維持 |
| answer_priority | 今回の高条件・供給支障・判定保留の扱いを補足 |

圧力・供給支障を高優先度の完了判定にも反映するため、任意措置P23「圧力・供給支障の確認と調査」を追加。P23は新しいトピック変数ではなく、AIが返す文字列内の措置コード。既存の文字列変数を使い、他の措置と同じ抽出・妥当性確認・高／中／低の欄への配置・未完了集計を行う。供給支障がない場合は対象外とし表示しない。該当時の必要な初期確認・追加調査が残る場合は、P23全体を対応済みにしない。

P23の内部ブロックがない旧形式は検証に失敗する。プロンプトだけを旧トピックへ貼らず、3-9のYAML全文を同じ版で適用する。内部形式不正時の再生成は既存どおり最大1回。

## 3. 添付と既存ルールの整合

| 添付の記述 | 今回の反映方法 |
|---|---|
| 10章の出力形式 | 概念を既存7見出しへ配置。今回まで修復してきた表示と内部契約を維持 |
| 室内の臭気・実反応は高、新しい反応は中 | 現在の高が成立する場合は高を優先。中の例は高条件がない場合だけ |
| 情報不足は判定保留 | 必要性の結論を保留と明示。内部3段階は中を暫定確認枠とし、根拠と確認文へ不足情報を記載。実施状況の要確認とは別 |
| 改善すれば低 | 既存の確実な止漏・継続改善・全影響範囲の安全確認も必要。過去の室内臭気で永久に高固定せず、換気だけの一時改善で下げない |
| 100Aと内径100mm | 提示された管区分は参照し、呼び径Aと実測内径の同一視を避ける。管種・社内基準を確認 |
| 都市ガス13A成分検出 | 実際の成分検出報告と、単なる設定・ラベル・供給種別を区別 |
| メーター取り外し・スクイズ | 適用・権限・安全・社内手順を担当者が確認する候補。AIだけで実行・開管・圧着の詳細を指示しない |
| 圧力・供給支障 | P23へ一つの措置として追加し、各確認項目を根拠と次行動に記載。供給支障だけで消防警察高を作らない |

原因候補は関連する措置の根拠に推定と明記し、事実欄へ混ぜない。次の確認・遮断・調査は各措置とネクストアクション、判断理由を伴う追加質問は確認したいことの文章へ反映する。AI単独で原因や安全を確定しない注意は、関係する作業の説明に添える。

## 4. 修正後のYAML全文

3-9が今回の差し替え対象。比較・保存用に入口と画像分析も全文を収録する。未変更部分も省略していない。

'''
 for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
 text+='## 5. 想定テストケースと期待結果\n\nこれは実モデル・Studioでの確認計画。全件未実行（NOT_RUN）。\n\n| ID | 入力・条件 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'
 for i,(a,b)in enumerate(CASES,1):text+=f'| C-{i:02} | {a} | {b} | NOT_RUN |\n'
 text+=f'''\nオフラインで実施した確認：回帰{count}件、Microsoft.PowerFx.Interpreter 1.8.1による{len(native['checks'])}式の構文・型確認、番号入力{len(native['runs'])}例、内部出力の配置・連動・拒否・完了判定{len(native['formats'])}ケース、画像11項目の特徴が分析と照合の両段へ渡ることを確認済み。全て合格。P23が高で未完了なら完了表示にならず、対応済みなら他の高措置と合わせて完了を判定すること、P23欠落を拒否することも実際の式で確認した。\n\n'''
 text+='''これらは模擬したAI出力を用いた制御・式の試験。実モデルが今回の文章の意味を正しく判定することや、社内資料の正確性を実証したものではない。Studioの読込・ホスト側型推論・写真認識・実ナレッジ検索・応答速度は未検証。

結果ファイル：validation/contract_tests.log、validation/static_results.json、validation/native_restart/results.json、validation/field_concepts_manifest.json。実機計画：validation/field_concepts_runtime_cases.csv。差分：diffs/field_concepts_ae67e12/。

## 6. 人による確認が必要な箇所

- 配管の呼称・区分、遮断設備と実際の遮断範囲、管種、マルサ・スクイズの社内適用基準、作業権限を保安担当者が確認する。添付の内容は外部の正規技術基準として検証していない。
- 室内臭気だけで避難・要請を高とする今回指定のルールを実モデルで確認する。成分検出、仮定の説明、過去と現在、中の例、改善解除、情報不足の扱いを混同していないか確認する。
- 高い優先度のP23は、必要な確認事項の一部だけで対応済みとしない。供給支障の原因は推定にとどめ、担当者の調査結果で更新する。
- 既存の画像機能、ナレッジ、全体指示と組み合わせてStudioで保存・エラー確認・新しい会話による回帰を行う。
- 新しい診断プロンプトの長さによる応答時間・モデル遵守率は実測が必要。正常時のAI呼出し・接続・画像フローは増やしていない。

## 7. 導入と再編集

18_追加概念の導入と反映箇所.mdを参照。編集元はfield_concepts/01_調査遮断供給支障.md。このMDをGitHubで編集するだけではStudioへ反映されない。ビルドして3-9の全文をStudioへ差し替える。今回の導入で入口・画像・全体指示を再変更する必要はない。
'''
 target=R/'17_調査遮断供給支障_変更内容とYAML全文.md';target.write_text(text)
 blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S)
 assert len(blocks)==3
 for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
 manifest['full_yaml_blocks_match']=True
 (R/'validation/field_concepts_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Latest report:',count,'tests;',len(added),'added P23 nodes;',len(CASES),'NOT_RUN Studio cases; 3 full YAML blocks match')
if __name__=='__main__':main()
