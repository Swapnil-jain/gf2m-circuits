"""Dissect a one-AND-level .slp: top forms, products, output columns gamma, and the layered floor.
usage: python3 ideas/anatomy.py FILE.slp"""
import sys, re
lin, prod, out = {}, {}, {}
for i in range(8):
    lin['A%d' % i] = (1 << i, 0); lin['B%d' % i] = (0, 1 << i)
P = []          # list of (alpha, beta)
bot = {}        # signal -> frozenset of product indices
for ln in open(sys.argv[1]):
    ln = ln.split('#')[0].strip()
    if not ln: continue
    m = re.match(r'(\w+)\s*=\s*(\w+)\s*([x+])\s*(\w+)', ln)
    if not m:
        d, s = [t.strip() for t in ln.split('=')]; out[d] = s; continue
    d, u, op, v = m.groups()
    if op == 'x':
        a = lin[u] if lin[u][0] else lin[v]; b = lin[v] if lin[v][1] else lin[u]
        P.append((a[0], b[1])); bot[d] = frozenset([len(P) - 1])
    elif u in lin and v in lin:
        lin[d] = (lin[u][0] ^ lin[v][0], lin[u][1] ^ lin[v][1])
    else:
        bot[d] = bot[u] ^ bot[v]
K = len(P)
gam = [0] * K
for j in range(8):
    for k in bot[out['C%d' % j]]: gam[k] |= 1 << j
w = lambda x: bin(x).count('1')
fa = {a for a, b in P if w(a) > 1}; fb = {b for a, b in P if w(b) > 1}; fg = {g for g in gam if w(g) > 1}
f = lambda x: '+'.join(str(i) for i in range(8) if x >> i & 1)
for k, (a, b) in enumerate(P):
    print('%2d  a{%s} b{%s} -> c{%s}' % (k, f(a), f(b), f(gam[k])))
ntopA = sum(1 for s, (a, b) in lin.items() if not s.startswith(('A', 'B')) and a)
ntopB = sum(1 for s, (a, b) in lin.items() if not s.startswith(('A', 'B')) and b)
nbot = sum(1 for s in bot if len(bot[s]) != 1 or s not in [None]) - K
print('K=%d topA=%d topB=%d bottom=%d total=%d' % (K, ntopA, ntopB, nbot, K + ntopA + ntopB + nbot))
print('d(alpha)=%d d(beta)=%d d(gamma)=%d  floor 2K-8+d = %d' % (len(fa), len(fb), len(fg), 2*K-8+len(fa)+len(fb)+len(fg)))
print('distinct gamma cols (incl weight1): %d ; weight hist %s' % (len(set(gam)), sorted(w(g) for g in gam)))
print('symmetric (a,b)->(b,a) closed:', set(P) == {(b, a) for a, b in P})
