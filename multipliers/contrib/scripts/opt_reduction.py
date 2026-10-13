"""Keep the published M(m) circuit whole and optimise only the reduction layer, instead of
appending the naive fold cascade. For a trinomial the naive cascade is already optimal, but for
a pentanomial the reduction matrix has shared subexpressions worth finding.

usage: python3 -I opt_reduction.py --m 16 --poly 0x1002b --out f16_opt.slp --restarts 2000 --seed 1
"""
import argparse, glob, json, os, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--m', type=int, required=True)
ap.add_argument('--poly', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--restarts', type=int, default=400)
ap.add_argument('--seed', type=int, default=1)
ap.add_argument('--tools', default=os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')))
a = ap.parse_args()
sys.path.insert(0, os.path.abspath(a.tools))
from circuit import Circuit, load
import verify as V, linear_opt as L

m, P = a.m, int(a.poly, 0)
assert P.bit_length() - 1 == m and V.is_irreducible(P)
src = sorted(glob.glob(os.path.join(a.tools, '..', 'sources', 'circuits', 'peralta_cmt',
                                    'BinPolMult_extracted', 'BinPolMult', f's_{m}_m_*.opt.rem'))
             + glob.glob(os.path.join(a.tools, '..', 'sources', 'circuits', 'peralta_cmt',
                                      'BinPolMult_extracted', 'BinPolMult', f's_{m}')))[0]
t0 = time.time()
c = load(src)
assert c.na == c.nb == m and len(c.outputs) == 2 * m - 1
assert V.symbolic(c, ('poly',))

# optimise the m x (2m-1) reduction map over the product coefficients the source already computes
red = list(V.reduction_rows(m, P, 2 * m - 1))
rh = L.run_heuristics(2 * m - 1, red, a.restarts, a.seed)
name = min(rh, key=lambda k: len(rh[k][0]))
prog, where = rh[name]

# emit: the whole source circuit, then the reduction program on top of its outputs
gates = list(c.gates)
n = c.nin
sig = list(c.outputs)                       # signal id of each product coefficient
for (i, j) in prog:
    gates.append(('XOR', sig[i], sig[j]))
    sig.append(n + len(gates) - 1)
outs = [sig[where[i]] for i in range(m)]
new = Circuit(m, m, gates, outs, {'source': src, 'poly': hex(P),
                                  'reduction': f'{name}/{len(prog)} XOR'}).prune()
res = V.verify_full(new, ('field', P), k=12, do_exhaustive=(new.nin <= V.MAX_EXHAUSTIVE))
rep = {'m': m, 'poly': hex(P), 'seed': a.seed, 'restarts': a.restarts,
       'reduction': {k: len(v[0]) for k, v in rh.items()}, 'picked': name,
       'reduction_xors': len(prog), 'counts': new.counts(),
       'verify': {k: (list(v) if isinstance(v, tuple) else v)
                  for k, v in res.items() if k != 'anf'},
       'secs': round(time.time() - t0, 1)}
if res['ok']:
    open(a.out, 'w').write(new.to_text())
json.dump(rep, open(a.out + '.json', 'w'), indent=1)
print('RESULT', json.dumps(rep), flush=True)
