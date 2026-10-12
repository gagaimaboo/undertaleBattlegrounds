# convert mojang proguard mappings (named -> obf) into SRG (obf -> named)
import sys, re
src, dst = sys.argv[1], sys.argv[2]
prims = {'void':'V','boolean':'Z','byte':'B','char':'C','short':'S','int':'I','long':'J','float':'F','double':'D'}
classes = {}   # named -> obf (dotted)
entries = []   # (named_cls, obf_cls, kind, data)
cur = None
for line in open(src, encoding='utf-8'):
    if line.startswith('#') or not line.strip(): continue
    if not line.startswith(' '):
        n, o = line.rstrip().rstrip(':').split(' -> ')
        classes[n] = o; cur = (n, o); continue
    s = line.strip()
    if s.startswith('#'): continue
    left, obf = s.split(' -> ')
    left = re.sub(r'^\d+:\d+:', '', left)
    typ, rest = left.split(' ', 1)
    if '(' in rest:
        name, args = rest.split('(', 1); args = args.split(')')[0]
        entries.append((cur, 'M', typ, name, [a for a in args.split(',') if a], obf))
    else:
        entries.append((cur, 'F', typ, rest, None, obf))
def desc(t, m):
    arr = 0
    while t.endswith('[]'): t = t[:-2]; arr += 1
    d = prims[t] if t in prims else 'L' + (m(t)).replace('.', '/') + ';'
    return '[' * arr + d
obf_of = lambda t: classes.get(t, t)
same = lambda t: t
with open(dst, 'w') as f:
    for n, o in classes.items():
        f.write(f"CL: {o.replace('.','/')} {n.replace('.','/')}\n")
    for (n, o), k, typ, name, args, obf in entries:
        no, nn = o.replace('.','/'), n.replace('.','/')
        if k == 'F':
            f.write(f"FD: {no}/{obf} {nn}/{name}\n")
        else:
            od = '(' + ''.join(desc(a, obf_of) for a in args) + ')' + desc(typ, obf_of)
            nd = '(' + ''.join(desc(a, same) for a in args) + ')' + desc(typ, same)
            f.write(f"MD: {no}/{obf} {od} {nn}/{name} {nd}\n")
