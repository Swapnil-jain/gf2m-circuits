"""Verify a circuit computes GF(2)[x] n x n multiplication or GF(2^m) multiplication.

Three independent checks:
  exhaustive  bitsliced evaluation over ALL 2^(na+nb) input pairs (the low 16 input bits are packed into one
              2^16-bit Python int per signal, the remaining bits are looped over). The reference outputs are
              computed by a separate bitsliced formula (sum of a_i b_j, then the reduction matrix), and that
              formula is itself spot-checked against a scalar carry-less multiply (clmul + mod).
  symbolic    every signal as its exact GF(2) algebraic normal form (a set of monomials); each output must
              equal the exact bilinear form sum_{i+j=k} a_i b_j (then reduced mod P for a field).
  controls    must-fail mutations: flip a gate type, rewire one operand, swap two input labels, wrong polynomial.

Specs:  --poly                      GF(2)[x]: na x nb -> na+nb-1 coefficients
        --field 0x11B               GF(2^m) polynomial basis mod P (bit m of P set); na = nb = m
        --field-any                 multiplication in SOME basis of GF(2^m) (tower / custom bases): the circuit
                                    must be bilinear, commutative, associative, have an identity, and be generated
                                    by an element whose minimal polynomial is irreducible of degree m
                                    (so the algebra is F_2[x]/(f), a field). Exact by bilinearity.

CLI:  python3 verify.py FILE (--poly | --field P | --field-any) [--controls K] [--no-exhaustive]
      python3 verify.py --baselines OUT.md      re-verify every CMT and bbe circuit in circuits/
"""
import argparse
import os
import random
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from circuit import load  # noqa: E402

CHUNK = 16          # input bits packed per bitsliced word (2^16-bit ints)
MAX_EXHAUSTIVE = 30  # inputs; above this only the symbolic check runs


# ---------------- GF(2)[x] scalar helpers ----------------

def clmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        b >>= 1
    return r


def pmod(a, p):
    dp = p.bit_length() - 1
    while a.bit_length() - 1 >= dp:
        a ^= p << (a.bit_length() - 1 - dp)
    return a


def pdeg(a):
    return a.bit_length() - 1


def pgcd(a, b):
    while b:
        a, b = b, pmod(a, b)
    return a


def mulmod(a, b, p):
    return pmod(clmul(a, b), p)


def is_irreducible(f):
    m = pdeg(f)
    if m < 1:
        return False
    x = 2

    def frob_pow(k):           # x^(2^k) mod f
        r = x
        for _ in range(k):
            r = mulmod(r, r, f)
        return r
    if frob_pow(m) != pmod(x, f):
        return False
    for q in {q for q in range(2, m + 1) if m % q == 0 and all(q % r for r in range(2, q))}:
        if pgcd(f, frob_pow(m // q) ^ pmod(x, f)) != 1:
            return False
    return True


def other_irreducible(m, avoid):
    for f in range((1 << m) | 1, 1 << (m + 1), 2):
        if f != avoid and is_irreducible(f):
            return f
    return None


def reduction_rows(m, p, nprod):
    """red[t] = bitmask over product coefficients k (k < nprod) with bit t of x^k mod p."""
    red = [0] * m
    for k in range(nprod):
        r = pmod(1 << k, p)
        for t in range(m):
            if r >> t & 1:
                red[t] |= 1 << k
    return red


# ---------------- exhaustive bitsliced ----------------

def _var_masks(nlow):
    W = 1 << nlow
    full = (1 << W) - 1
    masks = []
    for v in range(nlow):
        blk = (1 << (1 << v)) - 1               # 2^v ones
        pat = 0
        period = 1 << (v + 1)
        for start in range(1 << v, W, period):
            pat |= blk << start
        masks.append(pat)
    return masks, full


def eval_bitsliced(c, inmasks, full):
    n = c.nin
    v = list(inmasks) + [0] * len(c.gates)
    for i, (op, x, y) in enumerate(c.gates):
        if op == "AND":
            v[n + i] = v[x] & v[y]
        elif op == "XOR":
            v[n + i] = v[x] ^ v[y]
        elif op == "XNOR":
            v[n + i] = v[x] ^ v[y] ^ full
        else:
            v[n + i] = v[x] ^ full
    return [v[o] for o in c.outputs]


def reference_bitsliced(na, nb, spec, inmasks):
    A, B = inmasks[:na], inmasks[na:na + nb]
    prod = [0] * (na + nb - 1)
    for i in range(na):
        for j in range(nb):
            prod[i + j] ^= A[i] & B[j]
    if spec[0] == "poly":
        return prod
    m, p = na, spec[1]
    red = reduction_rows(m, p, len(prod))
    out = []
    for t in range(m):
        acc = 0
        for k in range(len(prod)):
            if red[t] >> k & 1:
                acc ^= prod[k]
        out.append(acc)
    return out


def exhaustive(c, spec):
    """True iff the circuit equals the spec on all 2^(na+nb) inputs."""
    n = c.nin
    nlow = min(n, CHUNK)
    low, full = _var_masks(nlow)
    for hi in range(1 << (n - nlow)):
        ins = low + [full if hi >> (v - nlow) & 1 else 0 for v in range(nlow, n)]
        if eval_bitsliced(c, ins, full) != reference_bitsliced(c.na, c.nb, spec, ins):
            return False
    return True


def spot_check_reference(na, nb, spec, trials=64, seed=7):
    """The bitsliced reference against scalar clmul (+ mod P) on random points: guards the reference code."""
    rng = random.Random(seed)
    n = na + nb
    for _ in range(trials):
        a, b = rng.getrandbits(na), rng.getrandbits(nb)
        bits = [(a >> i) & 1 for i in range(na)] + [(b >> j) & 1 for j in range(nb)]
        ref = reference_bitsliced(na, nb, spec, bits)
        want = clmul(a, b) if spec[0] == "poly" else pmod(clmul(a, b), spec[1])
        if ref != [(want >> k) & 1 for k in range(len(ref))]:
            return False
    del n
    return True


# ---------------- symbolic (ANF) ----------------

MONO_CAP = 500000


def anf_signals(c, free=True):
    """ANF of every signal: a set of monomials, a monomial = int bitmask over the na+nb inputs (0 = constant 1)."""
    n = c.nin
    # free each signal after its last use (outputs are kept), so wide circuits stay small in memory
    last = {}
    for i, (op, x, y) in enumerate(c.gates):
        last[x] = i
        if y is not None:
            last[y] = i
    keep = set(c.outputs)
    v = [frozenset([1 << s]) for s in range(n)]
    one = frozenset([0])
    for i, (op, x, y) in enumerate(c.gates):
        if op == "XOR":
            r = v[x] ^ v[y]
        elif op == "XNOR":
            r = v[x] ^ v[y] ^ one
        elif op == "NOT":
            r = v[x] ^ one
        else:
            acc = set()
            for m1 in v[x]:
                for m2 in v[y]:
                    acc ^= {m1 | m2}
            r = frozenset(acc)
        if len(r) > MONO_CAP:
            raise OverflowError("ANF too large")
        v.append(r)
        for p in (x, y):
            if free and p is not None and last.get(p) == i and p not in keep:
                v[p] = None
    return v


def anf_signals_all(c):
    """ANF of every signal, none freed (window tools need all of them)."""
    return anf_signals(c, free=False)


def target_anf(na, nb, spec):
    prod = [set() for _ in range(na + nb - 1)]
    for i in range(na):
        for j in range(nb):
            prod[i + j].add((1 << i) | (1 << (na + j)))
    if spec[0] == "poly":
        return [frozenset(s) for s in prod]
    red = reduction_rows(na, spec[1], len(prod))
    out = []
    for t in range(na):
        acc = set()
        for k in range(len(prod)):
            if red[t] >> k & 1:
                acc ^= prod[k]
        out.append(frozenset(acc))
    return out


def symbolic(c, spec):
    try:
        v = anf_signals(c)
    except OverflowError:
        return False
    tg = target_anf(c.na, c.nb, spec)
    return len(tg) == len(c.outputs) and all(v[o] == t for o, t in zip(c.outputs, tg))


# ---------------- field in some basis ----------------

def structure_constants(c):
    """For a bilinear circuit: T[i][j] = output bit vector of e_i * e_j. None if some output is not bilinear."""
    na = c.na
    v = anf_signals(c)
    T = [[0] * c.nb for _ in range(na)]
    for t, o in enumerate(c.outputs):
        for mono in v[o]:
            if bin(mono).count("1") != 2 or not (mono & ((1 << na) - 1)) or not (mono >> na):
                return None
            i = (mono & ((1 << na) - 1)).bit_length() - 1
            j = (mono >> na).bit_length() - 1
            T[i][j] ^= 1 << t
    return T


def alg_mul(T, x, y, m):
    r = 0
    for i in range(m):
        if x >> i & 1:
            for j in range(m):
                if y >> j & 1:
                    r ^= T[i][j]
    return r


def solve_gf2(cols_by_eq, rhs, m):
    """Find e (m-bit) with XOR_{i: e_i=1} cols_by_eq[j][i] == rhs[j] for all j (vectors as ints); None if none.
    Each equation j is an m-bit vector identity; flatten to m*m scalar equations."""
    rows = []
    for j in range(len(rhs)):
        for t in range(m):
            coef = 0
            for i in range(m):
                if cols_by_eq[j][i] >> t & 1:
                    coef |= 1 << i
            rows.append((coef, rhs[j] >> t & 1))
    piv = {}
    for coef, b in rows:
        while coef:
            p = coef.bit_length() - 1
            if p not in piv:
                piv[p] = (coef, b)
                break
            pc, pb = piv[p]
            coef ^= pc
            b ^= pb
        else:
            if b:
                return None
    e = 0
    for p in sorted(piv):
        coef, b = piv[p]
        rest = coef & ~(1 << p)
        val = b ^ (bin(rest & e).count("1") & 1)
        if val:
            e |= 1 << p
    return e if e else None


def field_any(c, seed=1):
    """(ok, info). Exact: bilinearity reduces commutativity / associativity / identity to basis elements."""
    m = c.na
    if c.nb != m or len(c.outputs) != m:
        return False, "shape"
    T = structure_constants(c)
    if T is None:
        return False, "not bilinear"
    E = [1 << i for i in range(m)]
    if any(T[i][j] != T[j][i] for i in range(m) for j in range(m)):
        return False, "not commutative"
    for i in range(m):
        for j in range(m):
            for k in range(m):
                if alg_mul(T, T[i][j], E[k], m) != alg_mul(T, E[i], T[j][k], m):
                    return False, "not associative"
    # identity: e * e_j = e_j for every j is linear in e: sum_i e_i T[i][j] = e_j. Solve over GF(2).
    ident = solve_gf2([[T[i][j] for i in range(m)] for j in range(m)], E, m)
    if ident is None:
        return False, "no identity"
    rng = random.Random(seed)
    for _ in range(200):
        th = rng.randrange(1, 1 << m)
        pw = [ident]
        for _ in range(m):
            pw.append(alg_mul(T, pw[-1], th, m))
        # minimal polynomial: first linear dependency among th^0..th^k
        basis = {}          # pivot -> (vector, combination)
        f = None
        for k, vec in enumerate(pw):
            comb = 1 << k
            x = vec
            while x:
                piv = x.bit_length() - 1
                if piv not in basis:
                    break
                bv, bc = basis[piv]
                x ^= bv
                comb ^= bc
            if x == 0:
                f = comb
                break
            basis[x.bit_length() - 1] = (x, comb)
        if f is not None and pdeg(f) == m and is_irreducible(f):
            return True, {"identity": ident, "generator": th, "minpoly": hex(f)}
    return False, "no generator with irreducible minimal polynomial found"


# ---------------- must-fail controls ----------------

def mutants(c, k, seed=3):
    """Yield (label, mutated circuit). Gate flips and rewires on random gates; one input-label swap."""
    rng = random.Random(seed)
    n = c.nin
    G = len(c.gates)
    for i in rng.sample(range(G), min(k, G)):
        op, x, y = c.gates[i]
        d = c.copy()
        d.gates[i] = ({"AND": "XOR", "XOR": "AND", "XNOR": "AND"}.get(op, "XOR"), x, y if y is not None else x)
        yield f"flip gate {i} {op}", d
    for i in rng.sample(range(G), min(k, G)):
        op, x, y = c.gates[i]
        if y is None:
            continue
        choices = [s for s in range(n + i) if s not in (x, y)]
        if not choices:
            continue
        d = c.copy()
        d.gates[i] = (op, x, rng.choice(choices))
        yield f"rewire gate {i}", d
    if c.na >= 2:
        d = c.copy()

        def sw(s):
            return 1 if s == 0 else 0 if s == 1 else s
        d.gates = [(op, sw(x), None if y is None else sw(y)) for op, x, y in d.gates]
        d.outputs = [sw(o) for o in d.outputs]
        yield "swap inputs a0,a1", d


def check(c, spec, do_exhaustive=True):
    """Return dict of results for one circuit against one spec."""
    res = {}
    if spec[0] == "field-any":
        ok, info = field_any(c)
        res["field_any"] = ok
        res["field_info"] = info
        return res
    res["reference_spot"] = spot_check_reference(c.na, c.nb, spec)
    res["symbolic"] = symbolic(c, spec)
    if do_exhaustive and c.nin <= MAX_EXHAUSTIVE:
        res["exhaustive"] = exhaustive(c, spec)
    return res


def passed(res):
    keys = [k for k in ("reference_spot", "symbolic", "exhaustive", "field_any") if k in res]
    return bool(keys) and all(res[k] is True for k in keys)


def controls(c, spec, k=5, do_exhaustive=True):
    """Every mutant must FAIL. Returns (n_mutants, n_failed_as_expected, survivors)."""
    tot = bad = 0
    surv = []
    muts = list(mutants(c, k))
    if spec[0] == "field":
        wrong = other_irreducible(c.na, spec[1])
        if wrong:
            muts.append((f"wrong polynomial {hex(wrong)}", ("spec", ("field", wrong))))
    elif spec[0] == "poly" and len(c.outputs) >= 2:
        d = c.copy()
        d.outputs[0], d.outputs[1] = d.outputs[1], d.outputs[0]
        muts.append(("swap outputs c0,c1", d))
    for label, d in muts:
        tot += 1
        if isinstance(d, tuple) and d[0] == "spec":
            r = check(c, d[1], do_exhaustive)
        else:
            r = check(d, spec, do_exhaustive)
        if spec[0] != "field-any":
            # a mutant must fail EVERY check that ran (each check alone must catch it)
            caught = all(r[k] is False for k in ("symbolic", "exhaustive") if k in r)
        else:
            caught = not r["field_any"]
        if caught:
            bad += 1
        else:
            surv.append(label)
    return tot, bad, surv


def verify_full(c, spec, k=5, do_exhaustive=True):
    t0 = time.time()
    res = check(c, spec, do_exhaustive)
    res["controls"] = controls(c, spec, k, do_exhaustive)
    res["ok"] = passed(res) and res["controls"][1] == res["controls"][0]
    res["secs"] = round(time.time() - t0, 2)
    return res


# ---------------- baselines ----------------

def _baseline_list(root):
    cm = os.path.join(root, "sources", "circuits", "cmt")
    pc = os.path.join(root, "sources", "circuits", "peralta_cmt")
    bb = os.path.join(root, "sources", "circuits", "bernstein_bbe251")
    L = [
        (os.path.join(cm, "slp_630.txt"), ("field", 0x49), "GF(2^6) poly x^6+x^3+1 (CMT 2010)"),
        (os.path.join(cm, "slp_740.txt"), ("field", 0x91), "GF(2^7) poly x^7+x^4+1 (CMT 2010)"),
        (os.path.join(pc, "slp_730.txt"), ("field", 0x89), "GF(2^7) poly x^7+x^3+1 (CMT)"),
        (os.path.join(cm, "slp_84310.txt"), ("field", 0x11B), "GF(2^8) AES poly 0x11B (CMT 2010)"),
        (os.path.join(cm, "GF256mult.s106.d6"), ("field-any",), "GF(2^8) custom tower basis (CMT 2017)"),
        (os.path.join(pc, "multcircuit"), ("field-any",), "GF(2^16) tower basis (CMT inversion page)"),
    ]
    for f in sorted(os.listdir(os.path.join(pc, "binary_pol_mult"))):
        L.append((os.path.join(pc, "binary_pol_mult", f), ("poly",), f"GF(2)[x] CMT binary_pol_mult/{f}"))
    for n in range(1, 65):
        L.append((os.path.join(bb, f"{n}.gz"), ("poly",), f"GF(2)[x] n={n} (Bernstein bbe251)"))
    fp = os.path.join(pc, "BinPolMult_extracted", "BinPolMult")
    if os.path.isdir(fp):
        def nn(f):
            return int(f.split("_")[1])
        for f in sorted((f for f in os.listdir(fp) if f.startswith("s_")), key=nn):
            L.append((os.path.join(fp, f), ("poly",), f"GF(2)[x] n={nn(f)} (Find-Peralta BinPolMult/{f})"))
    return L


def _one(args):
    path, spec, k = args
    c = load(path)
    return c.counts(), verify_full(c, spec, k)


def baselines(out, root, k=3, procs=1):
    jobs = [(p, s, lab) for p, s, lab in _baseline_list(root) if os.path.exists(p)]
    if procs > 1:
        from multiprocessing import Pool
        with Pool(procs) as pool:
            res = pool.map(_one, [(p, s, k) for p, s, lab in jobs], chunksize=1)
    else:
        res = [_one((p, s, k)) for p, s, lab in jobs]
    rows = []
    for (path, spec, label), (cnt, r) in zip(jobs, res):
        rows.append((label, os.path.relpath(path, root), cnt, r))
        print(label, cnt["total"], r["ok"], r.get("secs"), flush=True)
    with open(out, "w") as f:
        f.write("# Baselines: published circuits re-verified by tools/verify.py\n\n")
        f.write(f"Generated {time.strftime('%F %T')} by `python3 tools/verify.py --baselines`. Gates are fan-in 2; "
                "aliases (`h0 = t25`) are free. Columns: exhaustive = all 2^(na+nb) input pairs bitsliced "
                f"(run when na+nb <= {MAX_EXHAUSTIVE}); symbolic = exact ANF equals the bilinear form; field-any = "
                "bilinear, commutative, associative, unital, generated by an element with an irreducible minimal "
                "polynomial of degree m (so a field multiplication in some basis); controls = must-fail mutants "
                "caught / tried (gate flips, operand rewires, input swap, wrong polynomial or swapped outputs).\n\n")
        f.write("| Circuit | File | Total | AND | XOR | Depth | Exhaustive | Symbolic | Field-any | Controls | OK |\n")
        f.write("|---|---|---|---|---|---|---|---|---|---|---|\n")
        for label, p, cnt, r in rows:
            ctl = r["controls"]
            fa = r.get("field_any")
            fa = "-" if fa is None else (f"yes, minpoly {r['field_info']['minpoly']}" if fa else f"NO ({r['field_info']})")
            f.write(f"| {label} | `{p}` | {cnt['total']} | {cnt['AND']} | {cnt['XOR']} | {cnt['depth']} | "
                    f"{r.get('exhaustive', '-')} | {r.get('symbolic', '-')} | {fa} | {ctl[1]}/{ctl[0]} | "
                    f"{'PASS' if r['ok'] else 'FAIL'} |\n")
    return rows


def parse_spec(a):
    if a.poly:
        return ("poly",)
    if a.field_any:
        return ("field-any",)
    if a.field:
        return ("field", int(a.field, 0))
    raise SystemExit("give --poly, --field P or --field-any")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file", nargs="?")
    ap.add_argument("--poly", action="store_true")
    ap.add_argument("--field")
    ap.add_argument("--field-any", action="store_true")
    ap.add_argument("--controls", type=int, default=5)
    ap.add_argument("--no-exhaustive", action="store_true")
    ap.add_argument("--baselines")
    ap.add_argument("--procs", type=int, default=1)
    a = ap.parse_args()
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if a.baselines:
        baselines(a.baselines, root, procs=a.procs)
        return
    c = load(a.file)
    r = verify_full(c, parse_spec(a), a.controls, not a.no_exhaustive)
    print(c.counts())
    print(r)
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
