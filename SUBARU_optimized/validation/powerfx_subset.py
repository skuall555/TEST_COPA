"""Offline evaluator for tested scalar/table expressions, not the Power Fx engine/type checker."""
import ast,re,operator
TOKENS=re.compile(r'"(?:[^"]|"")*"|Topic\.\w+|<>|<=|>=|&&|\|\||[A-Za-z_]\w*|\d+|[^\s]')
def evaluate(expr,values):
 # Only the tested local-table alias form is supported; this is not a general Power Fx parser.
 expr=re.sub(r'\bFilter\((Topic\.\w+) As (\w+),',r'FilterAs(\1, "\2",',expr)
 parts=[]
 for t in TOKENS.findall(expr.lstrip('=')):
  if t.startswith('"'):parts.append(repr(t[1:-1].replace('""','"')))
  elif t.startswith('Topic.'):parts.append('values['+repr(t[6:])+']')
  else:parts.append({'=':'==','<>':'!=','&&':'and','||':'or','&':'+','true':'True','false':'False'}.get(t,t))
 tree=ast.parse(' '.join(parts),mode='eval')
 funcs={'Or':lambda *x:any(x),'And':lambda *x:all(x),'Not':lambda x:not x,'StartsWith':lambda x,p:x.startswith(p),'EndsWith':lambda x,p:x.endswith(p),'Trim':lambda x:re.sub(' +',' ',x.strip()),'TrimEnds':lambda x:x.strip(),'Find':lambda x,s:s.find(x)+1,'Mid':lambda s,start,count:s[start-1:start-1+count],'Substitute':lambda x,a,b:x.replace(a,b),'IsBlank':lambda x:x is None or x=='','Char':chr,'Len':len,'CountRows':len,'Split':lambda x,d:[{'Value':v}for v in x.split(d)],'FirstN':lambda x,n:x[:n],'First':lambda x:x[0],'Last':lambda x:x[-1]}
 comparisons={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Lt:operator.lt,ast.LtE:operator.le,ast.In:lambda a,b:a in b}
 def run(n,context):
  if isinstance(n,ast.Expression):return run(n.body,context)
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.Name):
   if n.id in context:return context[n.id]
   raise ValueError('Unknown name '+n.id)
  if isinstance(n,ast.Subscript):
   if not isinstance(n.value,ast.Name)or n.value.id!='values':raise ValueError('Only variable lookups supported')
   return values[run(n.slice,context)]
  if isinstance(n,ast.Attribute)and n.attr=='Value':return run(n.value,context)['Value']
  if isinstance(n,ast.BinOp)and isinstance(n.op,ast.Add):return run(n.left,context)+run(n.right,context)
  if isinstance(n,ast.BoolOp):
   if isinstance(n.op,ast.And):return all(run(v,context)for v in n.values)
   if isinstance(n.op,ast.Or):return any(run(v,context)for v in n.values)
  if isinstance(n,ast.Compare):
   left=run(n.left,context)
   for op,right in zip(n.ops,n.comparators):
    right=run(right,context)
    if type(op)not in comparisons or not comparisons[type(op)](left,right):return False
    left=right
   return True
  if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and not n.keywords:
   name=n.func.id
   if name=='If':return run(n.args[1]if run(n.args[0],context)else n.args[2],context)
   if name=='Filter':return [row for row in run(n.args[0],context)if run(n.args[1],{**context,**row})]
   if name=='FilterAs':
    alias=run(n.args[1],context)
    return [row for row in run(n.args[0],context)if run(n.args[2],{**context,**row,alias:row})]
   if name=='Distinct':
    result=[]
    for row in run(n.args[0],context):
     value=run(n.args[1],{**context,**row})
     if value not in result:result.append(value)
    return result
   if name=='Concat':
    table=run(n.args[0],context);separator=run(n.args[2],context)if len(n.args)>2 else ''
    return separator.join(str(run(n.args[1],{**context,**row}))for row in table)
   if name in funcs:return funcs[name](*(run(a,context)for a in n.args))
  raise ValueError('Unsupported expression '+ast.dump(n))
 return run(tree,{})
