"""Self-contained verifier for AES S-box / inverse S-box circuits (Python 3, standard library only).

Circuit JSON: {"gates": [[op, x, y], ...], "outputs": [...]}, op in AND/XOR/XNOR (each costs 1).
Signals 0..7 are the inputs U0..U7, MSB first (signal j = bit 7-j of the input byte); signal 8+i is gate i.
outputs[j] is the signal for bit 7-j of the result (S0 = MSB). NOT is never used; XNOR = 1 xor x xor y.

Tests: (1) exhaustive over all 256 inputs against a table computed here from GF(2^8) inversion + the affine map
(and its inverse table); (2) symbolic: every signal as an exact algebraic normal form, compared with the ANF of
the table; (3) must-fail controls (checker-sanity tests: they show the checker can reject, nothing more).
Usage: python3 -I tools/verify_sbox.py circuits/X.json [--inv]   (default: auto-detect; prints which table matched)
"""
import json, sys

def gmul(a, b):
    r = 0
    while b:
        if b & 1: r ^= a
        a <<= 1
        if a & 0x100: a ^= 0x11B
        b >>= 1
    return r

def tables():
    inv = [0] + [next(y for y in range(1, 256) if gmul(x, y) == 1) for x in range(1, 256)]
    sb = []
    for x in range(256):
        v, s = inv[x], 0
        for i in range(8):
            bit = ((v >> i) ^ (v >> ((i + 4) % 8)) ^ (v >> ((i + 5) % 8)) ^ (v >> ((i + 6) % 8))
                   ^ (v >> ((i + 7) % 8)) ^ (0x63 >> i)) & 1
            s |= bit << i
        sb.append(s)
    assert sb[0x00] == 0x63 and sb[0x01] == 0x7C and sb[0x53] == 0xED   # FIPS-197 spot values
    isb = [0] * 256
    for x in range(256): isb[sb[x]] = x
    assert isb[0x63] == 0x00 and isb[0x00] == 0x52
    return sb, isb

def eval_all(gates, outs):
    """Bit-sliced: signal value = 256-bit int, bit x = value on input byte x."""
    M = (1 << 256) - 1
    sig = []
    for j in range(8):
        v = 0
        for x in range(256):
            if (x >> (7 - j)) & 1: v |= 1 << x
        sig.append(v)
    for op, a, b in gates:
        sig.append(sig[a] & sig[b] if op == "AND" else sig[a] ^ sig[b] if op == "XOR" else M ^ sig[a] ^ sig[b])
    res = [0] * 256
    for j, o in enumerate(outs):
        for x in range(256):
            if (sig[o] >> x) & 1: res[x] |= 1 << (7 - j)
    return res

def anf_mul(p, q):
    r = set()
    for m1 in p:
        for m2 in q:
            r ^= {m1 | m2}
    return frozenset(r)

def eval_anf(gates, outs):
    """Exact ANF: a polynomial is a frozenset of monomials, a monomial is an 8-bit mask over U0..U7."""
    sig = [frozenset({1 << j}) for j in range(8)]
    one = frozenset({0})
    for op, a, b in gates:
        if op == "AND": sig.append(anf_mul(sig[a], sig[b]))
        elif op == "XOR": sig.append(sig[a] ^ sig[b])
        else: sig.append(sig[a] ^ sig[b] ^ one)
    return [sig[o] for o in outs]

def table_anf(tab):
    """ANF of output bit 7-j (j = 0..7) of a table, by the moebius transform on truth tables."""
    res = []
    for j in range(8):
        f = [(tab[x] >> (7 - j)) & 1 for x in range(256)]   # f indexed by byte x
        for k in range(8):
            for x in range(256):
                if x & (1 << k): f[x] ^= f[x ^ (1 << k)]
        # coefficient of the monomial over byte-bits mask x; convert byte bit b to variable U(7-b)
        mons = set()
        for x in range(256):
            if f[x]:
                m = 0
                for b in range(8):
                    if (x >> b) & 1: m |= 1 << (7 - b)
                mons.add(m)
        res.append(frozenset(mons))
    return res

def counts(gates):
    c = {"AND": 0, "XOR": 0, "XNOR": 0}
    d = [0] * 8
    for op, a, b in gates:
        c[op] += 1
        d.append(1 + max(d[a], d[b]))
    return c, d

def depth(gates, outs):
    return max(counts(gates)[1][o] for o in outs)

def wellformed(gates, outs):
    for i, (op, a, b) in enumerate(gates):
        if op not in ("AND", "XOR", "XNOR") or not (0 <= a < 8 + i and 0 <= b < 8 + i): return False
    return len(outs) == 8 and all(0 <= o < 8 + len(gates) for o in outs)

def check(gates, outs, tab):
    return wellformed(gates, outs) and eval_all(gates, outs) == tab and eval_anf(gates, outs) == table_anf(tab)

def controls(gates, outs, tab):
    """Mutants that must all be rejected. Returns the list of controls that were wrongly accepted."""
    bad, g = [], [list(x) for x in gates]
    def mut(name, gg, oo, tt):
        if check([tuple(x) for x in gg], oo, tt): bad.append(name)
    i = next(k for k, x in enumerate(g) if x[0] == "AND")
    gg = [list(x) for x in g]; gg[i][0] = "XOR"; mut("AND->XOR", gg, outs, tab)
    i = next(k for k, x in enumerate(g) if x[0] == "XOR")
    gg = [list(x) for x in g]; gg[i][0] = "AND"; mut("XOR->AND", gg, outs, tab)
    i = next(k for k, x in enumerate(g) if x[0] == "XOR")
    gg = [list(x) for x in g]; gg[i][0] = "XNOR"; mut("XOR->XNOR", gg, outs, tab)
    gg = [list(x) for x in g]; gg[len(g) // 2][1] = (gg[len(g) // 2][1] + 1) % (8 + len(g) // 2); mut("rewire", gg, outs, tab)
    oo = list(outs); oo[0], oo[1] = oo[1], oo[0]; mut("swap outputs", g, oo, tab)
    gg = [[o, (7 - a) if a < 8 else a, (7 - b) if b < 8 else b] for o, a, b in g]; mut("reverse input order", gg, outs, tab)
    tb = list(tab); tb[0x53] ^= 1; mut("wrong table entry", g, outs, tb)
    return bad

def main():
    path = sys.argv[1]; want = "--inv" in sys.argv
    d = json.load(open(path)); gates = [tuple(x) for x in d["gates"]]; outs = d["outputs"]
    sb, isb = tables()
    which = "sbox" if check(gates, outs, sb) else "invsbox" if check(gates, outs, isb) else None
    if "--inv" in sys.argv: ok = which == "invsbox"
    elif "--fwd" in sys.argv: ok = which == "sbox"
    else: ok = which is not None
    tab = sb if which == "sbox" else isb
    c, _ = counts(gates)
    badc = controls(gates, outs, tab) if which else ["n/a"]
    print(f"{path}: matches={which} gates={len(gates)} AND={c['AND']} XOR={c['XOR']} XNOR={c['XNOR']} "
          f"depth={depth(gates, outs)} exhaustive+symbolic={'PASS' if which else 'FAIL'} "
          f"controls_wrongly_accepted={badc} {'OK' if ok and not badc else 'FAIL'}")
    sys.exit(0 if ok and not badc else 1)

if __name__ == "__main__":
    main()
