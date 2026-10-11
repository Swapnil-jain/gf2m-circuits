"""Parse prior-work circuits (NIST .circ.txt and CMT .txt files) with our own code, check them against the
AES S-box / inverse S-box with verify_sbox.py, recount the depth with verify_sbox.depth, and write our JSON form.
The raw files are data only; nothing in them is executed.
Names x0..x7 / y0..y7 are read as U0..U7 / S0..S7 (U0, S0 = most significant bit); a wrong convention would make the
check below fail, so a file is only accepted if it computes the table.
Usage: python3 -I tools/prior_circuits.py   (run from repro/; reads prior/raw/, writes prior/*.json, prints a table)
NIST format: lines `OP out in1 in2` between `begin SLP` and `end SLP`; inputs U0..U7, outputs S0..S7.
CMT format: header (gate count, inputs, outputs), then between `begin` and `end` one gate per line:
`NAME = A + B` (XOR), `NAME = A # B` (XNOR), `NAME = A x B` (AND). Input/output names are taken by name (U0, S0 = MSB).
Names x0..x7 / y0..y7 are read as U0..U7 / S0..S7 (U0, S0 = most significant bit); a wrong convention would make the
check below fail, so a file is only accepted if it computes the table.
Usage: python3 -I tools/prior_circuits.py   (run from repro/; reads prior/raw/, writes prior/*.json, prints a table)
NIST format: lines `OP out in1 in2` between `begin SLP` and `end SLP`; inputs U0..U7, outputs S0..S7.
CMT format: header (gate count, inputs, outputs) then `NAME = A + B` (XOR), `A # B` (XNOR), `A x B` (AND, written `#`
for XNOR and `x`... see parse_cmt) between `begin` and `end`. Input/output names are taken by NAME (U0 = MSB, S0 = MSB)."""
import json, os, re, sys, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("verify_sbox", os.path.join(HERE, "verify_sbox.py"))
V = importlib.util.module_from_spec(spec); spec.loader.exec_module(V)

OPS = {"AND": "AND", "XOR": "XOR", "XNOR": "XNOR", "+": "XOR", "#": "XNOR", "x": "AND", "*": "AND"}

def canon(n):
    """Some NIST files name the inputs x0..x7 and the outputs y0..y7 or W0..W7 instead of U0..U7 and S0..S7."""
    return "U" + n[1:] if re.fullmatch(r"[xU]\d", n) else "S" + n[1:] if re.fullmatch(r"[ySW]\d", n) else n

def build(lines):
    """lines: list of (outname, op, in1, in2) in file order. Returns (gates, outputs) in our JSON form."""
    idx = {f"U{i}": i for i in range(8)}
    gates = []
    for out, op, a, b in lines:
        gates.append([OPS[op], idx[canon(a)], idx[canon(b)]]); idx[canon(out)] = 8 + len(gates) - 1
    return gates, [idx[f"S{i}"] for i in range(8)]

def parse_nist(path):
    L, on = [], False
    for ln in open(path):
        t = ln.split()
        if ln.startswith("begin SLP"): on = True; continue
        if ln.startswith("end SLP"): break
        if on and t and not t[0].startswith("%"): L.append((t[1], t[0], t[2], t[3]))
    return build(L)

def parse_cmt(path):
    L, on = [], False
    for ln in open(path):
        t = ln.split()
        if ln.strip() == "begin": on = True; continue
        if ln.strip() == "end": break
        if on and len(t) == 5 and t[1] == "=": L.append((t[0], t[3], t[2], t[4]))
    return build(L)

FILES = [  # (raw file, parser, label)
    ("aes-sbox-a34-ad4-g125-gd15-xx91-4.circ.txt", parse_nist, "NIST 125 (file name says depth 15)"),
    ("AESDEPTH16SIZE125", parse_cmt, "CMT 125 (page says depth 16)"),
    ("aes-sbox-a32-ad5-g110-gd22-xx78-3.circ.txt", parse_nist, "NIST 110/22, 32 AND (seed a32)"),
    ("aes-sbox-a34-ad4-g110-gd22-xx76-3.circ.txt", parse_nist, "NIST 110/22, 34 AND (seed a34)"),
    ("SLP_AES_113.txt", parse_cmt, "CMT/Calik 113 (page says depth 27)"),
    ("aes-invsbox-a32-ad5-g112-gd26-xx80-9.circ.txt", parse_nist, "NIST inverse 112 (file name says depth 26)"),
    ("Sinv.txt", parse_cmt, "CMT inverse 121 (page says depth 21)"),
]

def main():
    sb, isb = V.tables()
    print(f"{'raw file':50} {'gates':>5} {'AND':>3} {'XOR':>3} {'XNOR':>4} {'depth':>5}  computes  label")
    for fn, parser, label in FILES:
        g, o = parser(os.path.join(HERE, "..", "prior", "raw", fn))
        gt = [tuple(x) for x in g]
        which = "sbox" if V.check(gt, o, sb) else "invsbox" if V.check(gt, o, isb) else "NEITHER"
        c, _ = V.counts(gt)
        name = fn.replace(".circ.txt", "").replace(".txt", "")
        json.dump({"gates": g, "outputs": o}, open(os.path.join(HERE, "..", "prior", name + ".json"), "w"))
        print(f"{fn:50} {len(g):5} {c['AND']:3} {c['XOR']:3} {c['XNOR']:4} {V.depth(gt, o):5}  {which:8}  {label}")

if __name__ == "__main__":
    main()
