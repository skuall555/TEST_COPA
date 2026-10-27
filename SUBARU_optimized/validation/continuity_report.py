"""Current complete deliverable. AI/Studio runtime cases remain explicitly NOT_RUN."""
import csv,difflib,hashlib,json,re,subprocess,yaml
from restart_build import R,FILES
from restart_support import nodes
BASE='7b4724bde0cbf1895d3252574b5e6f84c7118c3d'
def prior(name):return subprocess.check_output(['git','-C',str(R.parent),'show',BASE+':SUBARU_optimized/'+name]).decode()
def own(n):return {k:v for k,v in n.items()if k not in ('actions','conditions','elseActions')}|({'conditions':[{k:v for k,v in c.items()if k!='actions'}for c in n['conditions']]}if 'conditions'in n else {})
def main():
 cases=[
 ('台所の臭気→排水口反応→他の家で警報開始→通報宅の写真→隣家ドアポスト反応・不在で入れず警報継続→LEL3％・換気不能→広範囲に拡散','全経過を元のトピックに累積。入室不能の検知・継続警報で避難・要請とも高。最後の短文でも指定7見出し・定型案内を維持。写真の実施済みを保持'),
 ('入室できず換気できない空間でLEL3％、警報器は継続鳴動','E-01で避難と消防・警察要請が高。10LEL％を待たない。開口部の値を室内濃度と同一視しない'),
 ('不在で入れない部屋のドアポストに検知反応。警報の報告なし','E-01で両方高。警報の追加報告を必須条件にしない'),
 ('換気不能の部屋でガス警報器が鳴り続ける。濃度は未測定','E-01で両方高。濃度を作らず測定の回答待ちで遅らせない'),
 ('「喚起できない」。直前に入室不能と検知・警報継続を報告','換気の意味として文脈を引き継ぐ。両方高'),
 ('二つの住戸で検知器反応があり臭気もある','E-02で両方高。三つになるまで待たない'),
 ('複数の部屋で高濃度反応。臭気の報告なし','E-02で両方高。臭気もあるという事実を作らない'),
 ('複数施設で反応し、排水口から多数の需要家への流入可能性あり','E-02で両方高。流入の可能性と確定を区別'),
 ('3軒以上で検知反応、バルブがなくガス遮断不能','E-02で両方高。設備があると捏造せず要請・避難を先行'),
 ('「広範囲に拡散している。」という短い続報だけ','質問待ちのトピックに引き継ぎ、両方高。親の自由回答へ切り替えない'),
 ('消防・警察は要請済み。避難誘導も実施済みだが危険継続','高の対応済みとして保持。優先度と実施状況を分け、必要な追加範囲を評価'),
 ('他の家の一台の警報器が鳴り始めたとだけ報告','警報器台数・鳴動住戸を勝手に複数にしない。周辺調査全完了としない'),
 ('表示シートの設置写真だけを送信','表示シートの実施済みを保持。火気使用禁止の周知徹底まで自動完了にしない'),
 ('換気できないと既に報告済み','同じ換気可否を繰り返し質問せず、要請・避難を先行。換気扇の電源操作を案内しない'),
 ('広域避難が必要という報告、具体的な範囲は未確認','「周辺数軒」「半径何m」を創作しない。影響範囲と現場基準で確認'),
 ('確実な止漏と影響範囲全体の改善・安全を後から報告','現在の高条件の解消を照合し、既存の再評価を適用。過去語で高固定しない'),
 ('AIが「危険度判定」「直近の対応措置」へ様式変更','様式不合格。一度再生成し、合格時だけ固定7見出しで表示'),
 ('低欄の行が「消防・警察への要請：高」となった','実施状況の書式に不合格。生の回答を送信しない'),
 ('二回とも様式不合格、または回答が空','再生成は最大1回。案件保存・通常表示へ進めず既存のエラー終了経路へ。判定保留の架空の全項目を生成しない'),
 ('確認できた事実に「全て対応済みではない」と含まれる','完了欄が未完了ありなら確認を継続。全文の単なる部分一致で終了しない'),
 ('確認待ち中に連続で画像送信、その後テキスト続報','既存の画像割り込みと質問への復帰を維持。画像だけを止める設定変更はしない'),
 ('親エージェントがトピック外で直接応答','このYAMLの検査は通らない。Studioの実行履歴で発生元を特定し、該当の生成・フォールバック設定を確認'),
 ]
 rows=[('CONT'+str(i+1).zfill(2),a,b,'NOT_RUN')for i,(a,b)in enumerate(cases)]
 with (R/'validation/continuity_runtime_cases.csv').open('w',newline='')as f:
  w=csv.writer(f,lineterminator='\n');w.writerow(['case_id','input_or_situation','expected','status']);w.writerows(rows)
 manifest={'base_commit':BASE,'runtime_cases_not_run':len(rows),'changes':[],'yaml_files':{},'scope':'Scalar format guard executed offline; routing/AI safety decisions in Studio NOT_RUN'}
 folder=R/'diffs/continuity_7b4724b';folder.mkdir(parents=True,exist_ok=True)
 for name in FILES:
  old=prior(name);new=(R/name).read_text()
  if old!=new:(folder/(name+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='7b4724b/'+name,tofile='continuity_fix/'+name)))
  if name.endswith('.yaml'):
   a={n['id']:n for n in nodes(yaml.safe_load(old))if 'id'in n and 'kind'in n};b={n['id']:n for n in nodes(yaml.safe_load(new))if 'id'in n and 'kind'in n}
   manifest['changes'].append({'file':name,'changed':[k for k in a if own(a[k])!=own(b[k])],'added':[{'id':k,'kind':n['kind'],'variable':n.get('variable')}for k,n in b.items()if k not in a],'removed':sorted(set(a)-set(b))})
   manifest['yaml_files'][name]={'lines':len(new.splitlines()),'sha256':hashlib.sha256((R/name).read_bytes()).hexdigest()}
 native=json.loads((R/'validation/native_restart/results.json').read_text())
 assert all(x['success']for x in native['checks']+native['runs']+native['formats'])
 for name,data in manifest['yaml_files'].items():assert native['source_sha256'][name]==data['sha256']
 text='''# 様式逸脱と避難・要請の連動条件の修正

## 1. 修正内容の要約と原因の切り分け

前回7b4724bを基準に修正。利用者提供の会話全文はoriginals/20261027_様式逸脱_会話全文.txtに保存した。冒頭の台所臭気、排水口反応、他住戸の警報、画像、隣家ドアポスト反応・不在・警報継続、LEL3％と換気不能まで進み、「広範囲に拡散している。」への回答で7見出しと定型の案内が消える。

会話ログだけでは、親の生成オーケストレーターが回答したのか、同じanswer_priorityが別様式を生成したのかは断定できない。以前のYAMLは「空でなければ送信」するため、同じトピック内でも様式逸脱を通してしまう構造だった。これを今回修正する。初期のexplanation_of_tool_callや検索不成立の表示は開発用UIの表示も含むため、それだけで最終回答の生成元を断定しない。

- 指定の7見出し・順序・本文の行形式・優先度欄の実施状況・完了欄を送信前に検査し、合格した本文を固定見出しで組み立てる。不正なら同じAIノードで再生成は1回だけ。2回目も不正なら通常の表示・案件保存へ進まず、既存のエラー終了経路で送信停止を通知する。
- ①入室不能または換気不能の空間でガス検知・濃度がある、またはガス警報継続なら、避難誘導と消防・警察の出動要請をともに高。開口部のLEL3％や1％だけで下げず、10％以上を待たない。
- ②複数の部屋・家・施設等で反応があり、臭気／高濃度、多数需要家への流入可能性、3軒以上反応＋バルブなしで遮断不能のいずれかがあれば両方高。既存のより厳しい高条件も維持する。
- 明示された広範囲拡散でも両方高。人身被害や事故発生を待たず、要請・避難を未実施のネクストアクションの先頭に置く。実施済み報告と現在の優先度は分ける。具体的な避難軒数・距離を創作しない。
- 「広範囲」「まだ入れない」等の短い続報は質問中のトピックへ返すよう全体「指示」を補強する。全体「指示」だけでStudioのオーケストレーション設定が物理的に変わるわけではない。

## 2. 変更・追加した変数

| 追加変数 | 型 | 用途 |
|---|---|---|
| Topic.優先度表示原文 | String | 今回生成された回答を検査用に保持 |
| Topic.優先度表示組立 | String | 固定の7見出しと検査した本文を連結 |
| Topic.優先度表示検証 | String | 合格／不合格。Boolean変数ではない |
| Topic.優先度表示区分 | String | 一区分ずつ本文を抽出して検査 |
| Topic.優先度様式再試行回数 | Number | 各再判定の開始時0、様式再生成は1回上限 |

既存の初回入力・追加情報履歴・優先度判定結果・画像用Global変数を維持する。新しい表変数・Global変数・型宣言ブロックは作らない。Splitは文字列の区分抽出に使用し、そのテーブルを変数へ保存しない。各式を短い段階に分ける。

## 3. 変更した条件分岐と送信経路

| 箇所 | 変更 |
|---|---|
| setVariable_priorityGuideFixed／setVariable_priorityPrompt／answer_priority | ①②をE-01／E-02として連動、避難・要請・現在事実・実施済み範囲を明示。様式指示を補強 |
| answer_priority直後 | 見出しの一意性、順序、本文行、措置状態、完了欄の短い検査を追加 |
| conditionGroup_priorityFormatRetry | 不合格かつ再試行0なら1に増やしてanswer_priorityへ。初期化を飛び越して戻るため上限が維持される |
| conditionGroup_priorityFormatAccepted | 合格時だけ固定見出しの組立結果をTopic.優先度判定結果に設定 |
| conditionGroup_prioritySucceeded | 空でないことだけでなく、様式検査の合格を要求。既存の案件保存もこの後 |
| conditionGroup_priorityLoopNeeded | 回答全文の「全て対応済み」部分一致を廃止し、完了欄の一行だけで継続判定 |
| sendActivity_priorityFailed | 空回答・様式不正では未検証の業務回答を送信しない旨を通知。架空の全項目の判定保留や実施済みの取消しを生成しない |
| エージェント全体の指示 | 短い続報の受け渡し・親の独自回答禁止を追記 |

既存の質問・画像割り込み・修理への移動・マニュアル目的変更・接続IDは維持する。入口と画像分析のYAMLは前回とバイト単位で同一。再生成時にAIが全く同じ結果を出す場合でも再試行は1回で打ち切る。

## 4. 既存条件との競合と限界

- 従来の避難「軽微臭気のみなら低」「人身危険等なら高」は維持するが、E-01／E-02と現在の広範囲拡散を高条件に追加する。人身被害の情報がないだけで低にしない。
- 単一の警報報告を複数の警報器に増やさず、警報を聞いただけで周辺調査全体を対応済みにしない。表示シートだけで周知徹底まで完了にしない。
- 既報の換気不能・不在を繰り返し質問せず、高の案内を先に出す。危険区域への進入や換気扇の電源操作は勧めない。改善後の再評価と確実な安全確認は従来どおり。
- 様式検査は危険度の意味判断を検証するものではない。例えば行書式を守っていても、理由と配置が意味上矛盾する可能性は残る。実モデルで高判定と配置を確認する。
- トピック外で親AIが生成した回答は、このYAMLの検査を通らない。以下の導入・診断手順で発生元を確認する。割り込みを一律禁止すると画像受付が壊れるため、allowInterruptionは維持した。

## 5. 修正後のYAML全文と全体「指示」

3YAMLを未変更部分も含めて全文収録する。今回差し替えるのは3-9と全体「指示」。

'''
 for name in FILES[:3]:text+='### '+name+'\n\n```yaml\n'+(R/name).read_text().rstrip('\n')+'\n```\n\n'
 text+='### エージェント全体の「指示」全文\n\n```text\n'+(R/FILES[3]).read_text().rstrip('\n')+'\n```\n\n'
 text+='## 6. テストケースと期待結果\n\n| ID | 入力・状況 | 期待結果 | Studio実機 |\n|---|---|---|---|\n'
 for row in rows:text+='| '+' | '.join(x.replace('|','／')for x in row)+' |\n'
 text+='\n検証結果：静的検査と回帰テスト43件。Microsoft.PowerFx.Interpreter 1.8.1で'+str(len(native['checks']))+'式の構文・型、目的番号45入力、様式検査'+str(len(native['formats']))+'入力を実行。正常形式、CRLF、誤った見出し・行・完了欄、実際に報告された逸脱回答、完了欄以外の「全て対応済み」を確認した。濃度やE-01／E-02の意味分類の実行試験ではない。\n\n'
 text+='''Copilot Studio読込・実会話・実モデルの危険度判断は未実行。上記22ケースは全件NOT_RUN。前回の48＋103ケースも関連する回帰対象。ログはvalidation/contract_tests.log、実際の式実行はvalidation/native_restart/results.json、今回の変更・対象SHAはvalidation/continuity_manifest.json。

## 7. 人による確認と導入・診断

1. 現在の3-9と全体「指示」を控え、今回の同名ファイルへ全文置換して保存する。入口・画像分析・外側の画像カスタムプロンプトは変更不要。トピックチェッカーを確認し、既存会話ではなく新しいテスト会話で全文と同じ順番を試す。
2. テスト画面のアクティビティマップ／実行履歴で、「広範囲に拡散している。」直後の実行元を確認する。正常な経路はquestion_priorityUpdateへの返信、履歴同期・追記、goto_priorityAgain、setVariable_priorityPrompt、answer_priority、様式検査、案件保存、question_priorityUpdateでの表示。
3. answer_priorityが実行され、その出力自体が別様式ならトピック内AIの逸脱。今回の検査では不合格として生の回答を表示しない。一方、answer_priorityや検査が実行されず、生成応答・別トピック・会話ブースティング等が実行されていればトピック外の応答。該当の生成・フォールバック・トピック選択設定を確認する。未確認の設定名や接続はYAMLに創作していない。
4. 親側の生成やシステムトピックの設定はこのリポジトリに含まれておらず、ここから変更できていない。全体「指示」の補強だけで横取りが完全に止まったとは扱わない。画像の割り込みと復帰が引き続き動くことも確認する。
5. ①②の判定・数値・最新情報・優先度欄の配置と、実施済み報告の保持を実モデルで確認する。式の構文合格をStudioの型推論や実AIの正答率として扱わない。ガス種や社内閾値、避難範囲・区域解除は保安責任者が確認する。

再生成：validation/rebuild.py → validation/validate.py → test_contracts／test_restart／test_additional → validation/native_restart/run.py → validation/continuity_report.py。restart_report.pyとadditional_report.pyも最新報告書の生成へ転送する。

今回の差分だけを戻す場合は、3-9と全体「指示」を7b4724bの同名ファイルへ戻す。
'''
 (R/'13_様式固定と避難要請連動_YAML全文.md').write_text(text)
 blocks=re.findall(r'```yaml\n(.*?)\n```',text,re.S);assert len(blocks)==3
 for name,block in zip(FILES[:3],blocks):assert block+'\n'==(R/name).read_text().rstrip('\n')+'\n'
 manifest['full_yaml_blocks_match']=True
 (R/'validation/continuity_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
 print('Complete report:',len(rows),'NOT_RUN Studio cases; all YAML blocks match')
if __name__=='__main__':main()
