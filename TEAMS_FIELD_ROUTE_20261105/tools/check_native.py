from pathlib import Path
import json,subprocess,urllib.request,zipfile,argparse,yaml
from build import ROOT,guard
def main():
 a=argparse.ArgumentParser();a.add_argument('--dotnet',type=Path,default=Path('/tmp/subaru-dotnet/dotnet'));args=a.parse_args();sdk=args.dotnet.resolve();b=Path('/tmp/teams-field-first-native');b.mkdir(exist_ok=True)
 for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
  p=b/(pkg+'.nupkg')
  if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
  with zipfile.ZipFile(p)as z:
   for n in z.namelist():
    if n.startswith('lib/netstandard2.0/')and n.endswith('.dll'):
     f=b/n.removeprefix('lib/netstandard2.0/');f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(z.read(n))
 cases=[]
 for text in ['台所でガス臭い','動作確認用のテスト案件です。台所でガス臭い','浴室で臭気あり','マンションの共用廊下でガス臭がする','検知器が反応した','都市ガス警報器が鳴り続けている','隣の家のドアポストでLEL3％を検知。入れず換気できない','3軒でガスを検知、止められない','ガスが噴出している','ガスを止めた。臭気が低下してきた','lel 1% を検知','台所で　ガスくさい']:
  cases.append({'input':text,'retry':0,'field':True})
 for text in ['ガス臭気時のマニュアルを確認したい','ガス漏れ対応の基準を変更したい','警報器が鳴り続けるときの社内基準は？','ガス臭とは？','LELの意味を教えて','警報器が鳴る仕組みは何？','ガス臭気時の手順を調べたい','臭気対応の条文を削除したい','台所でガス臭い。マニュアルを確認したい','ガス臭い場合の対応を調べて','こんにちは','1','１','マニュアルを確認したい','修理方法を教えて']:
  cases.append({'input':text,'retry':0,'field':False})
 cases.append({'input':'台所でガス臭い','retry':1,'field':False})
 cases.append({'input':'台所でガス臭い。どう対応すればいいか確認したい','retry':0,'field':True})
 cases.append({'input':'ガス臭を感じるときの対応を調べたい','retry':0,'field':False})
 data={'normalize':'Lower(Substitute(Topic.初回入力, "　", " "))','guard':guard()[1:],'cases':cases};(b/'input.json').write_text(json.dumps(data,ensure_ascii=False))
 ver=max((sdk.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')));refs=list((sdk.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(b.glob('Microsoft.*.dll'))
 (b/'compile.rsp').write_text('-nologo\n-target:exe\n-out:'+str(b/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(ROOT/'tools/CheckRoute.cs'));(b/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(sdk),str(ver/'Roslyn/bincore/csc.dll'),'@'+str(b/'compile.rsp')],check=True);result=subprocess.run([str(sdk),str(b/'check.dll'),str(b/'input.json')],capture_output=True,text=True)
 if result.returncode:raise SystemExit(result.stderr)
 output=json.loads(result.stdout);(ROOT/'validation/目的分岐検証.json').write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n');failed=[x for x in output['cases']if not x['success']];print('cases',len(output['cases']),'failed',len(failed))
 for f in failed:print(f)
 if failed:raise SystemExit(1)
if __name__=='__main__':main()
