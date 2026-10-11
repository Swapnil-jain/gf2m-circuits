# Other-field multipliers (2026-10-11)

Model: AND + XOR fan-in 2, polynomial basis. Pipeline: leads/scripts/fields_gen.py (split-family sampling, solved merged
output map, exact/Paar/BP layers, transposed bottom), then tools/linear_opt.py and tools/window_sat.py (sweep 2), then
tools/depth.py (depth variants). Sweeps: 1 sampling (60 jobs x 25 min), 2 polish, 3 more sampling; stopped after
sweep 3 found nothing new (only GF(2^12) moved, 213 -> 210, in sweep 2). Window SAT produced no output on GF(2^13).
Verification (tools/verify.py): symbolic ANF + exhaustive over all 2^(2m) pairs + 14/14 must-fail controls, for every file.

| field | polynomial | record | ours (total = AND+XOR) | depth | sha256 (12) | file | status |
|---|---|---|---|---|---|---|---|
| GF(2^4) | x^4+x+1 (0x13) | none | 30 = 10+20 | 5 | 9fa1f95b59da | final_f4.slp | verified; first published (no record) |
| GF(2^5) | x^5+x^2+1 (0x25) | none | 44 = 20+24 | 6 | 4c171804c7c9 | final_f5.slp | verified; first published |
| GF(2^6) | x^6+x^3+1 (0x49) | CMT 57 | 57 = 27+30 | 5 | 73e414510597 | final_f6.slp | verified; TIES record, no gain |
| GF(2^7) | x^7+x^4+1 (0x91) | CMT 84 | 87 = 32+55 | 11 | 0f6d4f4d0952 | final_f7.slp | verified; does NOT beat (3 above) |
| GF(2^7) | x^7+x^3+1 (0x89) | CMT 85 | **83** = 32+51 | 7 | 519d1835d18b | final_f73.slp | verified; BEATS record by 2; Lean PASS |
| GF(2^7) | x^7+x^3+1 (0x89) | CMT 85 (depth 5) | **83** = 32+51 | 6 | e704a7468be6 | final_f73_d6.slp | verified; BEATS record by 2; Lean PASS |
| GF(2^12) | x^12+x^3+1 (0x1009, McEliece) | none | 210 = 78+132 | 17 | e983be789bfd | final_f12.slp | verified; first published |
| GF(2^13) | x^13+x^4+x^3+x+1 (0x201b, McEliece) | none | 283 = 94+189 | 29 | a4eca82092bb | final_f13.slp | verified; first published |

McEliece polynomials checked: both irreducible, and equal to the spec's x^12+x^3+1 and x^13+x^4+x^3+x+1.
Depth: the CMT 85-gate record has depth 5; our 83-gate circuits are depth 6 and 7 (depth-5 not found at 83).
Lean (box 1, core Lean, decide +kernel, ~177 s, 1.2 GB): tools/lean/Gf7_f73.lean and Gf7_f73_d6.lean, circuit_ok plus
both controls refuted, axioms only propext (outputs .out beside them). Lean was not run on non-beating fields.
Caveat: literature check for these fields is the CMT page and lit/RECORDS.md only.

## Large polynomial multiplication M(n) (leads/scripts/kara_big.py, FP19 bases, one-level Karatsuba plans)
Symbolic verification only (tools/verify.py --poly, 12 must-fail controls on M128).

| n | record (Bernstein 2009) | ours | sha256 (12) | file | status |
|---|---|---|---|---|---|
| 128 | 11486 | **11464** = 3888 AND + 7576 XOR, depth 16 | aa5594ff03e8 | M128.slp | verified symbolically; BEATS by 22 (3*M(64)+7*64-3, FP19 M(64)=3673) |
| 113 | 9534 | 9703 | - | M113.slp | does not beat |
| 163 | 16923 | 17563 | - | M163.slp | does not beat |
| 233 | 29354 | 31176 | - | M233.slp | does not beat |
| 256 | 34079 | 35285 | - | M256.slp | does not beat (Karatsuba on M(128) only; Bernstein's splits are richer) |
| 283 | 38735 | 42704 | - | M283.slp | does not beat |
