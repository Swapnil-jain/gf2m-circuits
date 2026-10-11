"""Readable listing of a circuit JSON: inputs U0..U7 (MSB first), gates T0.., outputs S0..S7 (MSB first).
Usage: python3 -I tools/make_listing.py circuits/X.json > circuits/X.txt   (+ for XOR, x for AND, ~ for XNOR)"""
import json, sys
d = json.load(open(sys.argv[1]))
nm = lambda s: f"U{s}" if s < 8 else f"T{s-8}"
sym = {"XOR": "+", "AND": "x", "XNOR": "~"}
for i, (o, a, b) in enumerate(d["gates"]): print(f"T{i} = {nm(a)} {sym[o]} {nm(b)}")
for j, o in enumerate(d["outputs"]): print(f"S{j} = {nm(o)}")
