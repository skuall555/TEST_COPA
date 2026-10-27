"""Control-flow test helper, not the Power Fx engine or Studio host."""
import ast,re,operator
TOKENS=re.compile(r'"(?:[^"]|"")*"|Topic\.\w+|<>|<=|>=|&&|\|\||[A-Za-z_]\w*|\d+|[^\s]')
def evaluate(expr,values):
 parts=[]
 for t in TOKENS.findall(expr.lstrip('=')):
  if t.startswith('"'):parts.append(repr(t[1:-1].replace('""','"')))
  elif t.startswith('Topic.'):parts.append('values['+repr(t[6:])+']')
  else:parts.append({'=':'==','<>':'!=','&&':'and','||':'or','&':'+','true':'True','false':'False'}.get(t,t))
 tree=ast.parse(' '.join(parts),mode='eval')
 funcs={'Or':lambda *x:any(x),'And':lambda *x:all(x),'Not':lambda x:not x,'Trim':lambda x:re.sub(' +',' ',x.strip()),'StartsWith':lambda x,p:x.startswith(p),'Substitute':lambda x,a,b:x.replace(a,b),'Char':chr,'IsBlank':lambda x:x is None or x==''}
 comparisons={ast.Eq:operator.eq,ast.NotEq:operator.ne,ast.Gt:operator.gt,ast.GtE:operator.ge,ast.Lt:operator.lt,ast.LtE:operator.le,ast.In:lambda a,b:a in b}
 def run(n):
  if isinstance(n,ast.Expression):return run(n.body)
  if isinstance(n,ast.Constant):return n.value
  if isinstance(n,ast.Subscript)and isinstance(n.value,ast.Name)and n.value.id=='values':return values[run(n.slice)]
  if isinstance(n,ast.BinOp)and isinstance(n.op,ast.Add):return run(n.left)+run(n.right)
  if isinstance(n,ast.Compare):
   left=run(n.left)
   for op,right in zip(n.ops,n.comparators):
    right=run(right)
    if type(op)not in comparisons or not comparisons[type(op)](left,right):return False
    left=right
   return True
  if isinstance(n,ast.Call)and isinstance(n.func,ast.Name):
   if n.func.id=='If':return run(n.args[1]if run(n.args[0])else n.args[2])
   if n.func.id in funcs:return funcs[n.func.id](*(run(x)for x in n.args))
  raise ValueError(ast.dump(n))
 return run(tree)
