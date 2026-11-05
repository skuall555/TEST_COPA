"""Validate only new display expressions and execute realistic generated scenarios."""
import argparse,json,re,subprocess,urllib.request,zipfile
from pathlib import Path
import yaml
from build import ROOT,SOURCE,YAML,index,display_steps,DISPLAY,measures

def cases():
 def rows(priorities=None,states=None,optional=False,reason='報告に基づく根拠'):
  priorities=priorities or {};states=states or {}
  return [(code,label,priorities.get(code,'高'if code in ['P01','P02','P03','P04','P05','P06','P09']else'低'if code in ['P11','P12']else'中'),states.get(code,'要確認'),reason)for code,label in measures()[:14 if optional else 13]]
 def snap(rs):return '\n'.join('|'.join([r[0],r[2],r[3]])for r in rs)
 def case(name,cur,prev=None,contains=(),absent=(),case_id='case-A',previous_id='case-A',channel='msteams',oldchannel='msteams',user='user-A',olduser='user-A',conversation='chat-A',oldconversation='chat-A'):
  prev=prev or [];t={'案件ID':case_id,'判定表示行':''.join('|'.join([r[2],r[3],'└'+r[1]+'：'+r[3]+'　根拠：'+r[4]])+chr(30)for r in cur),'判定確認文':'未確認の条件が分かると優先度が変わるため、現在の状況を教えてください。','判定次行動':'└P05の実施状況を確認し、必要な作業を進めてください。','優先度判定結果':'従来のApps用文章\n見出し・改行・内容をそのまま保存'}
  for priority,var in [('高','判定高欄'),('中','判定中欄'),('低','判定低欄')]:t[var]='\n'.join('└'+r[1]+'：'+r[3]+'　根拠：'+r[4]for r in cur if r[2]==priority)
  g={'Teams表示前回案件ID':previous_id if prev else'','Teams表示前回会話ID':oldconversation,'Teams表示前回利用者ID':olduser,'Teams表示前回チャネル':oldchannel,'Teams表示前回判定':snap(prev)}
  return {'name':name,'system':{'channel':channel,'conversation':conversation,'user':user},'state':{'Topic':t,'Global':g},'contains':list(contains),'notContains':list(absent)+(['[[P','P05','【確認できた事実】','【高優先度の完了状況】']if channel=='msteams'else[])}
 r=rows();out=[case('初回は②③④・①省略',r,contains=['【②','【③','【④'],absent=['【①']),case('根拠の言い換えは変更扱いにしない',rows(reason='理由だけ言い換え'),r,contains=['前回から優先度・実施状況の変更はありません']),case('優先度の上昇',rows({'P08':'高'}),r,contains=['分岐バルブ・引込管ガス遮断装置等：中 → 高']),case('優先度の低下',rows({'P09':'中'}),r,contains=['消火器設置：高 → 中']),case('実施済みへの変更',rows(states={'P07':'対応済み'}),r,contains=['実施状況 要確認 → 対応済み']),case('優先度と状態が同時に変わる',rows({'P08':'高'},{'P08':'対応済み'}),r,contains=['中 → 高','実施状況 要確認 → 対応済み']),case('新規の任意措置',rows(optional=True),r,contains=['新たに判定']),case('今回ない項目は解消扱いにしない',r,rows(optional=True),contains=['今回は未判定（解消とは判断しません）']),case('別案件は比較しない',r,r,case_id='case-B',absent=['【①','中 → 高']),case('別会話は比較しない',r,r,conversation='chat-B',absent=['【①']),case('別利用者は比較しない',r,r,user='user-B',absent=['【①']),case('別チャネルのキャッシュと比較しない',r,r,oldchannel='webchat',absent=['【①']),case('案件IDなしは比較不可',r,r,case_id='',contains=['前回比較は現在できません'],absent=['変更はありません']),case('利用者IDなしは比較不可',r,r,user='',contains=['前回比較は現在できません']),case('高ゼロ件は該当なし',rows({k:'中'for k,_ in measures()}),contains=['🔴 高\n・該当なし']),case('Teams以外は元の文章をそのまま返す',r,r,channel='webchat'),case('チャネル不明は元の文章をそのまま返す',r,r,channel='')]
 for c in out:
  if c['system']['channel']!='msteams':c['equals']=c['state']['Topic']['優先度判定結果']
 return out

def main():
 a=argparse.ArgumentParser();a.add_argument('--dotnet',type=Path,default=Path('/tmp/subaru-dotnet/dotnet'));args=a.parse_args();sdk=args.dotnet.resolve();b=Path('/tmp/teams-display-native');b.mkdir(exist_ok=True)
 for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
  p=b/(pkg+'.nupkg')
  if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
  with zipfile.ZipFile(p)as z:
   for n in z.namelist():
    if n.startswith('lib/netstandard2.0/')and n.endswith('.dll'):
     dst=b/n.removeprefix('lib/netstandard2.0/');dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(z.read(n))
 ver=max((sdk.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')));refs=list((sdk.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(b.glob('Microsoft.*.dll'))
 (b/'compile.rsp').write_text('-nologo\n-target:exe\n-out:'+str(b/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(ROOT/'tools/PowerFxCheck.cs'))
 (b/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
 subprocess.run([str(sdk),str(ver/'Roslyn/bincore/csc.dll'),'@'+str(b/'compile.rsp')],check=True)
 variables={'Topic':set(),'Global':set()}
 for n in display_steps():
  group,name=n['variable'].split('.',1);variables[group].add(name)
  for g,v in re.findall(r'\b(Topic|Global)\.([^\W\d]\w*)',n['value']):variables[g].add(v)
 variables['Topic'].add('優先度判定結果')
 data={'variables':{k:sorted(v)for k,v in variables.items()},'steps':[{'id':n['id'],'variable':n['variable'],'expression':n['value'][1:]}for n in display_steps()],'display':DISPLAY,'cases':cases()}
 (b/'input.json').write_text(json.dumps(data,ensure_ascii=False));r=subprocess.run([str(sdk),str(b/'check.dll'),str(b/'input.json')],capture_output=True,text=True)
 if r.returncode:raise SystemExit(r.stderr)
 results=json.loads(r.stdout);(ROOT/'validation/PowerFx検証.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
 for name in ['checks','runs']:
  failed=[x for x in results[name]if not x['success']];print(name,len(results[name]),'failed',len(failed))
  for f in failed[:4]:print(f)
 if any(not x['success']for g in ['checks','runs']for x in results[g]):raise SystemExit(1)
if __name__=='__main__':main()
