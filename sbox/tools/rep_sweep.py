"""S2: build the Boyar-Peralta-shaped AES S-box in ANY representation and score it.

Representation (basis-free, numeric):
  a_k = Tr_{256/16}(theta_k * A), k = 0, 1   (theta0, theta1 GF(16)-independent; every GF(16)-basis of GF(256) is one)
  top forms q_{i,k} = Tr_{16/2}(lambda_i * a_k), lambda in a symmetric rank-9 set (lambda_sets.py)
  X = N(A) = A^17 in GF(16); inverter input bits Tr(mu_j * N); A^-1 = N^-1 * (a0 b0^16 + a1 b1^16)
  mul1:   P_i = q_{i,0} q_{i,1};  X_j = sum Gamma_ji P_i + l_j(U) + c_j      (Gamma, l, c solved numerically)
  inverter: the 113's own GF(16) inverter (t25..t45), re-targeted by (t, g): fed Z = (t N)^(2^g), it returns
            Tr(eta_i Z^-1) = Tr(lambda_i N^-1) with lambda_i = eta_i^(2^-g) / t, so Lambda = {eta^(2^-g)/t}
  bottom: z_{i,k} = o_i * q_{i,k};  S_b = sum M_b z + const                    (M solved numerically)
Linear layers are synthesised with tools/linear_opt.py heuristics; constants are fixed with XNOR flips (GF(2) solve).
Every circuit is verified on all 256 inputs against the AES table before it is scored or written.

usage: python3 rep_sweep.py calib RESTARTS               rebuild the 113's own representation (control)
       python3 rep_sweep.py sample N RESTARTS SEED OUTDIR   N random representations; writes any circuit <= 113
       python3 rep_sweep.py all SHARD NSHARD RESTARTS OUTDIR every (theta0, theta1, t, g) class, sharded (box)"""
import json, os, random, re, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "tools"))
sys.path.insert(0, HERE)
import sbox
import linear_opt as LO
from bp_class import g, gpow, ginv, trace_form

FULL = sbox.FULL
CMT113 = os.path.join(HERE, "..", "..", "circuits", "peralta_cmt", "SLP_AES_113.txt")
SUB = [x for x in range(256) if gpow(x, 16) == x]          # GF(16) inside the AES field


def tr16(y):                                                 # Tr_{16/2} for y in GF(16)
    return y ^ g(y, y) ^ gpow(y, 4) ^ gpow(y, 8)


def tr256_16(y):
    return y ^ gpow(y, 16)


def frob(y, e):                                              # y^(2^e), e may be negative (GF(16): mod 4)
    return gpow(y, 1 << (e % 4))


def tt(f):
    return sum((f(x) & 1) << x for x in range(256))


NORM = [gpow(x, 17) for x in range(256)]
NINV = [ginv(n) if n else 0 for n in NORM]
ONE_TT = FULL


# ---------- the 113's inverter, as a named sub-circuit ----------
def parse_named(path):
    rows = []
    for line in open(path):
        m = re.match(r"^\s*(\w+)\s*=\s*(\w+)\s*([+x#])\s*(\w+)\s*$", line)
        if m:
            rows.append(m.groups())
    return rows


def bp_inverter():
    rows = parse_named(CMT113)
    names = [r[0] for r in rows]
    i0, i1 = names.index("t25"), names.index("t45")
    inv = rows[i0:i1 + 1]
    ins = ["t21", "t22", "t23", "t24"]
    outs = ["t29", "t33", "t37", "t40", "t41", "t42", "t43", "t44", "t45"]
    c = sbox.parse(CMT113)
    vals = c.tts()
    env = {f"U{i}": i for i in range(8)}
    k = 8
    for d, a, op, b in rows:
        env[d] = k
        k += 1
    inT = [vals[env[n]] for n in ins]
    outT = [vals[env[n]] for n in outs]
    rho = []
    for t_ in inT:
        r = [p for p in SUB if p and tt(lambda x, p=p: tr16(g(p, NORM[x]))) == t_]
        assert len(r) == 1, "inverter input is not Tr(rho N)"
        rho.append(r[0])
    eta = []
    for t_ in outT:
        r = [p for p in SUB if p and tt(lambda x, p=p: tr16(g(p, NINV[x]))) == t_]
        assert len(r) == 1, "inverter output is not Tr(eta N^-1)"
        eta.append(r[0])
    return inv, ins, outs, rho, eta


INV, INV_IN, INV_OUT, RHO, ETA = bp_inverter()
OPM = {"+": "XOR", "x": "AND", "#": "XNOR"}


# ---------- GF(2) solve on truth tables ----------
def solve(basis, target):
    """express target as XOR of a subset of basis truth tables; returns index set or None"""
    piv = []                                                 # (vector, combo)
    for i, b in enumerate(basis):
        v, cmb = b, 1 << i
        for pv, pc in piv:
            if v ^ pv < v:
                v, cmb = v ^ pv, cmb ^ pc
        if v:
            piv.append((v, cmb))
            piv.sort(key=lambda t: -t[0])
    v, cmb = target, 0
    for pv, pc in piv:
        if v ^ pv < v:
            v, cmb = v ^ pv, cmb ^ pc
    return None if v else cmb


# ---------- linear layer with constants ----------
def linear_layer(gates, cols, rows, consts, restarts, seed):
    """cols: signal ids; rows: masks over cols; consts: 0/1 per row. Appends gates, returns output signal per row."""
    best = LO.run_heuristics(len(cols), rows, restarts, seed)
    prog, where = min(best.values(), key=lambda pw: len(pw[0]))
    n = len(cols)
    # constant of node v after flipping the gate set F: parity of paths from flipped gates. Linear in F.
    reach = [0] * (n + len(prog))                          # reach[v] = bitmask over gates: odd #paths g -> v
    for k, (a, b) in enumerate(prog):
        reach[n + k] = reach[a] ^ reach[b] ^ (1 << k)
    want = [(reach[w], cst) for w, cst in zip(where, consts)]
    sol = solve_masks(want, len(prog))
    if sol is None:
        return None, None
    loc = list(cols)
    for k, (a, b) in enumerate(prog):
        gates.append(("XNOR" if sol >> k & 1 else "XOR", loc[a], loc[b]))
        loc.append(7 + len(gates))
    return [loc[w] for w in where], len(prog)


def solve_masks(eqs, nv):
    """find F (bitmask over nv vars) with parity(F & m) == c for every (m, c)"""
    piv = []
    for m, c in eqs:
        for pm, pc in piv:
            if m ^ pm < m:
                m, c = m ^ pm, c ^ pc
        if m:
            piv.append((m, c))
            piv.sort(key=lambda t: -t[0])
        elif c:
            return None
    F = 0
    for m, c in sorted(piv, key=lambda t: t[0]):              # back-substitute, low pivots first
        top = m.bit_length() - 1
        if bin(F & m).count("1") % 2 != c:
            F ^= 1 << top
    return F if all(bin(F & m).count("1") % 2 == c for m, c in eqs) else None


# ---------- one representation ----------
def build(theta0, theta1, t, gexp, restarts=20, seed=0, eps=0):
    """eps: 18-bit polarity mask, bit 2i+k complements top form q_{i,k} (S2). Flipped products leak o_i terms into
    the bottom, so the bottom may also read the inverter outputs."""
    lam = [g(frob(e, -gexp), ginv(t)) for e in ETA]
    mu = [g(frob(r, -gexp), t) for r in RHO]
    a = [[tr256_16(g(th, x)) for x in range(256)] for th in (theta0, theta1)]
    if any(v not in SUB for v in a[0] + a[1]):
        return None
    q = [[tt(lambda x, k=k, l=l: tr16(g(l, a[k][x]))) for k in (0, 1)] for l in lam]
    qmask = [[trace_form(g(l, th)) for th in (theta0, theta1)] for l in lam]
    X = [tt(lambda x, m=m: tr16(g(m, NORM[x]))) for m in mu]
    qf = [[q[i][k] ^ (FULL if eps >> (2 * i + k) & 1 else 0) for k in (0, 1)] for i in range(9)]
    P = [qf[i][0] & qf[i][1] for i in range(9)]
    lin = list(sbox.VAR) + [ONE_TT]
    gam, ell, cst = [], [], []
    for j in range(4):
        s = solve(P + lin, X[j])
        if s is None:
            return None
        gam.append(s & 511)
        ell.append(sum(1 << u for u in range(8) if s >> (9 + u) & 1))
        cst.append(s >> 17 & 1)
    gates = []
    # top: 18 q forms (+ distinct nonzero ell forms not already present)
    forms, fpol = [], {}
    for i in range(9):
        for k in (0, 1):
            pol = eps >> (2 * i + k) & 1
            if qmask[i][k] in fpol and fpol[qmask[i][k]] != pol:
                return None
            fpol[qmask[i][k]] = pol
            if qmask[i][k] not in forms:
                forms.append(qmask[i][k])
    extra = [e for e in dict.fromkeys(ell) if e and e not in forms]
    rows = forms + extra
    tsig, ntop = linear_layer(gates, list(range(8)), rows, [fpol.get(r, 0) for r in rows], restarts, seed)
    if tsig is None:
        return None
    fsig = dict(zip(rows, tsig))
    Psig = []
    for i in range(9):
        gates.append(("AND", fsig[qmask[i][0]], fsig[qmask[i][1]]))
        Psig.append(7 + len(gates))
    # mul-sum: columns = 9 products + distinct nonzero ell forms
    ecol = [e for e in dict.fromkeys(ell) if e]
    cst = [c_ ^ (fpol.get(ell[j], 0) if ell[j] else 0) for j, c_ in enumerate(cst)]
    cols = Psig + [fsig[e] for e in ecol]
    mrows = [gam[j] | (sum(1 << (9 + ecol.index(ell[j])) for _ in [0]) if ell[j] else 0) for j in range(4)]
    xsig, nms = linear_layer(gates, cols, mrows, cst, restarts, seed)
    if xsig is None:
        return None
    env = dict(zip(INV_IN, xsig))
    for d, x_, op, y_ in INV:
        gates.append((OPM[op], env[x_], env[y_]))
        env[d] = 7 + len(gates)
    osig = [env[n] for n in INV_OUT]
    zsig, ztt = [], []
    for i in range(9):
        for k in (0, 1):
            gates.append(("AND", osig[i], fsig[qmask[i][k]]))
            zsig.append(7 + len(gates))
    c0 = sbox.C(gates, [0] * 8)
    vals = c0.tts()
    ztt = [vals[s] for s in zsig]
    ott = [vals[s_] for s_ in osig]
    bcols = zsig + (osig if eps else [])
    bbasis = ztt + (ott if eps else [])
    nb = len(bcols)
    brows, bconst = [], []
    for b in range(8):
        s = solve(bbasis + [ONE_TT], sbox.TARGET[b])
        if s is None:
            return None
        brows.append(s & ((1 << nb) - 1))
        bconst.append(s >> nb & 1)
    used = sorted({k for r in brows for k in range(nb) if r >> k & 1})
    brows = [sum(1 << used.index(k) for k in range(nb) if r >> k & 1) for r in brows]
    osigs, nbot = linear_layer(gates, [bcols[k] for k in used], brows, bconst, restarts, seed)
    if osigs is None:
        return None
    c = sbox.C(gates, osigs).prune()
    if not c.ok():
        raise AssertionError("built circuit fails the AES table: generator bug")
    parts = {"top": ntop, "top_forms": len(rows), "mulsum": nms, "bottom": nbot}
    return c, parts


def random_rep(rng):
    while True:
        th0, th1 = rng.randrange(1, 256), rng.randrange(1, 256)
        if not any(g(s, th0) == th1 for s in SUB):
            return th0, th1, rng.choice([s for s in SUB if s]), rng.randrange(4)


def calib_params():
    """find (theta0, theta1, t, g) reproducing the 113's own 18 forms"""
    from dissect import dissect
    from quad_rank import form_of
    from bp_class import FORM2W
    c = sbox.load(CMT113)
    cnt, na, nx, lvl, blk = dissect(c)
    v = c.tts()
    forms = {form_of(v[x_]) for op, x_, y_ in c.gates if op == "AND" for x_ in (x_, y_) if lvl[x_] == 0}
    W = {FORM2W[f] for f in forms}
    for t in SUB[1:]:
        for ge in range(4):
            lam = [g(frob(e, -ge), ginv(t)) for e in ETA]
            ths = [th for th in range(1, 256) if {g(l, th) for l in lam} <= W]
            for th0 in ths:
                for th1 in ths:
                    if th1 != th0 and not any(g(s, th0) == th1 for s in SUB):
                        if {g(l, th) for l in lam for th in (th0, th1)} == W:
                            return th0, th1, t, ge
    return None


def main():
    cmd = sys.argv[1]
    if cmd == "calib":
        R = int(sys.argv[2])
        p = calib_params()
        print("113 representation:", p)
        t0 = time.time()
        r = build(*p, restarts=R)
        print("rebuilt:", r[0].counts(), r[1], f"{time.time()-t0:.1f}s")
    elif cmd == "sample":
        N, R, seed, outdir = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        os.makedirs(outdir, exist_ok=True)
        rng = random.Random(seed)
        hist, t0, bad = {}, time.time(), 0
        best = None
        for n in range(N):
            p = random_rep(rng)
            r = build(*p, restarts=R, seed=n)
            if r is None:
                bad += 1
                continue
            c, parts = r
            tot = c.counts()["total"]
            hist[tot] = hist.get(tot, 0) + 1
            if best is None or tot < best[0]:
                best = (tot, p, parts)
            if tot <= 113:
                json.dump(c.to_json() | {"rep": p, "parts": parts},
                          open(os.path.join(outdir, f"rep_{tot}_{p[0]}_{p[1]}_{p[2]}_{p[3]}.json"), "w"))
        print(f"sample N={N} R={R} seed={seed}: {time.time()-t0:.0f}s, failed builds {bad}")
        print("  totals histogram:", dict(sorted(hist.items())))
        print("  best:", best)
    elif cmd == "all":
        shard, nshard, R, outdir = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
        os.makedirs(outdir, exist_ok=True)
        # classes: theta0 from GF(256)^* / GF(16)^* (17 cosets, any rep; Lambda scaling covers the rest),
        # theta1 any element outside GF(16)*theta0; t in GF(16)^*, g in 0..3
        reps0 = []
        seen = set()
        for x in range(1, 256):
            if x not in seen:
                reps0.append(x)
                seen |= {g(s, x) for s in SUB if s}
        jobs = [(th0, th1, t, ge) for th0 in reps0 for th1 in range(1, 256)
                if not any(g(s, th0) == th1 for s in SUB) for t in SUB[1:] for ge in range(4)]
        jobs = jobs[shard::nshard]
        log = open(os.path.join(outdir, f"shard_{shard}.tsv"), "w")
        for n, p in enumerate(jobs):
            r = build(*p, restarts=R, seed=n)
            if r is None:
                continue
            c, parts = r
            tot = c.counts()["total"]
            log.write(f"{tot}\t{p}\t{json.dumps(parts)}\n")
            log.flush()
            if tot <= 113:
                json.dump(c.to_json() | {"rep": p, "parts": parts},
                          open(os.path.join(outdir, f"rep_{tot}_{p[0]}_{p[1]}_{p[2]}_{p[3]}.json"), "w"))


if __name__ == "__main__":
    main()
