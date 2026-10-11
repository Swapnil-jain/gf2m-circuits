"""Baseline construction: a published M(m) circuit followed by the naive fold reduction modulo P (one XOR per fold,
cascading, as tools/naive_reduction.py counts it). Output verified with the author's verifier.
usage: python3 -I append_reduction.py --m 10 --poly 0x409 --out f10_base.slp [--src FILE] [--tools DIR]"""
import argparse, glob, os, sys
ap = argparse.ArgumentParser(); ap.add_argument('--m', type=int, required=True); ap.add_argument('--poly', required=True)
ap.add_argument('--out', required=True); ap.add_argument('--src', default=None); ap.add_argument('--controls', type=int, default=12)
ap.add_argument('--tools', default=os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')))
a = ap.parse_args(); sys.path.insert(0, os.path.abspath(a.tools))
from circuit import Circuit, load
import verify as V
m, P = a.m, int(a.poly, 0); assert V.is_irreducible(P) and P.bit_length() - 1 == m
d = os.path.join(a.tools, '..', 'sources', 'circuits', 'peralta_cmt', 'BinPolMult_extracted', 'BinPolMult')
src = a.src or sorted(glob.glob(os.path.join(d, f's_{m}_m_*.opt.rem')) + glob.glob(os.path.join(d, f's_{m}')))[0]
c = load(src); assert V.symbolic(c, ('poly',))
n = c.nin; gates = list(c.gates); cur = list(c.outputs)      # cur[k] = signal holding coefficient k
terms = [e for e in range(m) if P >> e & 1]
for k in range(2 * m - 2, m - 1, -1):
    for e in terms:
        gates.append(('XOR', cur[k - m + e], cur[k])); cur[k - m + e] = n + len(gates) - 1
new = Circuit(m, m, gates, cur[:m], {'source': src, 'poly': hex(P), 'construction': 'M(m) + naive fold reduction'}).prune()
res = V.verify_full(new, ('field', P), k=a.controls, do_exhaustive=new.nin <= V.MAX_EXHAUSTIVE)
open(a.out, 'w').write(new.to_text()); print(os.path.basename(src), new.counts(), {k: v for k, v in res.items() if k != 'anf'})
