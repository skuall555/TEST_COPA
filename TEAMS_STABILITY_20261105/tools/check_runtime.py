from pathlib import Path
import re,json,subprocess,yaml,sys,urllib.request,zipfile,argparse
from build import ROOT,guard
from yaml_edit import nodes
SDK=Path('/tmp/subaru-dotnet/dotnet');B=Path('/tmp/teams-stability-native');B.mkdir(exist_ok=True)
def main():
 global SDK
 a=argparse.ArgumentParser();a.add_argument('--dotnet',type=Path,default=SDK);args=a.parse_args();SDK=args.dotnet.resolve()
 d=yaml.safe_load((ROOT/'3-9_貼り替え用.yaml').read_text());idx={n['id']:n for n in nodes(d)if'id'in n and'kind'in n};actions=idx['conditionGroup_priorityGuideRetrieveSucceeded']['conditions'][0]['actions'];start=next(i for i,n in enumerate(actions)if n['id']=='answer_priority');end=next(i for i,n in enumerate(actions)if n['id']=='conditionGroup_prioritySucceeded');program=actions[start:end]
 variables=set(re.findall(r'Topic\.([^\W\d]\w*)',json.dumps(program,ensure_ascii=False)));variables.update(['目的分野','初回入力'])
 good='[[FACTS]]└台所でガス臭気あり[[/FACTS]]\n[[EMERGENCY]]通常|単独の臭気報告のみで、具体的な高条件は未報告[[/EMERGENCY]]\n'+'\n'.join(f'[[P{i:02}]]'+('低'if i in [11,12]else'高'if i in [1,2,3,4,5,6,7,9]else'中')+f'|要確認|報告された対象と適用条件を照合。実施状況は未報告[[/P{i:02}]]'for i in range(1,14))+'\n[[NEXT]]└必要な作業とその効果を確認してください[[/NEXT]]\n[[CHECK]]未確認の状況で判断が変わるため、対象場所の情報を教えてください。[[/CHECK]]'
 bad=good.replace('[[P07]]','[[BROKEN]]');missing=good.replace('[[EMERGENCY]]通常|','[[EMERGENCY]]通常：')
 cases=[{'name':'初回合格は再生成しない','outputs':[good],'expectedCalls':1,'expectedAccept':True},{'name':'空出力の後に合格','outputs':['',good],'expectedCalls':2,'expectedAccept':True},{'name':'マーカー破損の後に合格','outputs':[bad,good],'expectedCalls':2,'expectedAccept':True},{'name':'区切り不正の後に合格','outputs':[missing,good],'expectedCalls':2,'expectedAccept':True},{'name':'2回とも空なら保存へ進まない','outputs':['',''],'expectedCalls':2,'expectedAccept':False},{'name':'2回とも不正なら保存へ進まない','outputs':[bad,bad],'expectedCalls':2,'expectedAccept':False},{'name':'不正な後に空でも上限は2回','outputs':[bad,''],'expectedCalls':2,'expectedAccept':False}]
 routes=[]
 for text in ['台所でガス臭い','浴室で臭気あり','動作確認用のテスト案件です。台所でガス臭い','複数の家で検知器が反応','ガス警報が継続','ガスを止めた']:
  routes.append({'name':text,'text':text,'purpose':'現場対応アドバイス','expected':True})
 for purpose,text in [('マニュアル確認','ガス臭気時の基準を確認したい'),('マニュアル改訂','ガス漏れ対応の規定を改訂したい'),('','台所でガス臭い'),('現場対応アドバイス','こんにちは'),('現場対応アドバイス','ガス設備の通常点検について相談したい')]:routes.append({'name':purpose+':'+text,'text':text,'purpose':purpose,'expected':False})
 data={'variables':sorted(variables),'program':program,'cases':cases,'routes':routes,'routeGuard':guard()[1:],'saveGuard':idx['conditionGroup_prioritySucceeded']['conditions'][0]['condition'][1:]}
 (B/'input.json').write_text(json.dumps(data,ensure_ascii=False))
 for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
  p=B/(pkg+'.nupkg')
  if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
  with zipfile.ZipFile(p)as z:
   for n in z.namelist():
    if n.startswith('lib/netstandard2.0/')and n.endswith('.dll'):
     dst=B/n.removeprefix('lib/netstandard2.0/');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(n))
 ver=max((SDK.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')));refs=list((SDK.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(B.glob('Microsoft.*.dll'))
 (B/'compile.rsp').write_text('-nologo\n-target:exe\n-out:'+str(B/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(ROOT/'tools/NativeRuntime.cs'));(B/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(SDK),str(ver/'Roslyn/bincore/csc.dll'),'@'+str(B/'compile.rsp')],check=True);r=subprocess.run([str(SDK),str(B/'check.dll'),str(B/'input.json')],capture_output=True,text=True)
 if r.returncode:raise SystemExit(r.stderr)
 results=json.loads(r.stdout);(ROOT/'validation/実行分岐検証.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 for group in ['routes','cases']:
  failed=[x for x in results[group]if not x['success']];print(group,len(results[group]),'failed',len(failed))
  for case in failed:print(case)
 if any(not x['success']for g in ['routes','cases']for x in results[g]):raise SystemExit(1)
if __name__=='__main__':main()
