"""Gate depth and AND depth of every circuit (ours in circuits/, prior in prior/). Python 3 standard library only.
Depth = most gates on a path; AND depth = most AND gates on a path. Both count only gates that feed an output.
Run from repro/: python3 -I tools/and_depth.py   (output in and_depth_results.txt)
Cross-check: the NIST file names encode AND depth (ad) and gate depth (gd), e.g. aes-sbox-a34-ad4-g125-gd15."""
import json, glob, os
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

def depths(path):
    d = json.load(open(path)); g, a = [0] * 8, [0] * 8
    for op, x, y in d["gates"]:
        g.append(max(g[x], g[y]) + 1); a.append(max(a[x], a[y]) + (op == "AND"))
    return len(d["gates"]), max(g[o] for o in d["outputs"]), max(a[o] for o in d["outputs"])

for folder in ("circuits", "prior"):
    for p in sorted(glob.glob(os.path.join(ROOT, folder, "*.json"))):
        n, gd, ad = depths(p)
        print(f"{folder}/{os.path.basename(p):52} gates={n:3} depth={gd:2} and_depth={ad}")
