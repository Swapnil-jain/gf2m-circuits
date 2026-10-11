"""Gate-function overlap between circuits (Python 3 standard library only).
Each gate is reduced to its 256-bit truth table (bit x = value on input byte x), up to complement (an XNOR and an XOR
that differ by a constant count as the same function). overlap(A, B) = number of gates of A whose function occurs
among the gates of B (inputs are not counted as gates of B). It is not symmetric, and it does not prove descent: it
measures shared intermediate functions. Run from repro/: python3 -I tools/overlap.py
Reads circuits/*.json (ours) and prior/*.json (prior work, produced by tools/prior_circuits.py)."""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, "..")
M = (1 << 256) - 1

def functions(path):
    d = json.load(open(path)); sig = []
    for j in range(8):
        v = 0
        for x in range(256):
            if (x >> (7 - j)) & 1: v |= 1 << x
        sig.append(v)
    out = []
    for op, a, b in d["gates"]:
        sig.append(sig[a] & sig[b] if op == "AND" else sig[a] ^ sig[b] if op == "XOR" else M ^ sig[a] ^ sig[b])
        out.append(min(sig[-1], M ^ sig[-1]))
    return out

def overlap(fa, fb):
    sb = set(fb)
    return sum(1 for f in fa if f in sb)

def load(name, folder): return functions(os.path.join(ROOT, folder, name + ".json"))

OURS = ["sbox121_d16", "sbox116_d17", "sbox113_d18", "sbox112_d18", "sbox112_d20", "sbox111_d21", "sbox106_d24",
        "sbox110_d38", "sbox106_d34"]
REFS = [("NIST a32", "aes-sbox-a32-ad5-g110-gd22-xx78-3"), ("NIST a34", "aes-sbox-a34-ad4-g110-gd22-xx76-3"),
        ("CMT 125", "AESDEPTH16SIZE125"), ("NIST 125", "aes-sbox-a34-ad4-g125-gd15-xx91-4"), ("BP 113", "SLP_AES_113"),
        ("our 106/34", None)]

BASE = [("NIST a32", "aes-sbox-a32-ad5-g110-gd22-xx78-3", "prior"), ("NIST a34", "aes-sbox-a34-ad4-g110-gd22-xx76-3", "prior"),
        ("NIST 125", "aes-sbox-a34-ad4-g125-gd15-xx91-4", "prior"), ("CMT 125", "AESDEPTH16SIZE125", "prior"),
        ("BP 113", "SLP_AES_113", "prior"), ("our 110/38", "sbox110_d38", "circuits")]

def baseline():
    """Pairwise overlaps among the prior circuits and our 110/38: the background level for circuits built in the same representation."""
    fs = [(lab, load(n, d)) for lab, n, d in BASE]
    print("\nbaseline: pairwise overlaps among prior circuits and our 110/38 (row circuit's gates found in column circuit)")
    print(f"{'circuit':14}" + "".join(f"{lab:>16}" for lab, _ in fs))
    lo, hi = 100, 0
    for la, fa in fs:
        cells = []
        for lb, fb in fs:
            if la == lb: cells.append("-"); continue
            p = 100 * overlap(fa, fb) / len(fa); lo, hi = min(lo, p), max(hi, p)
            cells.append(f"{overlap(fa, fb)}/{len(fa)} ({p:.0f}%)")
        print(f"{la:14}" + "".join(f"{c:>16}" for c in cells))
    print(f"off-diagonal range: {lo:.0f}% to {hi:.0f}%")

INV_OURS = ["invsbox109_d30", "invsbox109_d31"]
INV_REFS = [("NIST inv 112", "aes-invsbox-a32-ad5-g112-gd26-xx80-9", "prior"), ("CMT Sinv 121", "Sinv", "prior"),
            ("inv 109/30", "invsbox109_d30", "circuits"), ("inv 109/31", "invsbox109_d31", "circuits")]

def inverse():
    """Inverse S-box circuits (ours and prior). The baseline for the inverse is NIST 112 against CMT 121, the two prior inverse circuits."""
    refs = [(lab, load(n, d)) for lab, n, d in INV_REFS]
    print("\ninverse S-box: gates of the row circuit whose function occurs in the column circuit")
    print(f"{'circuit':16}" + "".join(f"{lab:>16}" for lab, _ in refs))
    rows = [(o, load(o, "circuits")) for o in INV_OURS] + [(lab, f) for lab, f in refs[:2]]
    for lab, fo in rows:
        cells = ["-" if lab == rl or lab == n_ else f"{overlap(fo, f)}/{len(fo)} ({100 * overlap(fo, f) / len(fo):.0f}%)"
                 for (rl, f), n_ in zip(refs, [None] * len(refs))]
        print(f"{lab:16}" + "".join(f"{c:>16}" for c in cells))

def main():
    refs = [(lab, load(n, "prior") if n else load("sbox106_d34", "circuits")) for lab, n in REFS]
    print("gate-function overlap: gates of the row circuit whose function occurs in the column circuit")
    print(f"{'circuit':14}" + "".join(f"{lab:>16}" for lab, _ in refs))
    for o in OURS:
        fo = load(o, "circuits")
        cells = [f"{overlap(fo, f)}/{len(fo)} ({100 * overlap(fo, f) / len(fo):.0f}%)" for _, f in refs]
        print(f"{o:14}" + "".join(f"{c:>16}" for c in cells))
    print("\nsanity: a circuit against itself must be 100%:")
    for lab, f in refs: print(f"  {lab}: {overlap(f, f)}/{len(f)}")
    baseline()
    inverse()

if __name__ == "__main__":
    main()
