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
 from itemized_build import validator,MEASURES,STRING_VARS
 from image_features_build import ITEMS
 data['stringVariables']=STRING_VARS+['特徴_'+name for _,name in ITEMS]+['画像特徴カタログ']
 def wire(overrides=None,emergency='通常|両方を高に連動させる条件は今回の試験では指定しない',check='判断に必要な報告は確認できています。提示した未完了の作業を進めてください。'):
  overrides=overrides or {};parts=['[[FACTS]]└報告済みの事実を保持[[/FACTS]]','[[EMERGENCY]]'+emergency+'[[/EMERGENCY]]']
  for i,(code,name)in enumerate(MEASURES):
   priority,status,reason=overrides.get(code,('高','未実施','入力された基本措置の根拠')if i==0 else ('中','要確認','必要な対象情報が未確認')if i<13 else ('対象外','対象外','今回の事実では対象でない'))
   parts.append('[['+code+']]'+priority+'|'+status+'|'+reason+'[[/'+code+']]')
  return '\n'.join(parts+['[[NEXT]]└提示した高優先度の措置を進める[[/NEXT]]','[[CHECK]]'+check+'[[/CHECK]]'])
 good=wire();format_cases=[]
 def add(name,text,accept=True,**kwargs):format_cases.append(dict(name=name,text=text,accept=accept,**kwargs))
 add('valid scalar protocol',good)
 add('CRLF protocol',good.replace('\n','\r\n'))
 for priority,bucket in [('高','high'),('中','middle'),('低','low')]:
  add('police '+priority,wire({'P11':(priority,'未実施','この措置の優先度を'+priority+'と判定')}),expectBucket=bucket,expectLabel='消防・警察への要請')
 add('emergency forces both high despite low per-row values',wire({'P11':('低','未実施','元の行は低'), 'P12':('低','要確認','元の行は低')},emergency='高|入室不能の部屋で検知と警報が継続'),expectBucket='high',expectLabel='消防・警察への要請',expectEvacHigh=True)
 add('performed drain survey stays done',wire({'P05':('高','対応済み','排水口の調査実施済み'), 'P20':('高','未実施','未入室の別室は追加調査が必要')}),expectBucket='high',expectLabel='流入ガス・滞留ガスの検知器調査：対応済み')
 add('CHECK paragraph',wire(check='入室不能の部屋で検知されているため、要請と避難は高です。追加回答を待たず提示した作業を進めてください。上流遮断の方法を確認するため建物種別を教えてください。'),expectCheckPrefix='入室不能')
 add('completed high measures',wire({'P01':('高','対応済み','実施済み報告あり')}),expectWait=False)
 add('completion words in facts do not finish',good.replace('└報告済みの事実を保持','└全て対応済みではないと報告'))
 for name,text in [('wrong priority',good.replace('[[P11]]中|','[[P11]]最優先|')),('priority used as status',good.replace('[[P11]]中|要確認|','[[P11]]高|高|')),('extra delimiter',good.replace('入力された基本措置の根拠','根拠|余分')),('duplicate code',good+'\n[[P11]]高|未実施|追加[[/P11]]'),('missing row',good.replace('[[P12]]中|要確認|必要な対象情報が未確認[[/P12]]','')),('empty reason',good.replace('入力された基本措置の根拠','')),('unknown block',good.replace('[[NEXT]]','[[UNKNOWN]]余分[[/UNKNOWN]]\n[[NEXT]]')),('old 7-heading free text','【確認できた事実】\n└臭気あり'),('empty',''),('question list',wire(check='└建物種別は何か'))]:add(name,text,False)
 conversation=(R/'originals/20261027_様式逸脱_会話全文.txt').read_text()
 add('reported free-form drift',conversation.rsplit('ボット の発言:\n',1)[1],False)
 field=indexes[1];steps=[]
 for n in validator():
  if n['kind']=='SetVariable':
   assert field[n['id']]['value']==n['value']
   steps.append({'variable':n['variable'][6:],'expression':field[n['id']]['value'][1:]})
 data['formatSteps']=steps;data['formatCases']=format_cases
 image=indexes[2]
 image_ids=['setVariable_imageFeature'+code for code,_ in ITEMS]+['setVariable_imageFeatureCatalog','setVariable_prompt1','setVariable_prompt2']
 data['imageSteps']=[{'variable':image[ident]['variable'][6:],'expression':image[ident]['value'][1:]}for ident in image_ids]
 data['imageContext']=image['invokeAIBuilderModelAction_imageFacts']['input']['binding']['ContextText'][1:]
 data['featureSources']=[(R/'image_features'/(code+'_'+name+'.md')).read_text()for code,name in ITEMS]
 field=indexes[1];data['completion']=field['conditionGroup_priorityLoopNeeded']['conditions'][0]['condition'][1:]
 inp=build/'input.json';inp.write_text(json.dumps(data,ensure_ascii=False));out=subprocess.run([str(dotnet),str(build/'check.dll'),str(inp)],check=True,capture_output=True,text=True)
 result=json.loads(out.stdout);result['source_sha256']=hashes;(HERE/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print('Native SDK:',len(result['checks']),'expression checks,',len(result['runs']),'number parsing cases,',len(result['formats']),'itemized pipeline cases; image feature wiring:',result['imageFeatures']['success'])
 if any(not x['success']for x in result['checks']+result['runs']+result['formats'])or not result['imageFeatures']['success']:raise SystemExit(1)
if __name__=='__main__':main()
