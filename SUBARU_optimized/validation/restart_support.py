from pathlib import Path
import yaml, copy, json, difflib

class D(yaml.SafeDumper):

    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)

def rep(d, s):
    return d.represent_scalar('tag:yaml.org,2002:str', s, style='|' if '\n' in s else None)
D.add_representer(str, rep)

def dump(n, indent=0):
    return ''.join(((' ' * indent + l if l.strip() else '') + '\n' for l in yaml.dump(n, Dumper=D, allow_unicode=True, sort_keys=False, width=100000).splitlines()))

def nodes(x):
    if isinstance(x, dict):
        yield x
        for v in x.values():
            yield from nodes(v)
    elif isinstance(x, list):
        for v in x:
            yield from nodes(v)

def edit(p, ops):
    s = p.read_text()
    tree = yaml.compose(s)
    ranges = {}

    def walk(n):
        if isinstance(n, yaml.MappingNode):
            fields = {k.value: v for k, v in n.value}
            if 'id' in fields and 'kind' in fields:
                a = n.start_mark.index
                line = s.rfind('\n', 0, a) + 1
                a = line
                indent = n.start_mark.column - 2
                if indent >= 0 and s[line:line + indent + 2].endswith('- '):
                    ranges[fields['id'].value] = (a, n.end_mark.index, indent)
            for k, v in n.value:
                walk(v)
        elif isinstance(n, yaml.SequenceNode):
            for v in n.value:
                walk(v)
    walk(tree)
    edits = []
    data = yaml.safe_load(s)
    transformed = {}

    def transform(x):
        if isinstance(x, list):
            out = []
            for v in x:
                r = transform(v)
                out.extend(r if isinstance(r, list) and isinstance(v, dict) and (v.get('id') in ops) else [r])
            return out
        if isinstance(x, dict):
            n = {k: transform(v) for k, v in x.items()}
            if n.get('id') in ops and 'kind' in n:
                result = ops[n['id']](n)
                new = [n] if result is None else result
                transformed[n['id']] = new
                return new
            return n
        return x
    transform(data)
    candidates = []
    for ident, new in transformed.items():
        a, b, ind = ranges[ident]
        line = s.rfind('\n', 0, b) + 1
        if not s[line:b].strip():
            b = line
        candidates.append((a, b, dump(new, ind)))
    for a, b, t in sorted(candidates):
        if edits and a < edits[-1][1]:
            continue
        edits.append((a, b, t))
    for a, b, t in sorted(edits, reverse=True):
        s = s[:a] + t + s[b:]
    return s

def setv(i, v, x):
    return {'kind': 'SetVariable', 'id': i, 'variable': v, 'value': x}

def cg(i, c, acts, els=None):
    n = {'kind': 'ConditionGroup', 'id': i, 'conditions': [{'id': i + '_item', 'condition': c, 'actions': acts}]}
    if els is not None:
        n['elseActions'] = els
    return n

def add(n, t):
    n['additionalInstructions'] = n.get('additionalInstructions', '') + '\n' + t
