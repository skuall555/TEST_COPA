"""Complete current deliverable, incremental diffs, source hashes and Studio test plan."""
import csv,difflib,hashlib,json,re,subprocess,yaml
from restart_build import R,FILES
from restart_support import nodes
from itemized_build import MEASURES
from image_features_build import ITEMS,lit
BASE='640af62021dbb4c5bc45917cf7b1f264ab40e655'
def prior(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
def index(text):return {n['id']:n for n in nodes(yaml.safe_load(text))if 'kind'in n and 'id'in n}
def main():
 cases=[
 ('今回の全文と写真を順に入力する','入室不能の別室のLEL1％はE-01。消防警察・避難は高。通報宅の閉止・窓操作と別室を分け、屋外からの流入を考慮'),
 ('内部P11の優先度は高、実施状況は未実施','P11の表示行は必ず高欄。状態は未実施として表示'),
 ('内部P11が中または低','判定値に対応する欄へだけ配置。根拠の意味自体が不整合ならAI判定の問題として切り分け'),
 ('EMERGENCYは高、P11・P12の個別判定が低','連動条件を優先し両方高に統一。根拠も連動根拠へ統一'),
 ('E-01で両方高、要請・避難の報告なし','ネクストアクション先頭へ要請と避難の対応確認・未対応時の実施を表示'),
 ('要請・避難済みで危険が継続','実施済みを保持。危険と優先度は別で、未実施へ戻さない'),
 ('排水口を調査し反応、別室は未入室','排水口のP05は対象範囲付きの対応済み。別室の追加調査はP20で別に残す'),
 ('排水口を調査し反応なし／0％','調査した事実は対応済み。無反応を未調査としない'),
 ('メーター閉止済み、別室のメーター操作は未確認','P07の閉止対象を保持。必要な別対象の遮断をP22へ分ける'),
 ('換気を試みたが屋外から臭気が入り窓を閉めた','試行と流入防止閉止を保持。単に未実施へ戻さず、その窓の換気継続を無条件に勧めない'),
 ('写真に映らないが設置済みの明確な報告あり','写真の見えなさだけで実施済みを取り消さない'),
 ('今回の2コマ写真：全景の赤い縦長の注意表示','左の全景も確認し、火気厳禁表示シート等を特徴と文言で照合。立体の自立表示も対象'),
 ('今回の写真：排水口脇の小型黒ケース・黄橙ボタンの警報器','隣の検知器とは別の対象として照合。型番や濃度の不鮮明さだけで設置を落とさない'),
 ('今回の写真：置かれた検知器と排水口の採取ホース等','手が写っていることを必須にせず配置と採取先・使用状態を確認。数値確認と調査実施を分ける'),
 ('表示シートは全景、警報器と検知器は拡大に写る','複数コマを全て確認し、一つのコマだけで他のアイテムを未確認にしない'),
 ('機器を置いただけで採取先や使用状態が全く不明','調査中と断定しない。必要な当て先等を具体的に確認'),
 ('未知の黒い箱だけが置かれる','色や置き場所だけでポケット警報器と断定しない'),
 ('プローブ付き機器を手持ちして検査','可燃性ガス検知器。ポケット警報器設置にしない'),
 ('警報器の数値は不鮮明だが本体と設置位置は分かる','設置と濃度可読性を分離'),
 ('別の写真で消火器・表示シート等が見えない','画像外の項目は原則判定なし。全項目の撮り直し要求や未実施の断定をしない'),
 ('ポケット警報器の特徴ノードだけを書き換える','他の特徴を変えず、第1段と第2段の両方へ新しい特徴を渡す'),
 ('個別MDだけをGitHubで編集して稼働中Studioを使う','自動取得はされない。Studioノード編集、または再生成・再適用が必要'),
 ('画像事実には警報器があるが措置済みに落ちる','第2段の設置基準・MS-ID・取得した撮影要領を確認。第1段の識別ミスとは区別'),
 ('CHECKで建物種別が判断に必要','不足情報・影響する判定・条件が危険な理由・教えてほしいことを文章にする'),
 ('既に要請・避難は高と判断可能、上流遮断の情報だけ不足','高の案内を保留しない。その判断と残る確認を分けて文章で説明'),
 ('報告が優先度判断に十分','追加質問を増やさず提示した未完了作業の実施を促す。安全確認完了とは混同しない'),
 ('必須Pコード欠落、状態に高を入れる、未知マーカー、区切り不正','内部形式不合格。再生成は1回だけ。不正データの通常表示・案件保存をしない'),
 ('高の措置に要確認が一つ残る','高優先度の完了状況は未完了あり。AIの自由な完了宣言に依存しない'),
 ('既存の10往復上限に達して高が未完了','現状提示後に確認を終了。初動措置完了の表示や完了後の調査工程へ落ちない'),
 ('親AIがトピック外で回答する','今回の処理を通らないため、実行履歴で生成元・公開版を切り分ける'),
 ('画像割り込み後にテキスト続報、マニュアル目的変更、修理依頼','既存の割り込み・復帰・遷移・原文履歴の保持を回帰確認'),
 ]
 rows=[('ITEM'+str(i+1).zfill(2),a,b,'NOT_RUN')for i,(a,b)in enumerate(cases)]
 with (R/'validation/itemized_runtime_cases.csv').open('w',newline='')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['case_id','input_or_situation','expected','studio_status']);w.writerows(rows)
 manifest={'base_commit':BASE,'branch':'codex/subaru-restart-61e0c4a-20261027','changes':[],'yaml_files':{},'feature_sources':{},'runtime_cases_not_run':len(rows),'scope':'Native scalar execution and prompt wiring; Studio and image/AI model accuracy NOT_RUN'}
 folder=R/'diffs/itemized_640af62';folder.mkdir(parents=True,exist_ok=True)
 for name in FILES:
  old=prior(name);new=(R/name).read_text()
  if old!=new:(folder/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='640af62/'+name,tofile='itemized_20261030/'+name)))
  if name.endswith('.yaml'):
   a=index(old);b=index(new);av={n['variable']for n in a.values()if isinstance(n.get('variable'),str)};bv={n['variable']for n in b.values()if isinstance(n.get('variable'),str)}
   manifest['changes'].append({'file':name,'changed':[{'id':k,'fields':[f for f in own(a[k])if own(a[k])[f]!=own(b[k]).get(f)]}for k in a if k in b and own(a[k])!=own(b[k])],'added':[{'id':k,'kind':n['kind'],'variable':n.get('variable')}for k,n in b.items()if k not in a],'retired_ids':sorted(set(a)-set(b)),'new_variables':sorted(bv-av)})
   manifest['yaml_files'][name]={'lines':len(new.splitlines()),'sha256':hashlib.sha256((R/name).read_bytes()).hexdigest()}
 image=index((R/FILES[2]).read_text())
 for code,name in ITEMS:
  p=R/'image_features'/(code+'_'+name+'.md');assert image['setVariable_imageFeature'+code]['value']==lit(p.read_text())
  manifest['feature_sources'][p.name]={'variable':'Topic.特徴_'+name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
 native=json.loads((R/'validation/native_restart/results.json').read_text())
 assert all(x['success']for x in native['checks']+native['runs']+native['formats'])and native['imageFeatures']['success']
 for name,details in manifest['yaml_files'].items():assert native['source_sha256'][name]==details['sha256']
 text='''# 措置別の優先度配置・画像特徴の分離・確認文の修正（2026年10月30日）

## 1. 修正内容の要約

前回640af62を基準とする。今回の報告では「消防・警察は高と判断」と書きながら低欄に置かれる意味上の矛盾が残っていた。従来の7見出し・行形式の検査では、この矛盾までは防げなかった。

- AIに高・中・低の欄全体を書かせず、措置別の優先度・状態・根拠を分けた文字列で返させる。YAMLが優先度を使って表示欄へ配置し、完了状況も高措置の状態から計算する。E-01／E-02等の緊急連動が高なら消防・警察と避難をともに高へ統一し、その根拠で表示する。
- 画像特徴を11個の独立した設定ノードとMDに分離する。ポケット警報器だけを編集すれば、他の特徴を変えず両段の画像処理へ渡せる。表示シートの立体形状・黒ケースの警報器・手を離してホース等で排水口を調査する状態を追加する。
- 設置・調査・濃度の可読性を分ける。実施済み範囲を保持し、未入室の別室等の追加作業を別項目へ分ける。屋外臭気が流入して閉窓した経緯を単なる換気未実施へ戻さない。
- 「確認したいこと」は箇条書きの短問をやめ、不足情報・判断への影響・危険条件・何を教えてほしいかを文章で説明する。報告が十分なら追加質問を増やさず未完了作業を促す。

今回更新する導入ファイルは3-9と4-9の2つ。全体「指示」と入口は前回と同一。新しい外部サービス、Power Automateフロー、モデル参照、ナレッジ参照は追加していない。

## 2. 変更・追加した変数と編集箇所

表変数・Boolean変数を新設せず、文字列だけで内部データを分解・配置する。既存のNumber型の様式再試行回数を再利用し、再生成は従来どおり最大1回。

| グループ | 用途 |
|---|---|
| Topic.判定優先度／判定状態／判定根拠／判定表示行 | 一措置ずつの作業用文字列。優先度を状態の位置に書かせない |
| Topic.判定高欄／判定中欄／判定低欄 | 優先度に従って行を連結。AIにこの3欄を作文させない |
| Topic.判定連動／判定連動理由 | 避難と要請を高に連動させる一つの判定と根拠 |
| Topic.判定未完了／判定要請優先度／判定要請状態／判定避難状態 | 高の完了状況と先頭の要請・避難アクションを組み立てる |
| Topic.判定事実／判定次行動／判定確認文／判定残余 | 現場事実、次行動、説明文、余分なブロックや文字の検査 |
| Topic.優先度表示原文等 | 既存の文字列変数を再利用して検査・組立。原文・追加履歴は従来経路で保持 |
| Topic.特徴_各アイテム／Topic.画像特徴カタログ | 11個の独立した特徴設定と、それらを毎回読み込む文字列カタログ |

新規変数・変更フィールド・追加／廃止IDの完全一覧はvalidation/itemized_manifest.json。特徴ごとのノードID・編集方法・MDは16_アイテム別特徴の編集と導入.mdにまとめた。GitHubのMDを編集しただけで稼働中Studioが自動取得する構成ではない。Studioの該当ノードを編集するか、MDを変更して再生成・再適用する。

## 3. 変更した条件分岐とデータの流れ

AIの内部出力はFACTS、EMERGENCY、措置コードP01〜P22、NEXT、CHECKの文字列ブロック。措置行には優先度・状態・根拠を区切って返させる。ユーザーへはこの内部形式を表示しない。

| 処理 | 変更 |
|---|---|
| answer_priority | ガイドと原文・履歴に基づき、内部契約の文字列を生成。確認文は文章にする |
| 内部契約の検査 | 必須コード、一意なマーカー、区切り数、許可された優先度と状態、根拠、余分な文字を短い式で検査 |
| 措置別の配置 | 優先度が高なら高欄、中なら中欄、低なら低欄へだけ連結。対象外は追加項目だけ許可 |
| 緊急連動 | 連動が高ならP11・P12を高に統一し、根拠も連動根拠へ。未完了の要請・避難の案内を次行動の先頭へ |
| 完了判定 | 高欄の措置に未実施または要確認があれば未完了あり。自由な完了宣言を受け取らない |
| 不正時 | 同じAIノードで再生成1回。再び不正なら既存の送信停止経路へ。案件保存は合格後だけ |
| 確認往復の上限時 | 既存の10回上限は維持。未完了の現状提示後に終了し、完了表示・次工程へ進む経路を止める |
| 画像 | 11個の特徴ノード→カタログ→既存のContextTextと第2段の指示へ。既存の画像割り込み・Global履歴への追記・復帰を維持 |

措置コード一覧：

| コード | 表示名 | 扱い |
|---|---|---|
'''
 for i,(code,name)in enumerate(MEASURES):text+='| '+code+' | '+name+' | '+('基本項目'if i<13 else '必要時のみ。対象外可')+' |\n'
 text+='''
## 4. 既存条件との競合と解決

- 旧方式の「高と書いたが低欄」は、判定値と表示欄を二重に作文させていた。今回は判定値だけで欄を決める。ただしAIが判定値自体を低に誤り、理由だけ高と述べる場合はAI判定の不整合であり、配置処理だけでその意味を保証しない。原文のP11とEMERGENCYを見て切り分けられるようにする。
- 従来の7見出し生成指示と内部契約を混在させないよう、関連する出力指示を置換した。ユーザーには同じ7見出しをYAMLが組み立て、「確認したいこと」の本文だけは説明文にする。前回追加した関連部分の旧見出し解析22ノードを置換した。無関係の質問・接続・修理・検索のIDは維持する。
- 実施した調査と全域の未確認を分ける。P05の確認済み範囲は保持し追加はP20、P10の追加範囲はP21、別対象の供給遮断はP22で示す。確認していない全域まで完了にしない。
- 窓を開けて屋外臭気が流入した場合は、試行と閉窓を保持して流入元を照合する。換気停止を一度も行っていないことと同一視せず、無条件にその窓の換気継続を案内しない。
- 旧「手に持つ検知器」の例は手持ちを必須条件と誤読され得た。手が写らない状態でも、採取部・接続・排水口等との関係・使用状態を確認する。単に置いただけで測定中とはしない。
- 画像に写らない項目を未実施の証拠としない。設置、識別、設置条件、調査、濃度可読性を分離する。カタログは識別補助であり、写真に存在する証拠でも、撮影要領本文にない条件を作る根拠でもない。
- 親AIがトピック外で返す応答は、この処理を通らない。前回の全体「指示」は保持し、必要なら実行履歴で生成元を確認する。
- 既存の確認上限到達後、未完了のまま完了表示へ進み得る経路があった。10回上限自体は維持し、現状提示後は終了させる。未完了措置を完了扱いにしない。

## 5. 修正後のYAML全文

以下は3トピックの全文。未変更の入口も含む。今回導入するのは3-9と4-9。各コードブロックは同名の実ファイルと一致する。

'''
 for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
 text+='## 6. テストケースと期待結果\n\n以下はStudio実機の確認計画であり、全件NOT_RUN。今回の参照写真に関する期待結果は、利用者の報告と参照写真の位置関係を特徴文へ取り込んだもので、Studioでの認識成功を実証したものではない。\n\n| ID | 入力・状況 | 期待結果 | Studio結果 |\n|---|---|---|---|\n'
 for row in rows:text+='| '+' | '.join(x.replace('|','／')for x in row)+' |\n'
 text+='\n実施済みの検証：静的検査、契約・制御・変更範囲・特徴単独編集の回帰48件。Microsoft.PowerFx.Interpreter 1.8.1で'+str(len(native['checks']))+'式の構文・型、目的番号45入力、措置別の配置・連動・不正形式'+str(len(native['formats']))+'ケース、11項目の特徴全文が第1段と第2段の指示へ渡ることを確認した。\n\n'
 text+='''これらはStudioホストの型推論・読込・実モデルの判断・画像認識・実ナレッジ取得の検証ではない。配置試験では模擬したAIの内部出力を実際のPower Fx式へ通している。意味分類を模擬して正答率を主張するものではない。特徴の単独編集試験では、ポケット警報器だけの変更が他の特徴ノードを変えないことも確認した。

結果：validation/contract_tests.log、validation/native_restart/results.json、validation/itemized_manifest.json。実機計画：validation/itemized_runtime_cases.csv。前回の関連ケースも回帰対象とする。

## 7. 人による確認・導入・更新方法

導入と今後の個別編集は16_アイテム別特徴の編集と導入.mdを参照。今回は3-9と4-9の2YAMLを同じ版で適用する。全体「指示」・入口・AI Builder外側プロンプト・モデルID・接続IDは変更不要。

- Studioへ保存し、トピックチェッカーのエラーを確認する。単純な文字列・数値初期化と短い式に分けたが、この環境からStudioへの読込を実行していない。
- 今回の写真で、表示シート、警報器、排水口調査を別々に確認する。小さい本体・遮蔽・画質・複数コマによる見落とし、モデルの識別精度はプロンプトだけで保証できない。実機で画像事実→要領照合→履歴反映のどこで落ちるか確認する。
- 特徴の定義を変更した場合は対象が写る写真と写らない写真の両方で確認する。GitHubのMDはビルド元であり、外部ファイルを毎回ネット取得するフローではない。Studioの特徴ノードは各画像処理の冒頭に実行され、その値を実行時にカタログへ組み込む。
- E-01／E-02、現在の危険と改善後の再評価、対象場所、既存の実施済み、窓操作の経緯を実モデルで確認する。濃度の換算・閾値、社内基準や機器、避難範囲・安全確認は保安責任者が確認する。
- 理由と判定値の意味整合、説明文の適切さ、必要な追加作業の落とし漏れは、構文や型検査の合格で保証されない。内部P11が高なのに表示が低なら、旧版・別応答経路を確認する。P11自体が低なら、AIの判定根拠を確認する。
- 制御ノード数は増えるが、正常時の優先度AI呼出し・既存の画像AI呼出しを増やしてはいない。応答時間・内部契約の遵守率・最大長はStudioで実測する。

再生成：validation/rebuild.py、静的検査：validation/validate.py、回帰：unittest discoverでvalidation配下のtest_*.py、式実行：validation/native_restart/run.py --dotnet /tmp/subaru-dotnet/dotnet、報告書：validation/itemized_report.py。

今回分だけ戻す場合は3-9と4-9を640af62の同名ファイルへ戻す。今回追加した特徴ライブラリだけを旧3-9へ組み合わせる運用は、別途確認してから行う。
'''
 target=R/'15_措置別振分けと画像特徴分離_YAML全文.md';target.write_text(text)
 blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
 for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
 manifest['full_yaml_blocks_match']=True
 (R/'validation/itemized_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Complete report:',len(rows),'NOT_RUN Studio cases; all YAML blocks and 11 feature sources match')
if __name__=='__main__':main()
