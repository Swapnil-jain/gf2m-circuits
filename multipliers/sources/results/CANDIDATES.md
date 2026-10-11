# AES GF(2^8) candidates re-verified by tools/verify.py (independent of lane A's emit_aes.py / verify_slp.py)

2026-10-11. Spec: polynomial basis, P = x^8+x^4+x^3+x+1 (0x11B), gates = fan-in-2 AND/XOR. Checks: exhaustive
(all 65,536 pairs, bitsliced), symbolic (exact ANF of each output = reduced bilinear form), reference spot check vs
scalar clmul mod P, and 22 must-fail controls (10 gate flips, 10 operand rewires, a0/a1 swap, wrong polynomial 0x11D),
all caught. No dead gates (live = total).

| File | SHA-256 | Total | AND | XOR | Depth | Exhaustive | Symbolic | Controls |
|---|---|---|---|---|---|---|---|---|
| results/verified_snap/aes107_k35.slp (from leads/cand/laneA_aes107_k35.slp) | ebae5b576046b74552c243214b3ecb6711a9ab785bfc3de207a162dadc11da09 | **107** | 35 | 72 | 19 | PASS | PASS | 12/12 |
| results/verified_snap/aes107_k36.slp (from leads/cand/laneA_aes107_k36.slp) | 7bdcaf469f0c433d5357db9d742f93d0eec089e3d5e7a996672bb97e0af7f90f | **107** | 36 | 71 | 18 | PASS | PASS | 12/12 |
| leads/cand/aes_x_s3.slp / aes_x_s4.slp | f0c61c1a... / 8568a053... | 108 | 34 / 40 | 74 / 68 | 19 / 18 | PASS | PASS | 12/12 |
| leads/cand/aes_t_s2.slp | 30e169d7...(see shasum) | **109** | 33 | 76 | 18 | PASS | PASS | 22/22 |
| leads/cand/aes_t_s1.slp | 3d84794d... | 110 | 32 | 78 | 20 | PASS | PASS | 22/22 |
| leads/cand/aes_t112.slp | 448b7047... | 112 | 43 | 69 | 14 | PASS | PASS | 22/22 |
| leads/cand/aes_split.slp | c05434a1...d98a3 | 114 | 43 | 71 | 9 | PASS | PASS | 22/22 |
| leads/cand/aes_t113.slp | cd980adf...26ef | 113 | 43 | 70 | 15 | PASS | PASS | 22/22 |
| leads/cand/aes_cmtprods_t115.slp | ec38207d...1c19 | 115 | 48 | 67 | 15 | PASS | PASS | 22/22 |

Record for comparison: CMT slp_84310.txt, 117 = 48 AND + 69 XOR, depth 6 (re-verified here too). The candidates
beat it on total gates (model (a)) only; their depth is higher (9, 15 vs 6), so they are not records in a depth model.
Lean: pending (tools/lean/).

Snapshots of exactly the verified bytes: results/verified_snap/ (SHA256SUMS there). Lane A files may change later.
| results/verified_snap/aes112_d6.slp (depth lane, rebalanced 107 k36) | af49795ac6920cdf... | **112** | 36 | 76 | **6** | PASS | PASS | 46/46 |
