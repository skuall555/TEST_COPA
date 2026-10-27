"""Native scalar checks. Requires .NET 8 SDK; downloads fixed NuGet dependencies to /tmp only."""
import argparse,hashlib,io,json,subprocess,urllib.request,zipfile,sys
from pathlib import Path
import yaml
HERE=Path(__file__).resolve().parent;R=HERE.parents[1]
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dotnet',type=Path,required=True);args=ap.parse_args();dotnet=args.dotnet.resolve();build=Path('/tmp/subaru-restart-native');build.mkdir(exist_ok=True)
 for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
  p=build/(pkg+'.nupkg')
  if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
  z=zipfile.ZipFile(io.BytesIO(p.read_bytes()))
  for name in z.namelist():
   if name.startswith('lib/netstandard2.0/')and name.endswith('.dll'):
    out=build/name.removeprefix('lib/netstandard2.0/');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(name))
 sdk=max((dotnet.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')))
 refs=list((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(build.glob('Microsoft.*.dll'))
 rsp=build/'compile.rsp';rsp.write_text('-nologo\n-target:exe\n-out:'+str(build/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(HERE/'Program.cs'))
 (build/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(dotnet),str(sdk/'Roslyn/bincore/csc.dll'),'@'+str(rsp)],check=True)
 files=['1-マニュアル関連入口_optimized.yaml','3-9-緊急保安業務エージェント_optimized.yaml','4-9-画像分析エージェント_緊急保安_optimized.yaml'];expressions=[];indexes=[];hashes={}
 for name in files:
  raw=(R/name).read_bytes();hashes[name]=hashlib.sha256(raw).hexdigest();new=yaml.safe_load(raw)
  old=yaml.safe_load(subprocess.check_output(['git','-C',str(R.parent),'show','61e0c4a:SUBARU_optimized/'+name]))
  before={n['id']:n for n in walk(old)if 'id'in n and 'kind'in n};after={n['id']:n for n in walk(new)if 'id'in n and 'kind'in n};indexes.append(after)
  for ident,n in after.items():
   prior=before.get(ident,{})
   if n['kind']=='SetVariable'and n.get('value')!=prior.get('value'):expressions.append({'id':ident,'expression':n['value'][1:],'expected':'Number'if n.get('variable')=='Topic.優先度様式再試行回数'else 'String'})
   if n['kind']=='AnswerQuestionWithAI'and n.get('userInput')!=prior.get('userInput'):expressions.append({'id':ident+'Input','expression':n['userInput'][1:],'expected':'String'})
   if n['kind']=='ConditionGroup':
    previous_conditions={c['id']:c['condition']for c in prior.get('conditions',[])}
    expressions.extend({'id':c['id'],'expression':c['condition'][1:],'expected':'Boolean'}for c in n['conditions']if c['condition']!=previous_conditions.get(c['id']))
 entry=indexes[0];cases=[]
 for number,label in [(1,'現場対応アドバイス'),(2,'マニュアル確認'),(3,'マニュアル改訂')]:
  for digit in [str(number),str(number).translate(str.maketrans('123','１２３'))]:
   for text in [digit,'['+digit+']','［'+digit+'］',digit+'です',digit+'番',digit+'番です']:
    cases.append({'input':text,'expected':label})
 for text in ['0','4','9','1と2','２ではない','2ですか？','マニュアルを確認したい','1番でお願いします','']:
  cases.append({'input':text,'expected':''})
 data={'expressions':expressions,'normalize':entry['setVariable_normalizePurposeNumber']['value'][1:],'choose':entry['setVariable_purposeFromNumber']['value'][1:],'cases':cases}
 sys.path.insert(0,str(HERE.parent))
 from continuity_build import validator,HEADINGS
 good='\n\n'.join('【'+h+'】\n'+('└未完了あり'if i==4 else '└消防・警察への要請：未実施　根拠：継続警報と換気不能'if i==1 else '└なし'if i in (2,3)else '└報告された事実を保持')for i,h in enumerate(HEADINGS))
 bad=[good.replace('【確認したいこと】','【確認事項】'),good+'\n独自の追記',good.replace('└消防・警察への要請：未実施','└消防・警察への要請：高'),good.replace('└報告された事実を保持','本文の箇条書きなし',1),good.replace('└未完了あり','└全て対応済み または └未完了あり'),good+'\n【確認したいこと】\n└追加質問',good.replace('【初動措置　優先度：高】','【初動措置　優先度：低】'),good.replace('└なし','└なし\n【追加見出し】',1),'', '【危険度判定：極めて高】\n広範囲に拡散']
 data['formatSteps']=[{'variable':n['variable'][6:],'expression':n['value'][1:]}for n in validator()if n['kind']=='SetVariable']
 data['formatCases']=[{'name':'valid','text':good,'accept':True},{'name':'valid CRLF','text':good.replace('\n','\r\n'),'accept':True},{'name':'quoted completion outside status','text':good.replace('└報告された事実を保持','└「全て対応済みではない」と報告',1),'accept':True},{'name':'completed high measures','text':good.replace('：未実施','：対応済み').replace('└未完了あり','└全て対応済み'),'accept':True,'expectWait':False}]+[{'name':'malformed '+str(i),'text':s,'accept':False}for i,s in enumerate(bad)]
 conversation=(R/'originals/20261027_様式逸脱_会話全文.txt').read_text()
 data['formatCases'].append({'name':'actual reported format drift','text':conversation.rsplit('ボット の発言:\n',1)[1],'accept':False})
 field=indexes[1];data['completion']=field['conditionGroup_priorityLoopNeeded']['conditions'][0]['condition'][1:]
 inp=build/'input.json';inp.write_text(json.dumps(data,ensure_ascii=False));out=subprocess.run([str(dotnet),str(build/'check.dll'),str(inp)],check=True,capture_output=True,text=True)
 result=json.loads(out.stdout);result['source_sha256']=hashes;(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Native SDK:',len(result['checks']),'expression checks,',len(result['runs']),'number parsing cases,',len(result['formats']),'format pipeline cases')
 if any(not x['success']for x in result['checks']+result['runs']+result['formats']):raise SystemExit(1)
if __name__=='__main__':main()
