"""Small offline evaluator for pure scalar routing formulas only, not a Power Fx runtime."""
import ast,re
TOKENS=re.compile(r'"(?:[^"]|"")*"|Topic\.\w+|<>|&&|\|\||[A-Za-z_]\w*|\d+|[^\s]')
def evaluate(expr,values):
 parts=[]
 for t in TOKENS.findall(expr.lstrip('=')):
  if t.startswith('"'):parts.append(repr(t[1:-1].replace('""','"')))
  elif t.startswith('Topic.'):parts.append('values['+repr(t[6:])+']')
  else:parts.append({'=':'==','<>':'!=','&&':'and','||':'or','&':'+','true':'True','false':'False'}.get(t,t))
 source=' '.join(parts);tree=ast.parse(source,mode='eval')
 allowed=(ast.Expression,ast.Call,ast.Name,ast.Load,ast.Constant,ast.Subscript,ast.Compare,ast.Eq,ast.NotEq,ast.In,ast.BoolOp,ast.And,ast.Or,ast.BinOp,ast.Add)
 if any(not isinstance(n,allowed)for n in ast.walk(tree)):raise ValueError(source)
 funcs={'If':lambda c,a,b:a if c else b,'Or':lambda *x:any(x),'And':lambda *x:all(x),'Not':lambda x:not x,'StartsWith':lambda x,p:x.startswith(p),'Trim':lambda x:x.strip(),'Substitute':lambda x,a,b:x.replace(a,b),'IsBlank':lambda x:x is None or x==''}
 return eval(compile(tree,'<routing-formula>','eval'),{'__builtins__':{}},{**funcs,'values':values})
