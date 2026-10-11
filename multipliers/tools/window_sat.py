"""Window re-synthesis for AND/XOR circuits (port of ~/mobius-exp/search/window_sat.py from XOR-only to AND/XOR).

A window is a CONNECTED, CONVEX set of w gates (convex: no path leaves the window and comes back, so the
replacement can be spliced in topological order). Its frontier is the set of outside signals the window reads;
its outputs are the window signals read outside it or used as circuit outputs. We ask SAT for w-1 gates over the
frontier that produce every output value. Every hit is spliced back, dead gates are pruned, and the WHOLE circuit
is re-verified exhaustively (verify.exhaustive) and symbolically (verify.symbolic) before it is accepted.

Value semantics (--sem):
  local   truth tables over the window's frontier (frontier <= --maxfront bits, default 10). Strongest
          requirement (no don't-cares), exact for any circuit.
  anf2    typed values: the exact ANF of each signal restricted to degree <= 2 (constant, a_i/b_j, and all
          x_p x_q products: 1 + n + n(n-1)/2 bits; 137 at m = 8). Equal ANF = equal function, so this is exact
          for bilinear circuits at any m. AND gates in the replacement may only take degree <= 1 operands, so an
          UNSAT is a claim only about degree-2-bounded replacements; a SAT is always sound.
  global  full truth tables over all inputs (2^(na+nb) bits; only for na+nb <= 12).

Solver: pysat (glucose4 by default; it must support interrupt, which pysat's CaDiCaL does not) on the box. Without pysat (the Mac) the script falls back to our own exact
enumerator (greedy target closure + DFS over free gates), which is practical for w-1 <= ~5.

Symmetry breaking (sound for ANY circuit of exactly G gates, no minimality needed): operands x < y, and for
adjacent gates the key (y, x, type) is non-decreasing. Proof: bubble-sort adjacent INDEPENDENT pairs whose key
decreases; a swap keeps both gates' operands, leaves earlier keys alone and lowers the key at position i, so the
key sequence decreases lexicographically and the process ends. A dependent pair has y_{i+1} = gate i > y_i.
Padding: a circuit with fewer than G gates is padded with copies, so "exactly G gates" is SAT whenever "<= G" is.

Driver:
  python3 window_sat.py CIRCUIT --spec poly|0x11B --sem anf2 --wmin 4 --wmax 9 --budget 5 --total 1800 \
      --seed 1 --out results/win_run.json [--hits results/hits] [--plateau 0.3] [--max-and K]
"""
import argparse
import itertools
import json
import os
import random
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import Circuit, load  # noqa: E402
import verify as V  # noqa: E402

try:
    from pysat.card import CardEnc, EncType
    from pysat.formula import IDPool
    from pysat.solvers import Solver
    HAVE_PYSAT = True
except ImportError:          # the Mac has no pysat; the enumerator is used instead
    HAVE_PYSAT = False


# ---------------- value semantics ----------------

class TT:
    """Truth tables on `nvars` variables; values are ints of 2^nvars bits."""

    def __init__(self, nvars):
        self.nvars = nvars
        self.bits = 1 << nvars
        self.full = (1 << self.bits) - 1
        self.var, _ = V._var_masks(nvars) if nvars else ([], 1)
        self.and_terms = [[(j, j)] for j in range(self.bits)]
        self.and_zero = []           # value bits an AND operand must have clear

    def AND(self, u, v):
        return u & v

    def XOR(self, u, v):
        return u ^ v


class ANF2:
    """Degree <= 2 ANF over n inputs. Bit 0: constant; 1+s: x_s; then x_p x_q for p < q."""

    def __init__(self, n):
        self.n = n
        self.lin = [1 + s for s in range(n)]
        self.quad = {}
        k = 1 + n
        for p in range(n):
            for q in range(p + 1, n):
                self.quad[(p, q)] = k
                k += 1
        self.bits = k
        self.qmask = ((1 << k) - 1) ^ ((1 << (1 + n)) - 1)
        self.var = [1 << (1 + s) for s in range(n)]
        # product terms of an AND of two degree-<=1 values, per result bit (index pairs into operand bits)
        t = [[] for _ in range(k)]
        t[0].append((0, 0))
        for p in range(n):
            t[1 + p] += [(0, 1 + p), (1 + p, 0), (1 + p, 1 + p)]
        for (p, q), b in self.quad.items():
            t[b] += [(1 + p, 1 + q), (1 + q, 1 + p)]
        self.and_terms = t
        self.and_zero = list(range(1 + n, k))

    def AND(self, u, v):
        if (u | v) & self.qmask:
            return None
        r = 0
        for j, terms in enumerate(self.and_terms):
            par = 0
            for i1, i2 in terms:
                par ^= (u >> i1) & (v >> i2) & 1
            if par:
                r |= 1 << j
        return r

    def XOR(self, u, v):
        return u ^ v

    def from_monos(self, monos):
        r = 0
        for m in monos:
            bc = bin(m).count("1")
            if bc == 0:
                r ^= 1
            elif bc == 1:
                r ^= 1 << (1 + m.bit_length() - 1)
            elif bc == 2:
                p = (m & -m).bit_length() - 1
                q = m.bit_length() - 1
                r ^= 1 << self.quad[(p, q)]
            else:
                return None
        return r


def global_values(c, sem):
    """Value of every signal under `sem` (anf2 or global tt); None where not representable."""
    if isinstance(sem, ANF2):
        monos = V.anf_signals_all(c)
        return [sem.from_monos(m) for m in monos]
    vals = list(sem.var)
    for op, x, y in c.gates:
        vals.append(sem.AND(vals[x], vals[y]) if op == "AND" else vals[x] ^ vals[y])
    return vals


# ---------------- windows ----------------

def graph(c):
    n = c.nin
    users = [[] for _ in range(n + len(c.gates))]
    for i, (op, x, y) in enumerate(c.gates):
        for p in {x, y}:
            if p is not None:
                users[p].append(n + i)
    return users


def downstream(users, W):
    """Gates outside W reachable from W; None if one of them feeds back into W (W not convex)."""
    down = set()
    stack = [u for s in W for u in users[s] if u not in W]
    while stack:
        s = stack.pop()
        if s in down:
            continue
        down.add(s)
        for u in users[s]:
            if u in W:
                return None
            stack.append(u)
    return down


def pick_window(c, users, seed_sig, w, rng):
    """Grow a connected set of gate signals from seed by random BFS over fan-in and fan-out; make it convex."""
    n = c.nin
    W = {seed_sig}
    frontier = [seed_sig]
    while len(W) < w and frontier:
        s = rng.choice(frontier)
        op, x, y = c.gates[s - n]
        nb = [p for p in (x, y) if p is not None and p >= n] + users[s]
        nb = [p for p in nb if p not in W]
        if not nb:
            frontier.remove(s)
            continue
        p = rng.choice(nb)
        W.add(p)
        frontier.append(p)
    # convexity: no gate outside W may be both downstream of W and upstream of W
    if downstream(users, W) is None:
        return None
    return W


def window_io(c, users, W):
    n = c.nin
    outs_set = set(c.outputs)
    fr = []
    for s in sorted(W):
        op, x, y = c.gates[s - n]
        for p in (x, y):
            if p is not None and p not in W and p not in fr:
                fr.append(p)
    wout = [s for s in sorted(W) if s in outs_set or any(u not in W for u in users[s])]
    return fr, wout


def local_values(c, W, fr):
    n = c.nin
    sem = TT(len(fr))
    val = {p: sem.var[k] for k, p in enumerate(fr)}
    for s in sorted(W):
        op, x, y = c.gates[s - n]
        val[s] = sem.AND(val[x], val[y]) if op == "AND" else val[x] ^ val[y]
    return sem, val


# ---------------- SAT ----------------

SOLVER = "glucose4"   # must support interrupt(): pysat's CaDiCaL does not, so its time budget would be ignored


def sat_window(sem, avail, needed, G, budget_s, max_and=None, symbreak=True, block=None, seed=0):
    """G gates (AND/XOR) over constant values `avail` producing every value in `needed`.
    Returns list of (op, i, j) over indices into avail + new gates; None if UNSAT; 'unknown' on timeout."""
    na = len(avail)
    B = sem.bits
    pool = IDPool()
    v = lambda *t: pool.id(t)  # noqa: E731
    cl = []

    def xor2(a, b, z):
        cl.extend([[-a, -b, -z], [a, b, -z], [a, -b, z], [-a, b, z]])

    for i in range(G):
        s = na + i
        t = v("t", i)    # 1 = AND, 0 = XOR
        for side in ("x", "y"):
            lits = [v(side, i, p) for p in range(s)]
            cl.extend(CardEnc.equals(lits=lits, bound=1, vpool=pool, encoding=EncType.seqcounter).clauses)
        # x < y
        for q in range(s):
            cl.append([-v("y", i, q)] + [v("x", i, p) for p in range(q)])
        # operand value bits
        for j in range(B):
            for side in ("x", "y"):
                sv = v("s" + side, i, j)
                for p in range(s):
                    sel = v(side, i, p)
                    if p < na:
                        cl.append([-sel, sv] if avail[p] >> j & 1 else [-sel, -sv])
                    else:
                        cl.append([-sel, -v("val", p, j), sv])
                        cl.append([-sel, v("val", p, j), -sv])
        # AND operands must have the required-zero bits clear (anf2: degree <= 1)
        for j in sem.and_zero:
            cl.append([-t, -v("sx", i, j)])
            cl.append([-t, -v("sy", i, j)])
        for j in range(B):
            z = v("val", s, j)
            xv = v("xr", i, j)
            xor2(v("sx", i, j), v("sy", i, j), xv)
            terms = sem.and_terms[j]
            prods = []
            for (i1, i2) in terms:
                pz = v("pr", i, i1, i2)
                a_, b_ = v("sx", i, i1), v("sy", i, i2)
                cl.extend([[-pz, a_], [-pz, b_], [pz, -a_, -b_]])
                prods.append(pz)
            acc = prods[0]
            for k, pz in enumerate(prods[1:]):
                nz = v("pacc", i, j, k)
                xor2(acc, pz, nz)
                acc = nz
            cl.extend([[-t, -acc, z], [-t, acc, -z], [t, -xv, z], [t, xv, -z]])
    if symbreak:
        for i in range(G - 1):
            s0, s1 = na + i, na + i + 1
            # y_{i+1} >= y_i
            for q in range(s0):
                cl.append([-v("y", i, q)] + [v("y", i + 1, r) for r in range(q, s1)])
            # y equal -> x_{i+1} >= x_i ; x and y equal -> t_{i+1} >= t_i
            for q in range(s0):
                for p in range(q):
                    cl.append([-v("y", i, q), -v("y", i + 1, q), -v("x", i, p)] + [v("x", i + 1, r) for r in range(p, q)])
                    cl.append([-v("y", i, q), -v("y", i + 1, q), -v("x", i, p), -v("x", i + 1, p), -v("t", i), v("t", i + 1)])
    for k, tv in enumerate(needed):
        os_ = [v("o", k, i) for i in range(G)]
        cl.append(os_)
        for i in range(G):
            for j in range(B):
                cl.append([-os_[i], v("val", na + i, j) if tv >> j & 1 else -v("val", na + i, j)])
    if max_and is not None:
        cl.extend(CardEnc.atmost(lits=[v("t", i) for i in range(G)], bound=max_and, vpool=pool,
                                 encoding=EncType.seqcounter).clauses)
    if block is not None:
        lits = []
        for i, (op, a, b) in enumerate(block):
            lits += [-v("x", i, a), -v("y", i, b), -v("t", i) if op == "AND" else v("t", i)]
        cl.append(lits)
    random.Random(seed).shuffle(cl)
    with Solver(name=SOLVER, bootstrap_with=cl) as S:
        timer = threading.Timer(budget_s, S.interrupt)
        timer.start()
        try:
            r = S.solve_limited(expect_interrupt=True)
        finally:
            timer.cancel()
        if r is None:
            return "unknown"
        if not r:
            return None
        pos = set(l for l in S.get_model() if l > 0)
    out = []
    for i in range(G):
        s = na + i
        a = next(p for p in range(s) if v("x", i, p) in pos)
        b = next(p for p in range(s) if v("y", i, p) in pos)
        out.append(("AND" if v("t", i) in pos else "XOR", a, b))
    return out


# ---------------- enumerator (no pysat) ----------------

def enum_window(sem, avail, needed, G, budget_s, max_and=None, **_):
    """Exact search for <= G gates. Targets are added greedily whenever one gate makes them (never harmful:
    every target needs its own gate); DFS branches only on the free (non-target) gates."""
    deadline = time.time() + budget_s
    need = set(needed)
    nt = len(need)
    if nt > G:
        return None
    timed_out = [False]

    def ops(u, w_):
        yield "XOR", u ^ w_
        a = sem.AND(u, w_)
        if a is not None:
            yield "AND", a

    def closure(vals, prog, missing, nand):
        changed = True
        while changed and missing:
            changed = False
            idx = {x: i for i, x in enumerate(vals)}
            for tv in list(missing):
                hit = None
                for i in range(len(vals)):
                    j = idx.get(vals[i] ^ tv)
                    if j is not None and j != i:
                        hit = ("XOR", min(i, j), max(i, j))
                        break
                if hit is None and (max_and is None or nand < max_and):
                    for i in range(len(vals)):
                        for j in range(i + 1, len(vals)):
                            if sem.AND(vals[i], vals[j]) == tv:
                                hit = ("AND", i, j)
                                break
                        if hit:
                            break
                if hit:
                    prog.append(hit)
                    vals.append(tv)
                    missing.discard(tv)
                    nand += hit[0] == "AND"
                    changed = True
        return nand

    def dfs(vals, prog, missing, nand):
        if time.time() > deadline:
            timed_out[0] = True
            return None
        vals, prog, missing = list(vals), list(prog), set(missing)
        nand = closure(vals, prog, missing, nand)
        if not missing:
            return prog
        free = G - len(prog) - len(missing)
        if free <= 0:
            return None
        seen = set(vals)
        for i in range(len(vals)):
            for j in range(i + 1, len(vals)):
                for op, r in ops(vals[i], vals[j]):
                    if r in seen or (op == "AND" and max_and is not None and nand >= max_and):
                        continue
                    seen.add(r)
                    res = dfs(vals + [r], prog + [(op, i, j)], missing, nand + (op == "AND"))
                    if res is not None:
                        return res
                    if timed_out[0]:
                        return None
        return None

    r = dfs(list(avail), [], {t for t in need if t not in set(avail)}, 0)
    if r is None and timed_out[0]:
        return "unknown"
    return r


def solve(*a, **k):
    return (sat_window if HAVE_PYSAT else enum_window)(*a, **k)


# ---------------- splice ----------------

def splice(c, W, fr, wout, repl, out_vals, vals_avail_new):
    """New circuit: gates not downstream of W, then the replacement, then the downstream gates.
    repl indexes 0..len(fr)-1 = frontier, then its own gates. out_vals maps each window output to the index
    (into fr + repl gates) producing its value."""
    n = c.nin
    down = downstream(graph(c), W)
    assert down is not None, "window is not convex"
    gates = []
    remap = {s: s for s in range(n)}
    for i, g in enumerate(c.gates):
        s = n + i
        if s in W or s in down:
            continue
        op, x, y = g
        remap[s] = n + len(gates)
        gates.append((op, remap[x], None if y is None else remap[y]))
    loc = [remap[p] for p in fr]
    for op, a, b in repl:
        loc.append(n + len(gates))
        gates.append((op, loc[a], loc[b]))
    for s, k in zip(wout, out_vals):
        remap[s] = loc[k]
    for i, g in enumerate(c.gates):
        s = n + i
        if s not in down:
            continue
        op, x, y = g
        remap[s] = n + len(gates)
        gates.append((op, remap[x], None if y is None else remap[y]))
    return Circuit(c.na, c.nb, gates, [remap[o] for o in c.outputs], c.meta).prune()


# ---------------- one step and the driver ----------------

def full_check(c, spec):
    return V.symbolic(c, spec) and (c.nin > V.MAX_EXHAUSTIVE or V.exhaustive(c, spec))


def try_window(c, spec, sem_name, W, budget, maxfront, rng, max_and=None, plateau=0.0, gvals=None, gsem=None, max_depth=None):
    users = graph(c)
    fr, wout = window_io(c, users, W)
    w = len(W)
    if sem_name == "local":
        if len(fr) > maxfront:
            return None, "frontier_too_big"
        sem, val = local_values(c, W, fr)
        avail = [val[p] for p in fr]
        outv = [val[s] for s in wout]
    else:
        sem = gsem
        if any(gvals[s] is None for s in list(W) + fr):
            return None, "not_representable"
        avail = [gvals[p] for p in fr]
        outv = [gvals[s] for s in wout]
    needed = sorted(set(x for x in outv if x not in avail))
    res = solve(sem, avail, needed, w - 1, budget, max_and=max_and, seed=rng.randrange(1 << 30))
    tag = "unknown" if res == "unknown" else "unsat" if res is None else "sat"
    if isinstance(res, list):
        new = _build(c, W, fr, wout, res, sem, avail, outv)
        if new is not None and len(new.gates) < len(c.gates) and (max_depth is None or new.depth() <= max_depth) and full_check(new, spec):
            return new, "improved"
        tag = "bad_splice"
    if plateau and rng.random() < plateau and HAVE_PYSAT and tag in ("unsat", "unknown"):
        orig = _window_prog(c, W, fr)
        r2 = sat_window(sem, avail, needed, w, budget, max_and=max_and, block=orig, seed=rng.randrange(1 << 30))
        if isinstance(r2, list):
            new = _build(c, W, fr, wout, r2, sem, avail, outv)
            if new is not None and len(new.gates) <= len(c.gates) and (max_depth is None or new.depth() <= max_depth) and full_check(new, spec):
                return new, tag + "+moved"
    return None, tag


def _window_prog(c, W, fr):
    n = c.nin
    idx = {p: k for k, p in enumerate(fr)}
    prog = []
    for s in sorted(W):
        op, x, y = c.gates[s - n]
        a, b = sorted((idx[x], idx[y]))
        idx[s] = len(fr) + len(prog)
        prog.append((op, a, b))
    return prog


def _build(c, W, fr, wout, prog, sem, avail, outv):
    vals = list(avail)
    for op, a, b in prog:
        r = sem.AND(vals[a], vals[b]) if op == "AND" else vals[a] ^ vals[b]
        if r is None:
            return None
        vals.append(r)
    where = {}
    for k, x in enumerate(vals):
        where.setdefault(x, k)
    try:
        ov = [where[x] for x in outv]
    except KeyError:
        return None
    return splice(c, W, fr, wout, prog, ov, vals)


def parse_spec(s, c):
    if s == "poly":
        return ("poly",)
    return ("field", int(s, 0))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("circuit")
    ap.add_argument("--spec", required=True, help="poly or a field polynomial like 0x11B")
    ap.add_argument("--sem", default="anf2", choices=["local", "anf2", "global"])
    ap.add_argument("--wmin", type=int, default=4)
    ap.add_argument("--wmax", type=int, default=9)
    ap.add_argument("--maxfront", type=int, default=10)
    ap.add_argument("--budget", type=float, default=5.0, help="seconds per window")
    ap.add_argument("--total", type=float, default=600.0, help="seconds for the whole run")
    ap.add_argument("--plateau", type=float, default=0.0)
    ap.add_argument("--max-depth", type=int, default=None, help="reject any splice whose circuit depth exceeds this")
    ap.add_argument("--max-and", type=int, default=None)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--out", required=True)
    ap.add_argument("--hits", default=None)
    ap.add_argument("--solver", default=SOLVER, help="a pysat solver with interrupt support (glucose4, maplechrono, ...)")
    a = ap.parse_args()
    globals()["SOLVER"] = a.solver
    c = load(a.circuit)
    spec = parse_spec(a.spec, c)
    assert full_check(c, spec), "input circuit fails verification"
    assert a.max_depth is None or c.depth() <= a.max_depth, "input circuit already exceeds --max-depth"
    start_size = len(c.gates)
    rng = random.Random(a.seed)
    stats = {}
    t0 = time.time()
    tried = 0
    log = []
    gsem = gvals = None
    while time.time() - t0 < a.total:
        if a.sem != "local" and gvals is None:
            gsem = ANF2(c.nin) if a.sem == "anf2" else TT(c.nin)
            gvals = global_values(c, gsem)
        users = graph(c)
        n = c.nin
        w = rng.randint(a.wmin, a.wmax)
        seed_sig = n + rng.randrange(len(c.gates))
        W = pick_window(c, users, seed_sig, w, rng)
        if W is None or len(W) < max(2, a.wmin):
            stats["skip"] = stats.get("skip", 0) + 1
            continue
        tried += 1
        new, tag = try_window(c, spec, a.sem, W, a.budget, a.maxfront, rng, a.max_and, a.plateau, gvals, gsem, a.max_depth)
        stats[tag] = stats.get(tag, 0) + 1
        if new is not None:
            if len(new.gates) < len(c.gates):
                log.append({"t": round(time.time() - t0, 1), "size": len(new.gates), "w": len(W)})
                print(f"[{time.time() - t0:.0f}s] improved {len(c.gates)} -> {len(new.gates)} (w={len(W)})", flush=True)
            c = new
            gvals = None
            if a.hits and len(c.gates) < start_size:
                os.makedirs(a.hits, exist_ok=True)
                hp = os.path.join(a.hits, f"{os.path.basename(a.circuit)}_{len(c.gates)}_s{a.seed}.json")
                with open(hp, "w") as f:
                    json.dump(dict(c.to_json(), status="VERIFIED_EXHAUSTIVE_AND_SYMBOLIC"), f)
    cnt = c.counts()
    res = dict(circuit=a.circuit, spec=a.spec, sem=a.sem, seed=a.seed, solver="pysat" if HAVE_PYSAT else "enum",
               start=start_size, final=cnt, windows=tried, stats=stats, log=log, budget=a.budget,
               wmin=a.wmin, wmax=a.wmax, secs=round(time.time() - t0, 1), final_circuit=c.to_json())
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(json.dumps({k: v for k, v in res.items() if k not in ("final_circuit", "log")}))


if __name__ == "__main__":
    main()
