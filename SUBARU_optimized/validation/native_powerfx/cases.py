"""Synthetic model replies for native expression execution; no model is contacted."""
from pathlib import Path
BASIC=['火気使用禁止の徹底','電気スイッチ等の操作禁止','火気厳禁表示シート設置','ポケット警報器等の設置','流入ガス・滞留ガスの検知器調査']
RISKS=['継続警報','ガス検知','継続噴出','複数住戸影響','強臭等と遮断不能','その他要請高条件']
REPORT=(Path(__file__).resolve().parents[1]/'fixtures/priority_report_20261023.txt').read_text().strip()
CLOSED='警報器が鳴っている部屋のメーターガス栓を閉めたが濃度変わらず、警報も鳴りやまない'
def row(name,scope='現場',priority='高',status='要確認',effect='対象外',proof='なし'):
 return '|'.join([name,scope,priority,status,effect,'報告'if proof!='なし'else 'なし',proof,'固定ガイドと現場報告','なし','なし'])
def base():return [row(x)for x in BASIC]+[row(x,priority='低',status='未実施')for x in ['消防への要請','警察への要請']]+[row('メーターガス栓閉止')]
def risk():return [k+'|'+('あり|'+({'継続警報':'警報器が鳴りやまない','ガス検知':'ドアポストからLEL1％検知'}[k])if k in RISKS[:2]else '不明|なし')for k in RISKS]
def result(rows=None,risks=None):return '\n'.join(['[[FACTS]]','└受領した現場報告','[[END_FACTS]]','[[RISK]]',*(risk()if risks is None else risks),'[[END_RISK]]','[[MEASURES]]',*(base()if rows is None else rows),'[[END_MEASURES]]'])
def check(variable,**kwargs):return {'variable':'Topic.'+variable,**kwargs}
def cases():
 out=[]
 def add(name,raw,expect,report=REPORT,repair=None,calls=0):out.append({'name':name,'raw':raw,'report':report,'repair':[raw]if repair is None else repair,'repairCalls':calls,'expect':expect})
 closed=base();closed[-1]=row('メーターガス栓閉止','警報器鳴動宅',status='実施済み',effect='未解決',proof=CLOSED);valid=result(closed)
 add('閉止実施済みと効果未解決',valid,[check('P5HighText',contains='警報器鳴動宅）：実施済み　効果：未解決'),check('P5AllDone',equals=False)])
 add('LEL1と継続警報で要請高',result(),[check('P5HighText',contains='消防への要請'),check('P5LowText',notContains='消防への要請')])
 rows=base();rows[-3]=row('消防への要請',priority='低',status='実施済み',proof='消防は要請済み')
 add('消防だけ要請済み',result(rows),[check('P5HighText',contains='消防への要請（現場）：実施済み'),check('P5RequestNext',notContains='消防への要請'),check('P5RequestNext',contains='警察への要請')],report=REPORT+'\n消防は要請済み')
 add('一行不正でも閉止済み保持',result(closed+['誤った|列数']),[check('P5DataOK',equals=False),check('P5HighText',contains='警報器鳴動宅）：実施済み')],calls=1)
 add('他の危険行欠落でも要請高',result(risks=risk()[:-1]),[check('P5RequestHigh',equals=True),check('P5HighText',contains='消防への要請')],calls=1)
 add('危険矛盾は肯定しない',result(risks=risk()+['継続警報|なし|なし']),[check('P5Alarm',equals=False),check('P5LowText',notContains='消防への要請')],calls=1)
 add('旧形式を内部修復','【確認できた事実】\n└旧書式の模擬応答',[check('P5DataOK',equals=True),check('P5HighText',contains='警報器鳴動宅）：実施済み')],repair=[valid],calls=1)
 add('修復失敗は一回で打切り','旧形式',[check('P5AllDone',equals=False),check('優先度判定結果',notContains='└判定保留'),check('P5HighText',contains=BASIC[0])],repair=['不正な修復'],calls=1)
 raw='```text\r\n'+result().replace('|',' ｜ ').replace('\n','\r\n')+'\r\n```'
 add('CRLFと全角区切りと囲み',raw,[check('P5DataOK',equals=True)])
 proof='A室の栓を  閉めた';rows=base();rows[-1]=row('メーターガス栓閉止','A室',status='実施済み',proof=proof)
 add('引用内の連続空白保持',result(rows),[check('P5DataOK',equals=True),check('優先度判定結果',contains=proof)],report=REPORT+'\n'+proof)
 rows=closed+[row('メーターガス栓閉止','別の住戸')]
 add('対象住戸を混同しない',result(rows),[check('P5HighText',contains='警報器鳴動宅）：実施済み'),check('P5HighText',contains='別の住戸）：要確認')])
 complete=[row(x,status='実施済み',proof='全措置実施済み')for x in BASIC+['消防への要請','警察への要請']]
 add('整合確認後の正常完了',result(complete,[k+'|不明|なし'for k in RISKS]),[check('P5DataOK',equals=True),check('P5AllDone',equals=True)],report='全措置実施済み')
 rows=closed+[row('メーターガス栓閉止','警報器鳴動宅',status='未実施')]
 add('同一対象の重複を表示しない',result(rows),[check('P5DataOK',equals=False),check('P5HighText',notContains='警報器鳴動宅）：実施済み')],calls=1)
 add('捏造した実施根拠は不採用',result(base()+[row('消火器設置',status='実施済み',proof='全戸に設置済み')]),[check('P5DataOK',equals=False),check('優先度判定結果',notContains='全戸に設置済み')],calls=1)
 add('空応答の修復制限',None,[check('P5AllDone',equals=False)],repair=[None],calls=1)
 add('改善後の再評価',result(risks=[k+'|なし|改善確認'for k in RISKS]),[check('P5RequestHigh',equals=False),check('P5LowText',contains='消防への要請')],report=REPORT+'\n改善確認：有効止漏済み、影響範囲全体で濃度反応臭気解消、他の高条件なし')
 return out
