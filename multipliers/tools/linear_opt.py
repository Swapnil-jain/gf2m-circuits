"""Linear-layer optimiser for circuits whose AND set is fixed.

A bilinear circuit is   top (XORs over inputs) -> ANDs -> bottom (XORs over AND outputs and top/input signals).
We extract the two linear layers as binary matrices, re-synthesise each with our own SLP heuristics, splice
the result back around the SAME AND gates, and re-verify the whole circuit (exhaustive + symbolic).

  bottom matrix  rows = outputs, columns = AND outputs (plus any top/input signal the bottom reads).
                 For the 117-gate AES multiplier this is 8 x 48.
  top matrix     rows = distinct AND operands (and top signals read by the bottom) as forms over the inputs.

Heuristics (our implementations):
  paar    Paar 1997 greedy: repeatedly add the column pair occurring in the most remaining rows
          (cancellation-free); random tie-breaking, restarts.
  bp      Boyar-Peralta distance heuristic: base S, distance terms(t) = fewest base elements summing to t.
          Each step adds the pair-sum that most reduces the total distance (tie: larger norm of the distance
          vector, then random). Cancellation is allowed. Distances are exact up to 4 terms (meet in the middle
          over pair sums) and a greedy upper bound beyond that; a candidate's effect is detected exactly when the
          reduced target lands within 3 terms. A target at distance 2 is added at once.
  rnbp    bp with random tie-breaking and restarts (Visconti et al. style); this is the cancellation-aware search.

CLI:
  python3 linear_opt.py CIRCUIT --spec 0x11B [--layer bottom|top|both] [--restarts 50] [--seed 1]
         [--out results/linopt_117.json] [--save-circuit results/x.slp]
"""
import argparse
import json
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, load  # noqa: E402
import verify as V  # noqa: E402


# ---------------- layer extraction ----------------

def layers(c):
    """Split gates into pre (no AND below), and, post. Returns (pre, ands, post) gate index lists, or raises."""
    n = c.nin
    dep = [False] * (n + len(c.gates))     # depends on an AND
    pre, ands, post = [], [], []
    for i, (op, x, y) in enumerate(c.gates):
        s = n + i
        if op == "AND":
            if dep[x] or dep[y]:
                raise ValueError("AND of an AND: not a single-AND-layer circuit")
            ands.append(i)
            dep[s] = True
        elif op == "XOR":
            dep[s] = dep[x] or dep[y]
            (post if dep[s] else pre).append(i)
        else:
            raise ValueError(f"op {op} not supported by linear_opt")
    return pre, ands, post


def bottom_matrix(c):
    """Rows over columns = AND signals + other non-post signals read by the post layer."""
    n = c.nin
    pre, ands, post = layers(c)
    postset = set(n + i for i in post)
    cols = [n + i for i in ands]
    for i in post:
        op, x, y = c.gates[i]
        for p in (x, y):
            if p not in postset and p not in cols:
                cols.append(p)
    for o in c.outputs:
        if o not in postset and o not in cols:
            cols.append(o)
    ci = {s: k for k, s in enumerate(cols)}
    vec = {s: 1 << ci[s] for s in cols}
    for i in post:
        op, x, y = c.gates[i]
        vec[n + i] = vec[x] ^ vec[y]
    rows = [vec[o] for o in c.outputs]
    return cols, rows, len(post)


def top_matrix(c):
    """Targets = forms over inputs of every pre signal read by an AND or by the post layer (weight >= 2)."""
    n = c.nin
    pre, ands, post = layers(c)
    preset = set(n + i for i in pre)
    vec = {s: 1 << s for s in range(n)}
    for i in pre:
        op, x, y = c.gates[i]
        vec[n + i] = vec[x] ^ vec[y]
    needed = []
    for i in ands + post:
        op, x, y = c.gates[i]
        for p in (x, y):
            if p in preset and p not in needed:
                needed.append(p)
    for o in c.outputs:
        if o in preset and o not in needed:
            needed.append(o)
    return needed, [vec[p] for p in needed], len(pre)


# ---------------- SLP heuristics: base = unit vectors 0..ncols-1, targets = rows ----------------

def check_prog(ncols, rows, prog, where):
    vals = [1 << k for k in range(ncols)]
    for a, b in prog:
        vals.append(vals[a] ^ vals[b])
    return all(vals[w] == r for w, r in zip(where, rows))


def _finish(vals, rows):
    idx = {}
    for k, v in enumerate(vals):
        idx.setdefault(v, k)
    return [idx[r] for r in rows]


def paar(ncols, rows, rng):
    """Greedy common-pair elimination, cancellation-free. Returns (prog, where)."""
    vals = [1 << k for k in range(ncols)]
    rep = [set(k for k in range(ncols) if r >> k & 1) for r in rows]   # each row as a set of signal indices
    prog = []
    while True:
        cnt = {}
        for s in rep:
            if len(s) < 2:
                continue
            ls = sorted(s)
            for i in range(len(ls)):
                for j in range(i + 1, len(ls)):
                    cnt[(ls[i], ls[j])] = cnt.get((ls[i], ls[j]), 0) + 1
        if not cnt:
            break
        best = max(cnt.values())
        pick = rng.choice([p for p, v in cnt.items() if v == best])
        a, b = pick
        prog.append((a, b))
        vals.append(vals[a] ^ vals[b])
        new = len(vals) - 1
        for s in rep:
            if a in s and b in s:
                s.discard(a)
                s.discard(b)
                s.add(new)
    for r in rows:
        if r and r not in vals:
            raise AssertionError("paar did not reach a row")
    return prog, _finish(vals, rows)


def bp(ncols, rows, rng, randomize=True):
    """Boyar-Peralta style distance heuristic with cancellation. Returns (prog, where).

    Exact BP distances are out of reach for wide matrices (rows of weight 10-22 over 48 columns), so the
    distance of each target is estimated as min(|current decomposition|, exact distance when <= 4 terms).
    The decomposition starts as the row's support and is updated when a new base element covers a pair of it
    (Paar's gain) or when the exact small-distance search finds a shorter one, which may cancel (BP's gain).
    Each step adds the pair sum with the largest total reduction; ties go to the larger norm of the new
    distance vector, then at random (rnbp) or to the first (bp). A target at distance 2 is added at once."""
    vals = [1 << k for k in range(ncols)]
    S = {v: k for k, v in enumerate(vals)}
    prog = []
    targets = [r for r in dict.fromkeys(rows) if r and bin(r).count("1") >= 2]
    rep = {t: set(k for k in range(ncols) if t >> k & 1) for t in targets}

    def pairsums():
        ps = {}
        for i in range(len(vals)):
            vi = vals[i]
            for j in range(i + 1, len(vals)):
                v = vi ^ vals[j]
                if v not in ps and v not in S:
                    ps[v] = (i, j)
        return ps

    def exact_small(t, ps):
        """A decomposition of t into <= 4 base elements, as a list of indices, or None."""
        if t in S:
            return [S[t]]
        if t in ps:
            return list(ps[t])
        for v, k in S.items():
            if t ^ v in ps:
                return [k, *ps[t ^ v]]
        for p, ij in ps.items():
            if t ^ p in ps:
                return [*ij, *ps[t ^ p]]
        return None

    def add(i, j):
        v = vals[i] ^ vals[j]
        prog.append((i, j))
        vals.append(v)
        S[v] = len(vals) - 1
        k = len(vals) - 1
        for t, r in rep.items():
            if i in r and j in r:
                r.discard(i)
                r.discard(j)
                r.add(k)

    while True:
        todo = [t for t in targets if t not in S]
        if not todo:
            break
        ps = pairsums()
        near = [t for t in todo if t in ps]
        if near:
            add(*ps[near[0]])
            continue
        for t in todo:
            if len(rep[t]) > 3:
                d = exact_small(t, ps)
                if d is not None and len(d) < len(rep[t]):
                    rep[t] = set(d)
        dist = {t: len(rep[t]) for t in todo}
        gain = {}
        # Paar gains: a pair inside a decomposition saves one term there
        for t in todo:
            ls = sorted(rep[t])
            for x in range(len(ls)):
                for y in range(x + 1, len(ls)):
                    b = vals[ls[x]] ^ vals[ls[y]]
                    if b in ps:
                        g = gain.setdefault(b, {})
                        g[t] = max(g.get(t, 0), 1)
        # cancellation gains: t = b + (<= 2 base elements) with 3 terms < current
        for t in todo:
            if dist[t] <= 3:
                continue
            for v in vals:
                b = t ^ v
                if b in ps:
                    g = gain.setdefault(b, {})
                    g[t] = max(g.get(t, 0), dist[t] - 2)
            if dist[t] > 3:
                for p in ps:
                    b = t ^ p
                    if b in ps:
                        g = gain.setdefault(b, {})
                        g[t] = max(g.get(t, 0), dist[t] - 3)
        best_key, cands = None, []
        for b, red in gain.items():
            nd = [dist[t] - red.get(t, 0) for t in todo]
            key = (sum(red.values()), sum(x * x for x in nd))
            if best_key is None or key > best_key:
                best_key, cands = key, [b]
            elif key == best_key:
                cands.append(b)
        b = rng.choice(cands) if randomize else cands[0]
        i, j = ps[b]
        add(i, j)
        # a cancellation gain: rebuild the decomposition of the targets it served
        for t, r in gain[b].items():
            if dist[t] - r < len(rep[t]):
                d = exact_small(t ^ b, ps)
                if d is not None:
                    rep[t] = set(d) | {len(vals) - 1}
    return prog, _finish(vals, rows)


def run_heuristics(ncols, rows, restarts, seed, methods=("paar", "bp", "rnbp"), deadline=None):
    rng = random.Random(seed)
    best = {}
    for m in methods:
        reps = 1 if m == "bp" else restarts
        for r in range(reps):
            if deadline and time.time() > deadline:
                break
            if m == "paar":
                prog, where = paar(ncols, rows, rng)
            else:
                prog, where = bp(ncols, rows, rng if m == "rnbp" else random.Random(0), randomize=(m == "rnbp"))
            assert check_prog(ncols, rows, prog, where), m
            if m not in best or len(prog) < len(best[m][0]):
                best[m] = (prog, where)
    return best


# ---------------- splice ----------------

def rebuild(c, top=None, bottom=None):
    """Rebuild c with a new top and/or bottom layer. top/bottom = (prog, where) from the heuristics."""
    n = c.nin
    pre, ands, post = layers(c)
    gates = []
    sig = {s: s for s in range(n)}
    if top is None:
        for i in pre:
            op, x, y = c.gates[i]
            sig[n + i] = n + len(gates)
            gates.append((op, sig[x], sig[y]))
    else:
        needed, rows, _ = top_matrix(c)
        prog, where = top
        loc = list(range(n))
        for a, b in prog:
            loc.append(n + len(gates))
            gates.append(("XOR", loc[a], loc[b]))
        for p, w in zip(needed, where):
            sig[p] = loc[w]
    for i in ands:
        op, x, y = c.gates[i]
        sig[n + i] = n + len(gates)
        gates.append((op, sig[x], sig[y]))
    if bottom is None:
        for i in post:
            op, x, y = c.gates[i]
            sig[n + i] = n + len(gates)
            gates.append((op, sig[x], sig[y]))
        outs = [sig[o] for o in c.outputs]
    else:
        cols, rows, _ = bottom_matrix(c)
        prog, where = bottom
        loc = [sig[s] for s in cols]
        for a, b in prog:
            loc.append(n + len(gates))
            gates.append(("XOR", loc[a], loc[b]))
        outs = [loc[w] for w in where]
    return Circuit(c.na, c.nb, gates, outs, c.meta).prune()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("--spec", required=True)
    ap.add_argument("--layer", default="both", choices=["top", "bottom", "both"])
    ap.add_argument("--restarts", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--max-depth", type=int, default=None, help="use depth-capped Paar (depth.dpaar) for both layers; the result must have depth <= this")
    ap.add_argument("--time", type=float, default=600.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--save-circuit", default=None)
    a = ap.parse_args()
    c = load(a.circuit)
    spec = ("poly",) if a.spec == "poly" else ("field", int(a.spec, 0))
    assert V.symbolic(c, spec)
    t0 = time.time()
    dl = t0 + a.time
    rep = {"circuit": a.circuit, "spec": a.spec, "seed": a.seed, "restarts": a.restarts, "orig": c.counts()}
    best_top = best_bot = None
    if a.layer in ("bottom", "both"):
        cols, rows, cur = bottom_matrix(c)
        res = run_heuristics(len(cols), rows, a.restarts, a.seed, deadline=dl)
        rep["bottom"] = {"shape": [len(rows), len(cols)], "current_xor": cur,
                         "row_weights": [bin(r).count("1") for r in rows],
                         **{m: len(p) for m, (p, w) in res.items()}}
        m = min(res, key=lambda k: len(res[k][0]))
        if len(res[m][0]) < cur:
            best_bot = res[m]
    if a.layer in ("top", "both"):
        needed, rows, cur = top_matrix(c)
        res = run_heuristics(c.nin, rows, a.restarts, a.seed + 1, deadline=dl)
        rep["top"] = {"targets": len(rows), "current_xor": cur, **{m: len(p) for m, (p, w) in res.items()}}
        m = min(res, key=lambda k: len(res[k][0]))
        if len(res[m][0]) < cur:
            best_top = res[m]
    new = rebuild(c, best_top, best_bot)
    if a.max_depth is not None:
        import depth as Dp
        rng = random.Random(a.seed)
        best = new if new.depth() <= a.max_depth else None
        for _ in range(a.restarts):
            if time.time() > dl:
                break
            t = Dp.resynth(c, a.max_depth, rng, rng.choice([0, 2, 3, 4]), noise=rng.choice([0.0, 0.3, 1.0]))
            if t is not None and t.depth() <= a.max_depth and (best is None or len(t.gates) < len(best.gates)):
                best = t
        if best is None:
            print("no circuit within --max-depth"); return
        new = best
    ok_sym = V.symbolic(new, spec)
    ok_exh = V.exhaustive(new, spec) if new.nin <= V.MAX_EXHAUSTIVE else None
    rep["new"] = new.counts()
    rep["new_verified"] = {"symbolic": ok_sym, "exhaustive": ok_exh}
    rep["secs"] = round(time.time() - t0, 1)
    if a.save_circuit and ok_sym and ok_exh is not False:
        with open(a.save_circuit, "w") as f:
            f.write(new.to_text())
    with open(a.out, "w") as f:
        json.dump(rep, f, indent=1)
    print(json.dumps(rep))


if __name__ == "__main__":
    main()
