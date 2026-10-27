"""Produce the requested five-part deliverable with all three YAMLs in full code blocks."""
import csv,json,hashlib,re,yaml
from pathlib import Path
from restart_build import BASE,FILES,baseline
from restart_rules import MENU,POCKET_ILLUSTRATION,DETECTOR_ILLUSTRATION
R=Path(__file__).resolve().parents[1]
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
def main():
 cases=[]
 def add(group,source,expected):cases.append((group+str(sum(x[0].startswith(group)for x in cases)+1).zfill(2),source,expected,'NOT_RUN'))
 for source,expect in [
 ('マンションの共用廊下でガス臭がする','現場対応アドバイス。既存のフォルダ判定から専門トピックへ'),
 ('警報器が鳴り続ける場合の社内基準を確認したい','マニュアル確認。警報という単語だけで現場へ振らない'),
 ('消防要請の規定に項目を追加したい','マニュアル改訂'),
 ('ガス業務について相談したい','判断できなければ指定どおりの番号選択'),
 ('規定の確認と変更と現場判断を全部お願い','主目的が特定できなければ番号選択'),
 ('現場でバルブを交換したい','現物作業を規定改訂と混同しない')]:add('AUTO',source,expect)
 for text,label in [('1','現場対応アドバイス'),('１','現場対応アドバイス'),('1です','現場対応アドバイス'),('２番','マニュアル確認'),('[2]','マニュアル確認'),('3','マニュアル改訂'),('３番です','マニュアル改訂'),('マニュアルを確認したい','マニュアル確認'),('規定を変更したい','マニュアル改訂'),('1番でお願いします','現場対応アドバイス')]:add('NUM','目的不明の番号質問に「'+text+'」',label+'。元の発言と選択目的を保持')
 add('NUM','9 → 0 → 1と2','同じ選択肢を再表示し、質問3回で終了。無限ループなし')
 add('NUM','9 → 0 → ３','3回目の明確な回答を受け付けて改訂へ')
 add('NUM','計測基準を確認したい','通常の意味判定へ。計測という語だけで診断へ横取りしない。明示コマンド計測／計測＋空白は維持')
 add('NUM','番号1を選ぶ','案内文だけで終えず既存BeginDialog 64VMOAからcr88f_SUBARU_search.topic.9xYを呼ぶ')
 highs=['ガスが現在も継続して噴出','複数のお客様宅・建物・地点でガス臭','複数地点で検知器・警報器反応','都市ガス警報器が継続鳴動しガスも実検知','強いガス臭が継続','ガス流出が拡大、広範囲へ広がる可能性を報告','ガスを止められない','止めるまで時間を要する','止めようとしたが止められなかった','着火・爆発・火災・中毒の発生可能性が高い','周辺住民・複数のお客様へ影響する可能性を報告','現場だけでは安全確保できず避難・立入規制・交通整理が必要になる可能性を報告']
 for source in highs:add('HIGH',source,'消防・警察要請は高。既発生事故の有無だけで下げない。未報告事実を作らない')
 for source,expect in [
 ('確実な止漏、濃度が継続低下、警報は解消、影響拡大なし。ただし残留ガス等の最終確認は残る','継続中の他の高条件がなければ中。監視継続と悪化時要請'),
 ('確実な止漏・噴出停止、影響範囲全体の安全状態、警報臭気反応解消、避難等不要、他の高条件なし','低へ再評価できる。過去の噴出語だけで高固定しない'),
 ('以前は継続噴出。一度だけ検知器が無反応。停止確認なし','安易に下げない。停止と傾向を必要最小限で確認'),
 ('複数住戸に影響。一地点のみ反応低下。他の住戸は警報・検知が継続','高を維持。影響範囲全体で再評価'),
 ('警報器鳴動宅ドアポストでLEL1％。栓を閉めたが濃度不変・警報継続。未要請','高。操作実施と停止効果を区別し、未要請を低の理由にしない'),
 ('改善後に再びガス噴出・新たな周辺検知','再び高へ'),
 ('火災・爆発・着火・負傷者・体調不良者など明らかな緊急事態','高と要請を先に案内。追加質問の回答を待たない'),
 ('今の噴出・止漏・影響範囲・傾向が不明、明示高条件なし','中（条件確認）として必要な項目だけ質問。未確認を安全扱いしない'),
 ('既に停止可否・警報・影響範囲を報告済み','同じ事項の再質問を避ける'),
 ('消防・警察へ要請済み、危険は継続','実施状況と優先度を区別。取消しを指示しない')]:add('REEVAL',source,expect)
 for source,expect in [
 ('小型警報器が床・棚・設備付近に置かれプローブなし','警報器として外観を照合。存在と設置条件は別判定'),
 ('作業員が筒状プローブを配管へ向けて手持ち検査','可燃性ガス検知器。警報器設置にしない'),
 ('同じ画像に左の置かれた警報器と右の手持ち検知器','別機器として記述。プローブを誤接続しない'),
 ('未知の黒い箱が置かれているだけ','警報器と確定しない'),
 ('画像に警報器が写っていない','描画指定文を観察事実として補わない'),
 ('別サービスで機器イラストを表示する','指定文どおり置かれた警報器／手持ち筒状検知器を区別。別サービスの設定は人が確認')]:add('IMG',source,expect)
 with (R/'validation/restart_runtime_cases.csv').open('w',newline='')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['case_id','input_or_situation','expected','status']);w.writerows(cases)
 changes=[]
 for name in FILES[:3]:
  a={n['id']:n for n in walk(yaml.safe_load(baseline(name)))if 'id'in n and 'kind'in n};b={n['id']:n for n in walk(yaml.safe_load((R/name).read_text()))if 'id'in n and 'kind'in n}
  changes.append({'file':name,'changed':[{'id':k,'fields':sorted(f for f in set(own(a[k]))|set(own(b[k]))if own(a[k]).get(f)!=own(b[k]).get(f))}for k in a if own(a[k])!=own(b[k])],'added':[{'id':k,'kind':n['kind'],'variable':n.get('variable'),'actionId':n.get('actionId')}for k,n in b.items()if k not in a],'removed':sorted(set(a)-set(b))})
 (R/'validation/restart_changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
 text='''# 61e0c4a基準の改修結果（2026年10月27日）

## 1. 修正内容の要約

基準は61e0c4a13b8c68c53947cb03a12d9b9d2d2221fa。新しい作業ブランチでこの版から作り直した。以後の複雑な型初期化・テーブル解析・独自の優先度出力書式は持ち込まない。

- 要件1：入口で文章全体の意味から3目的を推定する。社内規定の確認・変更と現在の現場対応を区別し、危険単語だけで振り分けない。
- 要件2：不明時だけ指定の番号質問を表示。半角・全角数字、「1です」「２番」等を受け付ける。より自由な回答は意味を再判定する。無効時は同じ質問を出し、既存上限の3回で終了する。番号1は既存の緊急保安BeginDialogを実行する。明示的な「計測」コマンドは維持し、「計測基準を確認したい」等の通常文を診断へ横取りしない。
- 要件3〜5：消防・警察の高条件、改善後の中・低への再評価、情報不足の必要最小限の質問を既存の判断プロンプトへ反映。明らかな緊急事態の案内を質問で待たせない。優先度の高・中・低と実施状況を混同しない。
- 要件6：ポケット警報器は置く・設置する監視機器、可燃性ガス検知器は筒状プローブ等を使う手持ち検査機器として説明を統一する。画像・イラスト用の指定文は利用者提示文をそのまま収録する。

手順書検索・改訂、19段のROW検証、修理候補選択、既存の接続、画像割り込み・復帰は維持する。変更したのは以下に示す関連ノードと入口の説明・トリガー例。優先度の回答8見出し、画像の出力区分は維持する。

## 2. 変更した条件分岐と変数の一覧

| 箇所 | 条件・動作 | 変数／遷移先 |
|---|---|---|
| setVariable_purposeDetect → answer_inferPurposeFromText | 既存の単語判定を意味判定へ変更 | 既存Topic.目的分野を再利用。想定外のAI出力は空文字へ正規化 |
| conditionGroup_probeMode／conditionGroup_probeFromPurpose | 診断は「計測」単独または空白付きの明示コマンドだけ。通常の基準質問は意味判定へ | 既存の計測処理は維持 |
| conditionGroup_purposeMissing | 目的不明で質問する既存条件は維持 | 質問文だけ指定の番号メニューへ変更 |
| conditionGroup_purposeRetryLimit | 既存の3回上限を維持 | Topic.目的再試行回数 |
| conditionGroup_rememberPurposeReply | 番号質問後の明確な自然文回答 | 元発言を保持し、選択目的をTopic.追加情報履歴へ追記 |
| conditionGroup_purposeNumberAccepted | 1〜3の明確な番号・定型回答なら受理 | Topic.目的分野へ既存の正規名を設定 |
| conditionGroup_numberPurposeIsField | 1なら既存専門トピックへ、2・3なら既存マニュアル処理へ | 64VMOA／setVariable_classifyRetryCount |
| setVariable_priorityGuideFixed | 消防・警察について現在危険・改善・不足情報を総合判断 | 既存Topic.優先度ガイド取得結果。新たなPower Fx条件分岐や表解析は作らない |
| setVariable_priorityPrompt／answer_priority | 同じ判断ルールを既存8見出しの回答へ反映 | 既存の優先度変数・回答変数を維持 |
| setVariable_prompt1／setVariable_prompt2／answer_photoGuidelineJudge | 外観・配置・プローブ・手持ち検査を機器ごとに区別 | 既存の画像分析入力・出力を維持 |

新規のTopic変数は **Topic.目的選択入力（String）だけ**。用途は目的質問への返信の全角数字等を正規化すること。空文字で初期化する。既存Topic.目的回答も初回参照前に空文字で初期化する。新しいBoolean変数・テーブル変数・Global変数は作らない。

Topic.初回入力は今回の追加処理で書き換えない。返信原文と選択した目的は履歴へ追記し、既存のBeginDialogの2引数でそのまま引き継ぐ。番号1の遷移先は既存のcr88f_SUBARU_search.topic.9xYで、新しいトピック名は作らない。

消防・警察の条件は判断プロンプト内の規則として変更する。AIの意味判断をPower Fxの単語一致だけに置き換えない。高条件が現在あるなら高、確実な停止と改善・残留確認なら中、安全状態と影響解消まで確認できれば低。既報の高条件が継続中なら、単発の改善だけで下げない。

変更IDの完全一覧はvalidation/restart_changes.json、61e0c4aからの差分はdiffs/restart_61e0c4a/に保存する。

## 3. 修正後のYAML全文

各コードブロックは保存したYAMLファイルの全文。未変更部分も含み、途中を省略していない。

'''
 for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
 text+='### エージェント全体の「指示」全文\n\n目的選択の番号を修理候補の番号と混同しないよう、関連箇所だけを更新した。Copilot Studioの全体「指示」へ反映する。\n\n```text\n'+(R/FILES[3]).read_text().rstrip('\n')+'\n```\n\n'
 text+='''## 4. 想定テストケースと期待結果

実施した検証：YAML・ID・Goto・接続・新規未初期化候補の静的検査、契約と模擬AI応答を使う制御テスト37件、Microsoft.PowerFx.Interpreter 1.8.1による変更・追加20式の構文／型確認と45種類の番号入力の式実行。

これらはCopilot Studioの実会話や実モデルによる意味判定・画像認識の成功を示すものではない。以下は実機の確認計画であり、全件NOT_RUN。

| ID | 入力・状況 | 期待結果 | 実機結果 |
|---|---|---|---|
'''
 for ident,source,expected,status in cases:text+='| '+ident+' | '+source.replace('|','／')+' | '+expected.replace('|','／')+' | '+status+' |\n'
 text+='''
全ケースのCSVはvalidation/restart_runtime_cases.csv。制御テストはAIの分類結果を模擬するため、意味判定の正答率を測定したものではない。Power Fxの検証はMicrosoftのスタンドアロンライブラリであり、Studioホストの型推論・読込とは異なる。

## 5. YAML上で判断できず、人による確認が必要な箇所

- Copilot Studioへ各YAMLを保存して、トピックチェッカーのエラーが無いことを確認する。今回の環境からStudioの読込・実会話は実行できていない。
- 全体の「指示」、生成オーケストレーション、他のトピックとの競合により、自然文が入口へ届くか、質問中の番号返信が横取りされないかを実機で確認する。
- 論理名cr88f_SUBARU_search.topic.9xY、フロー、ナレッジ、AI Builderプロンプト参照が利用環境で有効かを確認する。すべて61e0c4aのIDを維持しており、新しい環境の接続IDは推測して作っていない。
- 消防・警察の意味判断、改善傾向、影響範囲、不足質問、緊急時の順序を上記ケースで確認する。安全状態・確実な止漏の現場確認や社内基準の適用は、画像やAI出力だけで代替しない。
- AI BuilderのContextText／ImageInputの実際の動的入力、利用モデル、写真の解像度や遮蔽による識別精度はYAMLだけでは確定できない。外側の画像カスタムプロンプト本文とモデルIDは変更していない。
- この3YAMLには画像生成アクションや画面カードのイラストURL設定が無い。画像生成・画面イラスト用の指定文は09_機器の説明と画像イラスト指定.mdへ保存した。別の画面・生成サービスがある場合は、その設定箇所へ人が適用する。機能が存在しないのに実装済みとはしない。
- 今回の要件外の61e0c4aの仕様は維持した。MS-018等の既存対象、画像の先頭添付の扱い、専門トピックの既存の終了・追加確認の制御は今回変更していない。
- 意味判定用のAI呼出しが入口へ1回追加される。番号の定型回答は追加AI判定なしで受け付けるが、自由文の再判定では再度AIを使う。待ち時間・分類品質は実測が必要。
'''
 (R/'08_61e0c4a基準_改修結果_YAML全文.md').write_text(text)
 (R/'09_機器の説明と画像イラスト指定.md').write_text('# 機器の説明と画像・イラスト指定\n\n## ポケット警報器\n\n床面・地面・棚・設備付近などに置く監視機器。筒状プローブを向ける手持ち検査機器として描かない。\n\n```text\n'+POCKET_ILLUSTRATION+'\n```\n\n## 可燃性ガス検知器\n\n先端の筒・プローブ・吸引部等を対象へ向けて、作業員が手に持って検査する機器。\n\n```text\n'+DETECTOR_ILLUSTRATION+'\n```\n\nYAMLには画像生成や画像URL付き画面カードのアクションがない。この指定文は画像分析の説明にも反映したが、画像自体は生成していない。別画面や生成サービスがある場合は、その設定へ適用する。\n')
 # Verify that each requested full YAML block equals the deployable file, including its content.
 blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
 for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
 manifest={'baseline':BASE,'branch':'codex/subaru-restart-61e0c4a-20261027','yaml_files':{name:{'lines':len((R/name).read_text().splitlines()),'sha256':hashlib.sha256((R/name).read_bytes()).hexdigest()}for name in FILES[:3]},'full_yaml_blocks_match':True,'runtime_cases_not_run':len(cases),'new_topic_variables':['Topic.目的選択入力']}
 (R/'validation/restart_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Saved complete five-part report,',len(cases),'NOT_RUN runtime cases; all 3 full YAML blocks match')
if __name__=='__main__':main()
