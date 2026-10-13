"""Re-run the repository's depth sweep on its own output until it stops improving.

Each sweep retimes the circuit under a depth cap and sometimes drops a gate on the way, so the
output is worth feeding back in. Keeps the best circuit at every depth seen (the Pareto set) and
stops when a whole round adds nothing.

usage: python3 -I iterate_depth.py --start f14.slp --spec 0x4021 --caps 7-13 --rounds 6 --outdir it14
"""
import argparse, glob, json, os, re, shutil, subprocess, sys, time

ap = argparse.ArgumentParser()
ap.add_argument('--start', required=True)
ap.add_argument('--spec', required=True)
ap.add_argument('--caps', default='7-13')
ap.add_argument('--rounds', type=int, default=6)
ap.add_argument('--tries', type=int, default=250)
ap.add_argument('--time', type=int, default=300)
ap.add_argument('--outdir', required=True)
ap.add_argument('--tools', default=os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools')))
a = ap.parse_args()
sys.path.insert(0, os.path.abspath(a.tools))
from circuit import load
import verify as V

os.makedirs(a.outdir, exist_ok=True)
spec = ('field', int(a.spec, 0))
pareto = {}          # depth -> (gates, path)


def offer(path):
    c = load(path)
    n = c.counts()
    d, g = n['depth'], n['total']
    if d in pareto and pareto[d][0] <= g:
        return False
    # a new point is only interesting if nothing shallower is also smaller or equal
    if any(dd <= d and gg <= g for dd, (gg, _) in pareto.items()):
        return False
    keep = os.path.join(a.outdir, f'g{g}_d{d}.slp')
    shutil.copyfile(path, keep)
    pareto[d] = (g, keep)
    for dd in [dd for dd, (gg, _) in pareto.items() if dd > d and gg >= g]:
        del pareto[dd]
    return True


offer(a.start)
frontier = [a.start]
for rnd in range(1, a.rounds + 1):
    work = os.path.join(a.outdir, f'round{rnd}')
    os.makedirs(work, exist_ok=True)
    found = False
    for i, f in enumerate(sorted(set(frontier))):
        subprocess.run([sys.executable, '-I', os.path.join(a.tools, 'depth.py'), 'sweep', f,
                        '--spec', a.spec, '--depths', a.caps, '--tries', str(a.tries),
                        '--seed', str(rnd * 10 + i), '--time', str(a.time),
                        '--outdir', os.path.join(work, str(i))],
                       capture_output=True, text=True)
    for out in glob.glob(os.path.join(work, '*', '*.slp')):
        if offer(out):
            found = True
    frontier = [p for _, p in pareto.values()]
    print(f'round {rnd}: ' + ', '.join(f'{g}@d{d}' for d, (g, _) in sorted(pareto.items())),
          flush=True)
    if not found:
        break

print('\nverifying the Pareto set')
rows = []
for d, (g, p) in sorted(pareto.items()):
    c = load(p)
    res = V.verify_full(c, spec, k=12, do_exhaustive=(c.nin <= V.MAX_EXHAUSTIVE))
    rows.append({'depth': d, 'gates': g, 'file': p, 'counts': c.counts(),
                 'verify': {k: (list(v) if isinstance(v, tuple) else v)
                            for k, v in res.items() if k != 'anf'}})
    print(f"  {g} gates at depth {d}: ok={res['ok']} exhaustive={res.get('exhaustive')}  {p}")
json.dump(rows, open(os.path.join(a.outdir, 'PARETO.json'), 'w'), indent=1)
print('wrote', os.path.join(a.outdir, 'PARETO.json'))
