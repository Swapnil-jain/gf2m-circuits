"""Depth tools for AND/XOR circuits: depth, XOR-tree rebalancing, and depth-capped linear-layer resynthesis.

  depth(c)               circuit depth (AND and XOR each cost 1)
  rebalance(c)           zero-cost: re-associate every XOR tree (leaves = inputs, ANDs, and XORs read more than once or
                         that are outputs) into a minimum-depth tree. Gate count never changes, depth never rises.
  dpaar(...)             Paar greedy pair elimination under per-row deadlines. A row of leaves with arrival times a_i
                         can be finished by some XOR tree of depth <= R iff sum 2^a_i <= 2^R (Kraft), so a shared pair
                         is only taken in rows where that still holds. Cancellation-free. Leftovers are finished
                         with private Huffman trees.
  resynth(c, D, rng)     top -> AND -> bottom circuits (all ours are): re-synthesise the top layer under a depth cap dt,
                         then the bottom layer under the total cap D. This is the gates-vs-depth trade-off knob.
  sweep(c, spec, D, ...) best verified circuit found with depth <= D.

CLI:
  python3 depth.py sweep FILE --spec 0x11B --depths 6-12 --tries 200 --seed 1 --outdir results/depth
  python3 depth.py pareto DIR [DIR ...] --out results/PARETO.md     (re-verifies every point with verify.verify_full)
"""
import argparse
import hashlib
import heapq
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, load  # noqa: E402
import linear_opt as L  # noqa: E402
import verify as V  # noqa: E402


def depth(c):
    return c.depth()


def arrivals(c):
    n = c.nin
    d = [0] * (n + len(c.gates))
    for i, (op, x, y) in enumerate(c.gates):
        d[n + i] = 1 + max(d[x], d[y] if y is not None else 0)
    return d


def rebalance(c):
    """Minimum-depth re-association of XOR trees, keeping every shared signal and every gate count."""
    c = c.prune()
    n = c.nin
    fan = [0] * (n + len(c.gates))
    xorfan = [0] * (n + len(c.gates))      # reads by XOR gates only
    for op, x, y in c.gates:
        for p in (x, y):
            if p is not None:
                fan[p] += 1
                xorfan[p] += op == "XOR"
    isout = set(c.outputs)
    gates = []
    sig = {s: s for s in range(n)}
    arr = {s: 0 for s in range(n)}

    def leaves(s, acc):
        op, x, y = c.gates[s - n]
        for p in (x, y):
            if p >= n and c.gates[p - n][0] == "XOR" and fan[p] == 1 and xorfan[p] == 1 and p not in isout:
                leaves(p, acc)
            else:
                acc.append(p)

    for i, (op, x, y) in enumerate(c.gates):
        s = n + i
        if op == "XOR" and fan[s] == 1 and xorfan[s] == 1 and s not in isout:
            continue            # interior of a tree: rebuilt from its root
        if op == "XOR":
            lv = []
            leaves(s, lv)
            h = [(arr[sig[p]], k, sig[p]) for k, p in enumerate(lv)]
            heapq.heapify(h)
            cnt = len(h)
            while len(h) > 1:
                a1, _, p1 = heapq.heappop(h)
                a2, _, p2 = heapq.heappop(h)
                gates.append(("XOR", p1, p2))
                ns = n + len(gates) - 1
                arr[ns] = max(a1, a2) + 1
                cnt += 1
                heapq.heappush(h, (arr[ns], cnt, ns))
            sig[s] = h[0][2]
        else:
            gates.append((op, sig[x], None if y is None else sig[y]))
            sig[s] = n + len(gates) - 1
            arr[sig[s]] = 1 + max(arr[sig[x]], arr[sig[y]] if y is not None else 0)
    return Circuit(c.na, c.nb, gates, [sig[o] for o in c.outputs], c.meta)


def dpaar(ncols, rows, arr, deadline, rng, noise=0.0):
    """Depth-capped Paar. rows: ints over ncols base signals with arrival times arr. deadline: int or list per row.
    Returns (prog, where) in the linear_opt format, or None if some row cannot meet its deadline at all."""
    dl = deadline if isinstance(deadline, list) else [deadline] * len(rows)
    rep, cap = [], []
    for r, R in zip(rows, dl):
        s = {k for k in range(ncols) if r >> k & 1}
        if sum(1 << arr[k] for k in s) > 1 << R:
            return None
        rep.append(s)
        cap.append(1 << R)
    ar = list(arr)
    vals = [1 << k for k in range(ncols)]
    kr = [sum(1 << ar[k] for k in s) for s in rep]
    prog = []
    while True:
        cnt = {}
        for ri, s in enumerate(rep):
            if len(s) < 2:
                continue
            ls = sorted(s)
            for i in range(len(ls)):
                for j in range(i + 1, len(ls)):
                    a, b = ls[i], ls[j]
                    na = max(ar[a], ar[b]) + 1
                    if kr[ri] - (1 << ar[a]) - (1 << ar[b]) + (1 << na) <= cap[ri]:
                        cnt[(a, b)] = cnt.get((a, b), 0) + 1
        if not cnt:
            break
        sc = {p: v - 0.05 * max(ar[p[0]], ar[p[1]]) + (noise * rng.random() if noise else 0) for p, v in cnt.items()}
        best = max(sc.values())
        a, b = rng.choice([p for p, v in sc.items() if v >= best - 1e-9])
        na = max(ar[a], ar[b]) + 1
        new = len(vals)
        vals.append(vals[a] ^ vals[b])
        ar.append(na)
        prog.append((a, b))
        for ri, s in enumerate(rep):
            if a in s and b in s and kr[ri] - (1 << ar[a]) - (1 << ar[b]) + (1 << na) <= cap[ri]:
                kr[ri] += (1 << na) - (1 << ar[a]) - (1 << ar[b])
                s.discard(a)
                s.discard(b)
                s.add(new)
    for s in rep:           # private Huffman finish
        if len(s) < 2:
            continue
        h = [(ar[k], k) for k in s]
        heapq.heapify(h)
        while len(h) > 1:
            a1, p1 = heapq.heappop(h)
            a2, p2 = heapq.heappop(h)
            prog.append((p1, p2))
            vals.append(vals[p1] ^ vals[p2])
            ar.append(max(a1, a2) + 1)
            heapq.heappush(h, (ar[-1], len(vals) - 1))
    return prog, L._finish(vals, rows)


def _uniq(rows):
    u = sorted(set(rows))
    return u


def resynth(c, D, rng, dt, noise=0.3):
    """One randomised top+bottom resynthesis; dt = top depth cap (0 = each row at its own minimum). Returns circuit or None."""
    n = c.nin
    needed, rows, _ = L.top_matrix(c)
    if dt == 0:
        ur = _uniq(rows)
        dl = [max(0, (bin(r).count("1") - 1).bit_length()) for r in ur]
    else:
        ur = _uniq(rows)
        dl = dt
    res = dpaar(n, ur, [0] * n, dl, rng, noise)
    if res is None:
        return None
    prog, where = res
    idx = {r: w for r, w in zip(ur, where)}
    c1 = L.rebuild(c, (prog, [idx[r] for r in rows]), None)
    cols, brow, _ = L.bottom_matrix(c1)
    ar = arrivals(c1)
    ub = _uniq(brow)
    res = dpaar(len(cols), ub, [ar[s] for s in cols], D, rng, noise)
    if res is None:
        return None
    prog, where = res
    idx = {r: w for r, w in zip(ub, where)}
    return L.rebuild(c1, None, (prog, [idx[r] for r in brow]))


def sweep(c, spec, D, tries, rng, deadline_t=None):
    best = None
    if depth(c) <= D:
        best = c
    rb = rebalance(c)
    if depth(rb) <= D and (best is None or len(rb.gates) < len(best.gates)):
        best = rb
    for t in range(tries):
        if deadline_t and time.time() > deadline_t:
            break
        dt = rng.choice([0] + list(range(1, max(2, D - 1))))
        try:
            new = resynth(c, D, rng, dt, noise=rng.choice([0.0, 0.3, 1.0]))
        except ValueError:      # not a single-AND-layer circuit
            return best
        if new is None or depth(new) > D:
            continue
        if best is None or len(new.gates) < len(best.gates):
            if V.symbolic(new, spec) and V.exhaustive(new, spec):
                best = new
    return best


def parse_spec(s):
    return ("poly",) if s == "poly" else ("field", int(s, 0))


def cmd_sweep(a):
    c = load(a.file)
    spec = parse_spec(a.spec)
    assert V.symbolic(c, spec)
    lo, hi = (int(x) for x in a.depths.split("-"))
    rng = random.Random(a.seed)
    os.makedirs(a.outdir, exist_ok=True)
    base = os.path.basename(a.file).replace(".", "_")
    t_end = time.time() + a.time
    for D in range(lo, hi + 1):
        b = sweep(c, spec, D, a.tries, rng, t_end)
        if b is not None:
            p = os.path.join(a.outdir, f"{base}_d{D}_s{a.seed}_g{len(b.gates)}_D{depth(b)}.slp")
            with open(p, "w") as f:
                f.write(b.to_text())
            print(f"{a.file} cap={D} -> gates={len(b.gates)} depth={depth(b)}", flush=True)
        else:
            print(f"{a.file} cap={D} -> none", flush=True)


def cmd_pareto(a):
    pts = []
    for d in a.dirs:
        for r, _, fs in os.walk(d):
            for fn in fs:
                if fn.endswith(".slp"):
                    p = os.path.join(r, fn)
                    try:
                        c = load(p)
                    except Exception:
                        continue
                    pts.append((len(c.gates), depth(c), p))
    # best gate count per depth, then keep only strictly improving points (Pareto)
    bydepth = {}
    for g, dd, p in sorted(pts):
        bydepth.setdefault(dd, []).append((g, p))
    front, bestg = [], 10 ** 9
    for dd in sorted(bydepth):
        for g, p in bydepth[dd]:
            c = load(p)
            if V.verify_full(c, parse_spec(a.spec), k=a.controls)["ok"]:
                if g < bestg:
                    front.append((g, dd, p))
                    bestg = g
                break
    lines = ["# GF(2^8) 0x11B multipliers: gates vs depth (Pareto front)", "",
             "Each row passed verify.py: exhaustive (all 65,536 pairs), symbolic, and the must-fail controls. "
             "Best gate count at each depth, kept only if it beats every shallower point.", "",
             "| Gates | Depth | SHA-256 | File |", "|---|---|---|---|"]
    for g, dd, p in front:
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        lines.append(f"| {g} | {dd} | {h[:16]}... | {p} |")
    open(a.out, "w").write("\n".join(lines) + "\n")
    print("\n".join(lines))


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sweep")
    s.add_argument("file")
    s.add_argument("--spec", default="0x11B")
    s.add_argument("--depths", default="6-12")
    s.add_argument("--tries", type=int, default=200)
    s.add_argument("--seed", type=int, default=1)
    s.add_argument("--time", type=float, default=1e9)
    s.add_argument("--outdir", required=True)
    p = sub.add_parser("pareto")
    p.add_argument("dirs", nargs="+")
    p.add_argument("--spec", default="0x11B")
    p.add_argument("--controls", type=int, default=5)
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    (cmd_sweep if a.cmd == "sweep" else cmd_pareto)(a)


if __name__ == "__main__":
    main()
