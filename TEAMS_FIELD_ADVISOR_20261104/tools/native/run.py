import sys,subprocess,json,yaml,re,shutil,argparse,urllib.request,zipfile,io
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'tools'))
from yaml_edit import nodes
from build_topics import FILES,MEASURES
parser=argparse.ArgumentParser();parser.add_argument('--dotnet',type=Path,default=Path(shutil.which('dotnet')or '/tmp/subaru-dotnet/dotnet'));parser.add_argument('--topic-dir',type=Path,default=ROOT/'topics');parser.add_argument('--result',type=Path,default=ROOT/'validation/native_results.json');args=parser.parse_args()
SDK=args.dotnet.resolve();BUILD=Path('/tmp/teams-native');BUILD.mkdir(exist_ok=True)
if not SDK.exists():raise SystemExit('Install .NET 8 SDK, then use --dotnet /absolute/path/to/dotnet')
for pkg,ver in [('microsoft.powerfx.core','1.8.1'),('microsoft.powerfx.interpreter','1.8.1'),('microsoft.powerfx.transport.attributes','1.8.1'),('microsoft.bcl.asyncinterfaces','6.0.0')]:
 p=BUILD/(pkg+'.nupkg')
 if not p.exists():p.write_bytes(urllib.request.urlopen(f'https://api.nuget.org/v3-flatcontainer/{pkg}/{ver}/{pkg}.{ver}.nupkg',timeout=30).read())
 z=zipfile.ZipFile(io.BytesIO(p.read_bytes()))
 for name in z.namelist():
  if name.startswith('lib/netstandard2.0/')and name.endswith('.dll'):
   out=BUILD/name.removeprefix('lib/netstandard2.0/');out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(z.read(name))
sdk=max((SDK.parent/'sdk').iterdir(),key=lambda p:tuple(int(x)for x in p.name.split('.')))
refs=list((SDK.parent/'packs/Microsoft.NETCore.App.Ref').glob('*/ref/net8.0/*.dll'))+list(BUILD.glob('Microsoft.*.dll'))
(BUILD/'compile.rsp').write_text('-nologo\n-target:exe\n-out:'+str(BUILD/'check.dll')+'\n'+'\n'.join('-r:'+str(p)for p in refs)+'\n'+str(HERE/'Program.cs'))
(BUILD/'check.runtimeconfig.json').write_text(json.dumps({'runtimeOptions':{'tfm':'net8.0','framework':{'name':'Microsoft.NETCore.App','version':'8.0.0'}}}))
subprocess.run([str(SDK),str(sdk/'Roslyn/bincore/csc.dll'),'@'+str(BUILD/'compile.rsp')],check=True)
variables={'Topic':{},'Global':{}};expressions=[];index={}
for name in FILES:
 old={n['id']:n for n in nodes(yaml.safe_load((ROOT/'source'/name).read_text()))if'id'in n and'kind'in n}
 new={n['id']:n for n in nodes(yaml.safe_load((args.topic_dir/name).read_text()))if'id'in n and'kind'in n};index[name]=new
 new_doc=yaml.safe_load((args.topic_dir/name).read_text());old_doc=yaml.safe_load((ROOT/'source'/name).read_text())
 if new_doc['beginDialog'].get('condition')!=old_doc['beginDialog'].get('condition'):expressions.append({'id':name+':trigger','expression':new_doc['beginDialog']['condition'][1:],'expected':'Boolean'})
 for ident,n in new.items():
  for text in [json.dumps(n,ensure_ascii=False)]:
   for group,var in re.findall(r'\b(Topic|Global)\.([^\W\d]\w*)',text):variables[group].setdefault(var,'String')
  if n['kind']=='SetVariable':
   group,var=n['variable'].split('.',1)
   if n['value']in ['=0','=1','=false','=true']or var in ['画像処理上限','画像添付番号','画像処理枚数']:
    variables[group][var]='Boolean'if n['value']in ['=false','=true']else 'Number'
  prior=old.get(ident,{})
  if n['kind']=='SetVariable'and n.get('value')!=prior.get('value'):expressions.append({'id':name+':'+ident,'expression':n['value'][1:],'target':n['variable']})
  if n['kind']=='ConditionGroup':
   prev={c['id']:c['condition']for c in prior.get('conditions',[])}
   expressions.extend({'id':name+':'+c['id'],'expression':c['condition'][1:],'expected':'Boolean'}for c in n['conditions']if c['condition']!=prev.get(c['id']))
  if n['kind']in ['InvokeFlowAction','BeginDialog']and n.get('input')!=prior.get('input'):
   for key,expr in n.get('input',{}).get('binding',{}).items():
    if isinstance(expr,str)and expr.startswith('='):expressions.append({'id':name+':'+ident+':'+key,'expression':expr[1:],'expected':'String'})
 for n in new.values():
  for match in re.finditer(r'Topic\.([^\W\d]\w*)\.text',json.dumps(n,ensure_ascii=False)):variables['Topic'][match[1]]='RecordText'
variables['Topic']['画像形式対応']='Boolean';variables['Global']['TeamsFieldReportCount']='Number'
for x in expressions:
 if 'target'in x:g,v=x.pop('target').split('.',1);x['expected']=variables[g][v]
field=index[FILES[1]];image=index[FILES[2]]
steps=[field[k]for k in ['setVariable_teamsCurrentSnapshot','setVariable_teamsPreviousSnapshot','setVariable_teamsPreviousId','setVariable_teamsCompareStatus','setVariable_teamsChanges','setVariable_teamsRender']]
def rows(priorities=None,states=None,optional=False,reason='報告に基づく根拠'):
 priorities=priorities or {};states=states or {};data=[]
 for code,label in MEASURES[:14 if optional else 13]:data.append((code,label,priorities.get(code,'高'if code in ['P01','P02','P03','P04','P05','P06','P07','P09']else'低'if code in ['P11','P12']else'中'),states.get(code,'要確認'),reason))
 return data

def snapshot(rs):return '\n'.join('|'.join([r[0],r[2],r[3]])for r in rs)
def case(name,current,previous=None,saved='case-A',previous_id='case-A',explicit=False,includes=(),excludes=()):
 previous=previous or [];acc=''.join(r[2]+'|'+r[3]+'|└'+r[1]+'：'+r[3]+'　根拠：'+r[4]+chr(30)for r in current)
 topic={'判定表示行':acc,'判定高欄':'\n'.join('└'+r[1]+'：'+r[3]+'　根拠：'+r[4]for r in current if r[2]=='高'),'判定中欄':'\n'.join('└'+r[1]+'：'+r[3]+'　根拠：'+r[4]for r in current if r[2]=='中'),'判定低欄':'\n'.join('└'+r[1]+'：'+r[3]+'　根拠：'+r[4]for r in current if r[2]=='低'),'判定確認文':'未確認の条件で判断が変わるため、現在の状況を教えてください。','判定次行動':'└未完了の高優先度作業を進めてください。','案件ID':saved,'明示案件指定':'あり'if explicit else'なし'}
 glob={'TeamsLastFieldSnapshot':snapshot(previous),'TeamsLastCaseId':previous_id if previous else'','TeamsFieldReportCount':1 if previous else 0}
 return {'name':name,'state':{'Topic':topic,'Global':glob},'includes':list(includes),'excludes':list(excludes)+['[[P','【確認できた事実】','【高優先度の完了状況】']}
current=rows();cases=[case('first report hides change section',current,includes=['【②','【③','【④'],excludes=['【①']),case('same priorities despite wording changes',rows(reason='別の言い回し'),current,includes=['前回から優先度の変更なし']),case('priority rises',rows({'P08':'高'}),current,includes=['分岐バルブ・引込管ガス遮断装置等：中 → 高']),case('state changes separately',rows(states={'P07':'対応済み'}),current,includes=['状態 要確認 → 対応済み']),case('different case never compared',current,current,saved='case-B',includes=['前回比較は現在できません'],excludes=['前回から優先度の変更なし']),case('missing saved identity never compared',current,current,saved='',includes=['前回比較は現在できません']),case('optional item absent is not resolved',current,rows(optional=True),includes=['今回は未判定（解消とは判定しません）']),case('new optional item',rows(optional=True),current,includes=['新規項目']),case('explicit resume without data is not a first case',current,explicit=True,includes=['前回比較は現在できません'])]
images=[{'name':'two actual inline inputs','attachments':[{'name':'a.jpg','mime':'image/jpeg','content':'image-A'},{'name':'b.png','mime':'image/png','content':'image-B'}],'expectedInputs':['image-A','image-B'],'rejected':0},{'name':'Teams metadata not mistaken for bytes','attachments':[{'name':'a.jpg','mime':'application/vnd.microsoft.teams.file.download.info','content':'metadata-reference'}],'expectedInputs':[],'rejected':1},{'name':'mixed file order','attachments':[{'name':'a.txt','mime':'text/plain','content':'not-image'},{'name':'b.png','mime':'image/png','content':'image-B'}],'expectedInputs':['image-B'],'rejected':1},{'name':'bounded maximum five attachments','attachments':[{'name':str(i)+'.jpg','mime':'image/jpeg','content':'image-'+str(i)}for i in range(6)],'expectedInputs':['image-'+str(i)for i in range(5)],'rejected':0}]
data={'variables':variables,'expressions':expressions,'renderSteps':[{'variable':n['variable'],'expression':n['value'][1:]}for n in steps],'renderCases':cases,'imageCases':images,'imageExpressions':{k:{'variable':image[k]['variable'],'expression':image[k]['value'][1:]}for k in ['setVariable_attachmentName','setVariable_attachmentContentType','setVariable_attachmentSupported']}|{'imageInput':image['invokeAIBuilderModelAction_imageFacts']['input']['binding']['ImageInput'][1:]}}
(BUILD/'input.json').write_text(json.dumps(data,ensure_ascii=False));p=subprocess.run([str(SDK),str(BUILD/'check.dll'),str(BUILD/'input.json')],capture_output=True,text=True)
if p.returncode:raise SystemExit(p.stderr)
result=json.loads(p.stdout);args.result.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
for group in ['checks','renders','images']:
 failed=[x for x in result[group]if not x['success']];print(group,len(result[group]),'failed',len(failed))
 for x in failed[:12]:print(x)
if any(not x['success']for g in ['checks','renders','images']for x in result[g]):raise SystemExit(1)
