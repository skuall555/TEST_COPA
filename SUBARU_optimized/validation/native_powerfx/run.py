"""Check priority expressions with Microsoft's standalone engine, not the Studio host.
Uses direct csc invocation so restricted cloud environments need no NuGet named mutex.
"""
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
def export(source):
 data=yaml.safe_load(source.read_text());expressions=[]
 for n in walk(data):
  if n.get('kind')=='SetVariable'and n['id'].startswith(('setVariable_priority','setVariable_p5')):
   expressions.append({'id':n['id'],'target':n['variable'],'expr':n['value'][1:],'kind':'SetVariable'})
  if n.get('kind')=='ConditionGroup'and n['id'].startswith('conditionGroup_priority'):
   expressions.extend({'id':c['id'],'target':'','expr':c['condition'][1:],'kind':'Condition'}for c in n['conditions'])

 seeds=[n for n in data['beginDialog']['actions'] if n.get('id','').startswith('setVariable_p5')]
 for n in walk(data):
  a=n.get('actions')
  if isinstance(a,list)and any(x.get('id')=='setVariable_priorityRaw'for x in a):
   start=next(i for i,x in enumerate(a)if x.get('id')=='setVariable_priorityRaw');end=next(i for i,x in enumerate(a)if x.get('id')=='conditionGroup_prioritySucceeded');pipeline=a[start:end];break
 from cases import cases
 return {'expressions':expressions,'seeds':seeds,'pipeline':pipeline,'cases':cases()}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--dotnet',type=Path,required=True);ap.add_argument('--build-dir',type=Path,default=Path('/tmp/subaru-native-powerfx'));args=ap.parse_args()
 dotnet=args.dotnet.resolve();sdk=max((dotnet.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')));build=args.build_dir;build.mkdir(parents=True,exist_ok=True)
 for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
  cache=build/(pkg+'.'+ver+'.nupkg')
  if not cache.exists():cache.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
  z=zipfile.ZipFile(io.BytesIO(cache.read_bytes()))
  for name in z.namelist():
   if name.startswith('lib/netstandard2.0/')and name.endswith('.dll'):
    out=build/name.removeprefix('lib/netstandard2.0/');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(name))
 refs=list((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(build.glob('Microsoft.*.dll'))
 rsp=build/'compile.rsp';rsp.write_text('-nologo\n-target:exe\n-out:'+str(build/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(HERE/'Program.cs')+'\n')
 (build/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(dotnet),str(sdk/'Roslyn/bincore/csc.dll'),'@'+str(rsp)],check=True)
 payload=build/'input.json';payload.write_text(json.dumps(export(R/'3-9-緊急保安業務エージェント_optimized.yaml'),ensure_ascii=False))
 result=subprocess.run([str(dotnet),str(build/'check.dll'),str(payload)],check=True,capture_output=True,text=True)
 data=json.loads(result.stdout)
 data['source_file']='3-9-緊急保安業務エージェント_optimized.yaml'
 data['source_sha256']=hashlib.sha256((R/data['source_file']).read_bytes()).hexdigest()
 data['sdk']=sdk.name
 (HERE/'results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 bad=[x for x in data['results']if not x['success']]
 print('Microsoft.PowerFx.Interpreter 1.8.1:',len(data['results']),'expressions;',len(bad),'failures')
 failed_runs=[x for x in data.get('execution',[])if not x['success']]
 print('Native expression execution:',len(data.get('execution',[])),'synthetic cases;',len(failed_runs),'failures')
 if bad or failed_runs:raise SystemExit(1)
if __name__=='__main__':main()
