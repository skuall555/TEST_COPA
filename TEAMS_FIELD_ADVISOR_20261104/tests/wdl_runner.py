"""Small WDL interpreter for the exact generated template, not a Power Automate emulator.
It executes generated expressions/actions against a mocked SharePoint boundary.
"""
import json,re
class Wdl:
 def __init__(self,text):self.s=text[1:]if text.startswith('@')else text;self.i=0
 def ws(self):
  while self.i<len(self.s)and self.s[self.i].isspace():self.i+=1
 def take(self,c):
  self.ws()
  if self.s.startswith(c,self.i):self.i+=len(c);return True
  return False
 def expr(self):
  self.ws()
  if self.take("'"):
   out=''
   while self.i<len(self.s):
    c=self.s[self.i];self.i+=1
    if c=="'":
     if self.i<len(self.s)and self.s[self.i]=="'":out+="'";self.i+=1;continue
     break
    out+=c
   n=('literal',out)
  else:
   m=re.match(r'[A-Za-z_][\w]*|\d+',self.s[self.i:])
   if not m:raise ValueError('Bad WDL near '+self.s[self.i:self.i+80])
   v=m[0];self.i+=len(v)
   if self.take('('):
    args=[]
    if not self.take(')'):
     while True:
      args.append(self.expr())
      if self.take(')'):break
      if not self.take(','):raise ValueError('Missing comma')
    n=('call',v,args)
   else:n=('literal',{'true':True,'false':False,'null':None}.get(v,int(v)if v.isdigit()else v))
  while True:
   self.take('?')
   if not self.take('['):break
   key=self.expr()
   if not self.take(']'):raise ValueError('Missing bracket')
   n=('get',n,key)
  return n
 def parse(self):
  n=self.expr();self.ws()
  if self.i!=len(self.s):raise ValueError('Unused WDL '+self.s[self.i:])
  return n

def ev(node,ctx):
 typ=node[0]
 if typ=='literal':return node[1]
 if typ=='get':
  obj=ev(node[1],ctx);key=ev(node[2],ctx)
  return None if obj is None else obj.get(key)if isinstance(obj,dict)else obj[key]
 name,args=node[1:]
 if name=='if':return ev(args[1]if ev(args[0],ctx)else args[2],ctx)
 if name=='and':return all(ev(a,ctx)for a in args)
 if name=='or':return any(ev(a,ctx)for a in args)
 values=[ev(a,ctx)for a in args]
 if name=='triggerBody':return ctx['trigger']
 if name in ['body','outputs']:return ctx['actions'][values[0]]
 if name=='item':return ctx['item']
 if name=='concat':return ''.join(''if v is None else str(v)for v in values)
 if name=='string':return ''if values[0]is None else str(values[0])
 if name=='replace':return values[0].replace(values[1],values[2])
 if name=='split':return values[0].split(values[1])
 if name=='trim':return values[0].strip()
 if name=='first':return values[0][0]if values[0]else None
 if name=='last':return values[0][-1]if values[0]else None
 if name=='skip':return values[0][values[1]:]
 if name=='empty':return values[0]in (None,'',[],{})
 if name=='length':return len(values[0])
 if name=='contains':return values[1]in values[0]
 if name=='equals':return values[0]==values[1]
 if name=='not':return not values[0]
 if name=='greater':return values[0]>values[1]
 if name=='coalesce':return next((v for v in values if v is not None),None)
 if name=='createArray':return values
 if name=='json':return json.loads(values[0])
 if name=='join':return values[1].join(values[0])
 if name=='union':
  out=[]
  for seq in values:
   for v in seq:
    if v not in out:out.append(v)
  return out
 raise ValueError('Unsupported test-only WDL function '+name)

def value(x,ctx):
 if isinstance(x,str)and x.startswith('@'):return ev(Wdl(x).parse(),ctx)
 if isinstance(x,dict):return {k:value(v,ctx)for k,v in x.items()}
 if isinstance(x,list):return [value(v,ctx)for v in x]
 return x
class Reply(Exception):
 def __init__(self,body):self.body=body
class ScopeFailed(Exception):pass
class Flow:
 def __init__(self,definition,config,records=None,fail_operation=None):self.definition=definition;self.config=config;self.records=records if records is not None else[];self.fail_operation=fail_operation;self.trace=[]
 def run(self,request):
  self.ctx={'trigger':request,'actions':{}};self.status={}
  try:self.actions(self.definition['actions'])
  except Reply as r:return r.body
  raise AssertionError('Flow did not respond')
 def actions(self,actions):
  todo=dict(actions);local=[]
  while todo:
   progressed=False
   for name,a in list(todo.items()):
    deps=a.get('runAfter',{})
    if any(k not in self.status for k in deps):continue
    if any(self.status[k]not in allowed for k,allowed in deps.items()):self.status[name]='Skipped';del todo[name];progressed=True;continue
    self.trace.append(name);progressed=True;del todo[name]
    try:self.execute(name,a);self.status[name]='Succeeded'
    except ScopeFailed:self.status[name]='Failed';local.append(name)
   if not progressed:raise AssertionError('Unresolved runAfter '+str(todo))
  if local:raise ScopeFailed()
 def execute(self,name,a):
  kind=a['type']
  if kind=='Scope':return self.actions(a['actions'])
  if kind=='If':return self.actions(a['actions']if value(a['expression'],self.ctx)else a.get('else',{}).get('actions',{}))
  if kind=='Compose':self.ctx['actions'][name]=value(a['inputs'],self.ctx);return
  if kind in ['Select','Query']:
   inp=a['inputs'];rows=value(inp['from'],self.ctx);out=[]
   for row in rows:
    ctx=self.ctx|{'item':row}
    if kind=='Select':out.append(value(inp['select'],ctx))
    elif value(inp['where'],ctx):out.append(row)
   self.ctx['actions'][name]=out;return
  if kind=='Response':raise Reply(value(a['inputs']['body'],self.ctx))
  if kind=='OpenApiConnection':
   op=a['inputs']['host']['operationId'];params=value(a['inputs']['parameters'],self.ctx)
   if self.fail_operation==op:raise ScopeFailed()
   if op=='GetItems':
    matches=re.findall(r"(\w+) eq '((?:[^']|'')*)'",params['$filter']);rows=[r for r in self.records if all(r.get(k)==v.replace("''", "'")for k,v in matches)];rows=sorted(rows,key=lambda r:r['ID'],reverse=True)[:params['$top']];self.ctx['actions'][name]={'value':rows};return
   if op=='PostItem':
    row={k[5:]:v for k,v in params.items()if k.startswith('item/')};event=self.config['field_map']['event_key']
    if any(r.get(event)==row[event]for r in self.records):raise ScopeFailed()
    row['ID']=max([r['ID']for r in self.records],default=0)+1;self.records.append(row);self.ctx['actions'][name]=row;return
  raise ValueError('Unsupported mock action '+kind)
