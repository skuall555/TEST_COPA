"""Give priority temporaries explicit initial values and acyclic table stages for the Studio host."""
import re,yaml
NAMES={
'優先度書式版':('P5Version','String'),'優先度形式修復回数':('P5RepairCount','Number'),
'優先度初回構造化結果':('P5FirstRaw','String'),'優先度構造化結果':('P5Raw','String'),
'措置状態根拠入力':('P5Evidence','String'),'優先度構造妥当':('P5EnvelopeOK','Boolean'),
'措置確認事実':('P5Facts','String'),'現危険監査本文':('P5RiskText','String'),
'措置状態監査本文':('P5MeasureText','String'),'現危険監査行':('P5RiskRows','Table'),
'現危険元件数':('P5RiskCount','Number'),'現危険原始行':('P5RiskOriginal','Table'),
'現危険妥当':('P5RiskOK','Boolean'),'現危険Alarm':('P5Alarm','Boolean'),
'現危険Detected':('P5Detected','Boolean'),'現危険肯定行':('P5RiskPositive','Table'),
'現危険追加0':('P5RiskExtra0','Boolean'),'現危険追加1':('P5RiskExtra1','Boolean'),
'現危険追加2':('P5RiskExtra2','Boolean'),'現危険追加3':('P5RiskExtra3','Boolean'),
'消防警察強制高':('P5RequestHigh','Boolean'),'措置状態監査行':('P5MeasureRows','Table'),
'措置状態元件数':('P5MeasureCount','Number'),'措置状態一意':('P5UniqueOK','Boolean'),
'措置状態必須行':('P5RequiredOK','Boolean'),'措置状態妥当':('P5DataOK','Boolean'),
'優先度高行':('P5HighRows','Table'),'優先度Middle行':('P5MiddleRows','Table'),
'優先度Low行':('P5LowRows','Table'),'高優先度未完了行':('P5PendingHigh','Table'),
'高優先度完了':('P5AllDone','Boolean'),'措置表示High':('P5HighText','String'),
'措置表示Middle':('P5MiddleText','String'),'措置表示Low':('P5LowText','String'),
'要請未完了行':('P5PendingRequests','Table'),'他措置未完了行':('P5PendingOther','Table'),
'要請次対応':('P5RequestNext','String'),'措置次対応':('P5OtherNext','String'),
'措置確認質問':('P5Questions','String')}
TOKEN=re.compile(r'"(?:[^"]|"")*"|Topic\.\w+')
def apply(R,edit,setv,cg,nodes):
 p=R/'3-9-緊急保安業務エージェント_optimized.yaml'
 data=yaml.safe_load(p.read_text());ix={n['id']:n for n in nodes(data)if 'id'in n and 'kind'in n}
 def f(k):return 'TrimEnds(Last(FirstN(Split(Value, "|"), '+str(k)+')).Value)'
 def columns(var,count):
  parts=' & "|" & '.join(f(k)for k in range(1,count+1))
  return '=Concat(Split('+var+', Char(10)), If(CountRows(Split(Value, "|")) = '+str(count)+', '+parts+', TrimEnds(Value)), Char(10))'
 ix['setVariable_priorityNormalizeRiskColumns']['value']=columns('Topic.現危険監査本文',3)
 ix['setVariable_priorityNormalizeRiskStatus']['value']='=Topic.現危険監査本文'
 ix['setVariable_priorityNormalizeMeasuresColumns']['value']=columns('Topic.措置状態監査本文',10)
 # Match a complete normalized row prefix; no nested table alias or Distinct is needed.
 prefix='Char(10) & '+f(1)+' & "|" & '+f(2)+' & "|"'
 once='CountRows(Split(Char(10) & Topic.措置状態監査本文, '+prefix+')) = 2'
 ix['setVariable_priorityMeasureUnique']['value']='=CountRows(Filter(Topic.措置状態監査行, '+once+')) = CountRows(Topic.措置状態監査行)'
 ix['setVariable_priorityRemoveAmbiguousTargets']['value']='=Filter(Topic.措置状態監査行, '+once+')'
 ix['setVariable_priorityFormatVersion']['value']='="priority-v5-types-20261023"'
 active={};counts={};types={};mapping=[]
 for old,(base,kind)in NAMES.items():
  if kind!='Table':active['Topic.'+old]='Topic.'+base;types['Topic.'+base]=kind
 def rename(expr):
  return TOKEN.sub(lambda m:active.get(m.group(),m.group())if m.group().startswith('Topic.')else m.group(),expr)
 # All priority table writes occur in the linear parse/render sequence; branches only read them.
 for n in nodes(data):
  if not isinstance(n,dict):continue
  for field in ['value','condition','userInput','additionalInstructions','activity','prompt']:
   value=n.get(field)
   if isinstance(value,str):n[field]=rename(value)
  var=n.get('variable')
  if isinstance(var,str)and var.startswith('Topic.')and var[6:]in NAMES:
   old=var[6:];base,kind=NAMES[old]
   if kind=='Table':
    index=counts.get(old,0);counts[old]=index+1;new='Topic.'+base+str(index).zfill(2);active[var]=new;types[new]='Table'
   else:new=active[var]
   n['variable']=new;mapping.append({'id':n.get('id'),'old':var,'new':new,'type':kind})
 seeds=[]
 defaults={'String':'=""','Number':'=0','Boolean':'=false','Table':'=FirstN(Split("", Char(10)), 0)'}
 for i,(name,kind)in enumerate(types.items()):seeds.append(setv('setVariable_p5Seed'+str(i).zfill(2),name,defaults[kind]))
 # Existing public text output is also anchored before the model writes it.
 seeds.append(setv('setVariable_p5ResultSeed','Topic.優先度判定結果','=""'))
 data['beginDialog']['actions']=seeds+data['beginDialog']['actions']
 # Emit as ordinary YAML. Existing action IDs, connector references and question settings remain.
 class Dumper(yaml.SafeDumper):
  def increase_indent(self,flow=False,indentless=False):return super().increase_indent(flow,False)
 def represent(dumper,s):return dumper.represent_scalar('tag:yaml.org,2002:str',s,style='|'if '\n'in s else None)
 Dumper.add_representer(str,represent)
 p.write_text(yaml.dump(data,Dumper=Dumper,allow_unicode=True,sort_keys=False,width=100000))
 import json
 (R/'validation/priority_type_map.json').write_text(json.dumps({'version':'priority-v5-types-20261023','variables':types,'assignments':mapping},ensure_ascii=False,indent=2)+'\n')
