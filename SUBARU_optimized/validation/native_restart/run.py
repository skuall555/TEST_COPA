"""Native scalar checks. Requires .NET 8 SDK; downloads fixed NuGet dependencies to /tmp only."""
import argparse,hashlib,io,json,subprocess,urllib.request,zipfile
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
   if n['kind']=='SetVariable'and n.get('value')!=prior.get('value'):expressions.append({'id':ident,'expression':n['value'][1:],'expected':'String'})
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
 inp=build/'input.json';inp.write_text(json.dumps(data,ensure_ascii=False));out=subprocess.run([str(dotnet),str(build/'check.dll'),str(inp)],check=True,capture_output=True,text=True)
 result=json.loads(out.stdout);result['source_sha256']=hashes;(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Native SDK:',len(result['checks']),'expression checks,',len(result['runs']),'number parsing cases')
 if any(not x['success']for x in result['checks']+result['runs']):raise SystemExit(1)
if __name__=='__main__':main()
