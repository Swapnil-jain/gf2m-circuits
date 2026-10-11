"""Build a GF(2^m) polynomial-basis multiplier from a published M(m) circuit (Find-Peralta / CMT files) by keeping its
top layers and AND products, replacing the bottom layer by the merged reduced output map, and re-synthesising both
linear layers with the author's tools (linear_opt: paar/bp/rnbp). Author's framework, paper section 3; stdlib only.
usage: python3 -I build_field.py --m 9 --poly 0x211 --out f9.slp [--src FILE] [--restarts 300] [--seeds 10] [--tools DIR]
"""
import argparse, glob, json, os, random, sys, time
ap = argparse.ArgumentParser()
ap.add_argument('--m', type=int, required=True); ap.add_argument('--poly', required=True); ap.add_argument('--out', required=True)
ap.add_argument('--src', default=None, help='M(m) circuit file (default: FP19 s_<m>* from the repo pack)')
ap.add_argument('--restarts', type=int, default=300); ap.add_argument('--seeds', type=int, default=10)
ap.add_argument('--tools', default=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')))
ap.add_argument('--no-exhaustive', action='store_true')
a = ap.parse_args()
sys.path.insert(0, os.path.abspath(a.tools))
from circuit import Circuit, load
import verify as V, linear_opt as L
m, P = a.m, int(a.poly, 0)
assert P.bit_length() - 1 == m, 'poly degree must equal m'
assert V.is_irreducible(P), 'polynomial is reducible'
src = a.src or sorted(glob.glob(os.path.join(a.tools, '..', 'sources', 'circuits', 'peralta_cmt', 'BinPolMult_extracted', 'BinPolMult', f's_{m}_m_*.opt.rem')) + glob.glob(os.path.join(a.tools, '..', 'sources', 'circuits', 'peralta_cmt', 'BinPolMult_extracted', 'BinPolMult', f's_{m}')))[0]
t0 = time.time()
c = load(src); assert c.na == c.nb == m and len(c.outputs) == 2 * m - 1
assert V.symbolic(c, ('poly',)), 'source M(m) circuit fails symbolic check'
spec = ('field', P)
# merged output map: out_i = XOR_k red[i][k] * (product-coefficient row k)
cols, rows, cur_bottom = L.bottom_matrix(c)
red = V.reduction_rows(m, P, 2 * m - 1)
merged = []
for i in range(m):
    r = 0
    for k in range(2 * m - 1):
        if red[i] >> k & 1: r ^= rows[k]
    merged.append(r)
# naive merged circuit: pre + ANDs unchanged, each output an XOR chain over its row
n = c.nin; pre, ands, post = L.layers(c)
gates, sig = [], {s: s for s in range(n)}
for i in pre + ands:
    op, x, y = c.gates[i]; sig[n + i] = n + len(gates); gates.append((op, sig[x], sig[y]))
loc = [sig[s] for s in cols]; outs = []
for r in merged:
    bits = [loc[k] for k in range(len(cols)) if r >> k & 1]
    cur = bits[0]
    for b in bits[1:]:
        gates.append(('XOR', cur, b)); cur = n + len(gates) - 1
    outs.append(cur)
naive = Circuit(m, m, gates, outs, {'source': src, 'poly': hex(P)}).prune()
assert V.symbolic(naive, spec), 'merged naive circuit fails symbolic field check'
print('naive merged', naive.counts(), 'src', os.path.basename(src), f'{time.time()-t0:.1f}s', flush=True)
# linear-layer re-synthesis: bottom and top, best over seeds x restarts
best = naive; rep = {'src': src, 'poly': hex(P), 'naive': naive.counts(), 'seeds': {}}
for seed in range(1, a.seeds + 1):   # --seeds 0 skips re-synthesis (naive merged circuit only)
    t1 = time.time()
    cols, rows, cur = L.bottom_matrix(naive)
    rb = L.run_heuristics(len(cols), rows, a.restarts, seed)
    mb = min(rb, key=lambda k: len(rb[k][0])); bot = rb[mb] if len(rb[mb][0]) < cur else None
    needed, trows, curt = L.top_matrix(naive)
    rt = L.run_heuristics(naive.nin, trows, a.restarts, seed + 1000)
    mt = min(rt, key=lambda k: len(rt[k][0])); top = rt[mt] if len(rt[mt][0]) < curt else None
    new = L.rebuild(naive, top, bot)
    ok = V.symbolic(new, spec)
    rep['seeds'][seed] = {'bottom': {k: len(v[0]) for k, v in rb.items()}, 'bottom_cur': cur, 'top': {k: len(v[0]) for k, v in rt.items()}, 'top_cur': curt, 'new': new.counts(), 'symbolic': ok, 'secs': round(time.time() - t1, 1)}
    print('seed', seed, rep['seeds'][seed], flush=True)
    if ok and len(new.gates) < len(best.gates): best = new
res = V.verify_full(best, spec, k=12, do_exhaustive=(not a.no_exhaustive) and best.nin <= V.MAX_EXHAUSTIVE)
rep['best'] = best.counts(); rep['verify'] = {k: (v if not isinstance(v, (list, tuple)) else list(v)) for k, v in res.items() if k != 'anf'}
rep['secs'] = round(time.time() - t0, 1)
with open(a.out, 'w') as f: f.write(best.to_text())
with open(a.out + '.json', 'w') as f: json.dump(rep, f, indent=1, default=str)
print('BEST', best.counts(), 'verify', rep['verify'], f'{rep["secs"]}s', flush=True)
