# Repro pack: GF(2^m) multiplier circuits

Contents: sources/ (evidence files and third-party circuit data, see sources/README.md), circuits/ (.slp), lean/ (.lean + .out), tools/ (verify.py, circuit.py are all that is needed to check; depth.py,
window_sat.py, linear_opt.py are the search/post-processing tools, shown for reference), commitment/ (SHA256SUMS, ROOT.txt, GIST.txt).
Needs Python 3 only (no third-party packages) to run verify.py. Run from this directory.

## 1. Check the commitment
    shasum -a 256 commitment/SHA256SUMS      # must equal commitment/ROOT.txt (7139c329...)
    cd circuits && shasum -a 256 -c ../commitment/SHA256SUMS 2>&1 | grep -v 'json'   # slp lines OK; sbox .json entries belong to another paper and are absent here
Weak public timestamp (editable GitHub gist, GitHub-dated): https://gist.github.com/Swapnil-jain/6750e3f460658bc51c9a5f376c93af72
First-round file: `shasum -a 256 commitment/SHA256SUMS.v1` must equal f9cfddf4... (gist 3b2c5d8c...).

## 2. Verify every circuit (exhaustive + symbolic + must-fail controls)
    for f in aes107_k35 aes107_k36 aes110_d7 aes112_d6 aes107_d13 aes108_d12; do
      python3 -I tools/verify.py circuits/$f.slp --field 0x11B; done
    python3 -I tools/verify.py circuits/final_f73.slp    --field 0x89
    python3 -I tools/verify.py circuits/final_f73_d6.slp --field 0x89
    python3 -I tools/verify.py circuits/final_f4.slp     --field 0x13
    python3 -I tools/verify.py circuits/final_f5.slp     --field 0x25
    python3 -I tools/verify.py circuits/final_f12.slp    --field 0x1009
    python3 -I tools/verify.py circuits/final_f13.slp    --field 0x201b
    python3 -I tools/verify.py circuits/M128.slp --poly       # symbolic only (2^256 pairs)
Expected: `'ok': True`, controls (12, 12, []), and total/depth equal to the paper's Table 1.

## 3. Lean (core Lean v4.34.1, no Mathlib; ~15-22 min and ~3 GB each for GF(2^8), ~3 min for GF(2^7))
    nice -n 19 lean --threads=1 lean/Aes112d6.lean     # likewise Aes110d7, Aes107k35, Aes107k36, Aes109, Aes114d9, Aes113d15, Aes112d14, Aes110d20, Aes108d19, Aes115d15, Gf7_f73, Gf7_f73_d6, Gf7_f74, Gf6, Gf4Rec, Gf5Rec
Expected last lines: `#print axioms` lists only [propext] for circuit_ok, control_mutant, control_wrong_poly.
Saved outputs of our runs: lean/*.out. All of Aes107d13 and Aes108d12 (re-run: 14m10s, 14m17s) are Lean-checked too, as are the ladder circuits, the 115-gate circuit and the 0x91 and 0x49 circuits; lean/SHA256SUMS holds SHA-256 hashes of every file in lean/. Theorem as written: `circuit_ok : allOkC = true`, a conjunction of 64 decided Boolean chunks, each checking evalPt circuit a b == gmul a b for its range; equivalent to the forall-statement by unfolding the definitions. The gate lists in the Lean files are generated from the .slp circuit files by tools/gen_lean.py (its docstring still says tools/lean/); the .lean files are hashed in lean/SHA256SUMS but are not under the commitment root. Chunk layout per field: Aes* 64 chunks x 4 values of a, Gf7 64 x 2, Gf6 64 x 1, Gf5Rec 32 x 1, Gf4Rec 16 x 1. Lean version: lean/lean_version.txt (4.34.1, x86_64 Linux). Timings: see lean/*.out (about 1 s for GF(2^4) up to 17m45s for GF(2^8)); every .out records its logged time and exit=0.

## 3b. Released after the commitment (NOT under the commitment root; hashes in the paper's Table 6)
    for p in aes114_d9 aes113_d15 aes112_d14 aes110_d20 aes109_d18 aes108_d19; do python3 -I tools/verify.py circuits/$p.slp --field 0x11B; done
    python3 -I tools/verify.py circuits/final_f7.slp --field 0x91
    python3 -I tools/verify.py circuits/final_f6.slp --field 0x49
    python3 -I tools/verify.py circuits/aes115_cmtprods_d15.slp --field 0x11B   # 115 gates, 48 AND, 67 XOR, depth 15; CMT products with our layers
    python3 -I tools/verify.py --baselines OUT.md   # re-verifies the third-party circuits in sources/circuits (about a minute)
    python3 -I sources/ideas/anatomy.py circuits/aes107_k36.slp   # layered floor 105
Baseline arithmetic for the small fields: `python3 -I tools/naive_reduction.py 0x13 25` (also 0x25 41, 0x1009 207, 0x201b 255) prints the naive reduction XOR count and M(m)+reduction.

## 4. Search tools (reference)
tools/depth.py (depth rebalancing), tools/window_sat.py (window SAT, needs pysat), tools/linear_opt.py (Paar/BP/RNBP).
