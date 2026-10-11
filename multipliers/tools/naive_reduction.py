"""XOR cost of naive reduction of a (2m-1)-coefficient carry-free product modulo a field polynomial P.
Fold c_k (k = 2m-2 .. m) into c_{k-m+e} for every non-leading term x^e of P, one XOR per fold.
A fold into a coefficient >= m is itself folded later (cascade), so it is counted when that coefficient is processed.
The result is checked against direct polynomial reduction (set of original product coefficients per output).
usage: python3 -I naive_reduction.py HEXPOLY [M(m)]"""
import sys
def naive(P):
    m = P.bit_length() - 1
    terms = [e for e in range(m) if P >> e & 1]
    c = [{i} for i in range(2 * m - 1)]          # each coefficient = set of original product coefficients (XOR of them)
    xors = 0
    for k in range(2 * m - 2, m - 1, -1):
        for e in terms:
            c[k - m + e] ^= c[k]; xors += 1
    # direct reduction for the check
    ref = []
    for j in range(m):
        s = set()
        for i in range(2 * m - 1):
            r = 1 << i                          # x^i mod P
            while r.bit_length() > m:
                r ^= P << (r.bit_length() - 1 - m)
            if r >> j & 1: s ^= {i}
        ref.append(s)
    assert c[:m] == ref
    return m, xors
if __name__ == "__main__":
    P = int(sys.argv[1], 16); m, x = naive(P)
    print("m=%d poly=%#x naive reduction XORs=%d" % (m, P, x), end="")
    if len(sys.argv) > 2: print("  M(m)=%s  baseline=%d" % (sys.argv[2], int(sys.argv[2]) + x), end="")
    print()
