#!/usr/bin/env python3
"""Static checks only; this is not a Copilot Studio or Power Fx runtime."""
from pathlib import Path
import yaml, json, re, collections, hashlib
R=Path(__file__).resolve().parents[1]
PAIRS=[('1-マニュアル関連入口 (1).txt','1-マニュアル関連入口_optimized.yaml'),('3-9-緊急保安業務エージェント(2).txt','3-9-緊急保安業務エージェント_optimized.yaml'),('4-9-画像分析エージェント_緊急保安(1).txt','4-9-画像分析エージェント_緊急保安_optimized.yaml')]
class Strict(yaml.SafeLoader):pass
def mapping(loader,node,deep=False):
 d={}
 for k,v in node.value:
  key=loader.construct_object(k,deep=deep)
  if key in d:raise ValueError('duplicate key '+str(key))
  d[key]=loader.construct_object(v,deep=deep)
 return d
Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
def walk(x):
 if isinstance(x,dict):
  yield x
  for v in x.values():yield from walk(v)
 elif isinstance(x,list):
  for v in x:yield from walk(v)
def flat(d):return {n['id']:n for n in walk(d) if 'id' in n and 'kind' in n}
def own(n):
 return {k:v for k,v in n.items() if k not in ('actions','elseActions','conditions') } | ({'conditions':[{k:v for k,v in c.items() if k!='actions'} for c in n['conditions']]} if 'conditions'in n else {})
def formulas(x):
 if isinstance(x,str):
  if x.startswith('='):yield x[1:]
  elif '{Topic.' in x or '{If(' in x:
   yield from re.findall(r'\{([^{}]+)\}',x)
 elif isinstance(x,dict):
  for k,v in x.items():
   if k not in ('variable','result','output','actions','elseActions'):yield from formulas(v)
 elif isinstance(x,list):
  for v in x:yield from formulas(v)
def reads(n):
 refs=set()
 for expr in formulas(own(n)):
  expr=re.sub(r'"(?:[^"]|"")*"','""',expr)
  refs.update(re.findall(r'Topic\.([^\W\d]\w*)',expr))
 return refs
def defines(n):
 out=set()
 for k in ['variable','result']:
  v=n.get(k)
  if isinstance(v,str) and v.startswith('Topic.'):out.add(v.split('.')[1])
 for m in walk(n.get('output',{})):
  for v in m.values():
   if isinstance(v,str) and v.startswith('Topic.'):out.add(v.split('.')[1])
 return out

def dataflow(d):
 ix=flat(d); edges={k:set() for k in ix}
 def seq(actions,after=None):
  nxt=after
  for n in reversed(actions):
   k=n['id'];kind=n['kind']
   if kind=='GotoAction':edges[k]={n['actionId']}
   elif kind=='EndDialog':edges[k]=set()
   elif kind=='ConditionGroup':
    dest=set()
    for c in n['conditions']:
     v=seq(c.get('actions',[]),nxt)
     if v:dest.add(v)
    v=seq(n.get('elseActions',[]),nxt)
    if v:dest.add(v)
    edges[k]=dest
   elif nxt:edges[k]={nxt}
   nxt=k
  return nxt
 entry=seq(d['beginDialog']['actions']); reachable=set();stack=[entry]
 while stack:
  k=stack.pop()
  if k in reachable:continue
  reachable.add(k);stack.extend(edges[k]-reachable)
 pred={k:set() for k in reachable}
 for a in reachable:
  for b in edges[a]:pred[b].add(a)
 initial=set(d.get('inputType',{}).get('properties',{})); universe=set().union(*(defines(ix[k]) for k in reachable))|initial
 before={k:set(universe) for k in reachable};before[entry]=initial
 while True:
  changed=False
  for k in reachable:
   values=[before[p]|defines(ix[p]) for p in pred[k]]
   if k==entry:values.append(initial)
   new=set.intersection(*values) if values else set(initial)
   if new!=before[k]:before[k]=new;changed=True
  if not changed:break
 return [{'id':k,'variables':sorted(reads(ix[k])-before[k])} for k in sorted(reachable) if reads(ix[k])-before[k]], edges

def dependencies(ix):
 return {k:{f:n[f] for f in ['flowId','dialog','aIModelId','knowledgeSources','fileSearchDataSource','applyModelKnowledgeSetting'] if f in n} for k,n in ix.items() if any(f in n for f in ['flowId','dialog','aIModelId','knowledgeSources','fileSearchDataSource'])}

def formula_balance(d):
 errors=[]
 for n in flat(d).values():
  for expr in formulas(own(n)):
   clean=re.sub(r'"(?:[^"]|"")*"','',expr)
   stack=[]
   for c in clean:
    if c in '([':stack.append(c)
    elif c in ')]':
     if not stack or stack.pop()!=('(' if c==')'else '['):errors.append(n['id']);break
   if stack:errors.append(n['id'])
 return sorted(set(errors))
report={'scope':'静的検証のみ。Copilot Studio読込・Power Fx実行・実ナレッジ・性能は未検証','files':[]};changes=[]
for old,new in PAIRS:
 a=yaml.load((R/'originals'/old).read_text(),Loader=Strict);b=yaml.load((R/new).read_text(),Loader=Strict)
 ai,bi=flat(a),flat(b); ids=[n['id'] for n in walk(b) if 'id'in n]
 duplicate=[k for k,c in collections.Counter(ids).items() if c>1]
 broken=[k for k,n in bi.items() if n.get('kind')=='GotoAction' and n['actionId'] not in bi]
 assert not duplicate and not broken,(duplicate,broken)
 assert not set(ai)-set(bi),set(ai)-set(bi)
 assert dependencies(ai)=={k:v for k,v in dependencies(bi).items() if k in ai},'dependency mutation'
 for k,n in bi.items():
  if n.get('kind')=='SearchAndSummarizeContent':assert n['autoSend'] is False and n['applyModelKnowledgeSetting'] is False
  if n.get('kind')=='SearchKnowledgeSources':assert 'result'in n and 'userInput'in n and 'variable' not in n
  if k not in ai:
   exemplars=[v for old_name,_ in PAIRS for v in flat(yaml.safe_load((R/'originals'/old_name).read_text())).values() if v['kind']==n['kind']]
   assert exemplars,('new kind',n['kind'])
   allowed=set().union(*(set(v) for v in exemplars))
   assert set(n)<=allowed,('new node properties',k,set(n)-allowed)
 assert not formula_balance(b),formula_balance(b)
 aw,_=dataflow(a);bw,edges=dataflow(b)
 previous={(w['id'],v) for w in aw for v in w['variables']}
 added=[{'id':w['id'],'variables':[v for v in w['variables'] if (w['id'],v)not in previous]} for w in bw]
 added=[w for w in added if w['variables']]
 changed=[{'id':k,'fields':[f for f in sorted(set(own(ai[k]))|set(own(bi[k]))) if own(ai[k]).get(f)!=own(bi[k]).get(f)]} for k in ai if own(ai[k])!=own(bi[k])]
 changes.append({'file':new,'changed':changed,'added':[k for k in bi if k not in ai]})
 report['files'].append({'file':new,'yaml':'PASS (duplicate keys rejected)','unique_ids':len(ids),'broken_goto':broken,'removed_ids':sorted(set(ai)-set(bi)),'dependencies':'UNCHANGED','formula_delimiters':'PASS (not type validation)','read_before_write_baseline':aw,'read_before_write_optimized':bw,'new_read_before_write_candidates':added,'node_counts_before':dict(collections.Counter(n['kind'] for n in ai.values())),'node_counts_after':dict(collections.Counter(n['kind'] for n in bi.values())),'sha256':hashlib.sha256((R/new).read_bytes()).hexdigest()})
 (R/'validation'/(new+'.graph.json')).write_text(json.dumps(edges,ensure_ascii=False,indent=2,default=sorted)+'\n')
(R/'validation/static_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(R/'validation/changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
for f in report['files']:
 print(f['file'], 'PASS', 'new variable candidates:',f['new_read_before_write_candidates'])
print('PyYAML',yaml.__version__)
