# gf2m-circuits

Circuits, Lean 4 proofs and verifiers for two preprints by Swapnil Jain (October 2026):

1. **Smaller Gate Counts for Polynomial-Basis Binary-Field Multipliers.** [ResearchGate](https://www.researchgate.net/publication/415561348), PDF in [`papers/`](papers/), artifacts in [`multipliers/`](multipliers/).
   - AES-field (x^8+x^4+x^3+x+1) multiplication in **112 gates at depth 6** (previously 117 at depth 6), and 107 gates at depth 13.
   - GF(2^7) in 83 gates; an explicit 11,464-gate 128x128 polynomial multiplier; explicit circuits for GF(2^4), GF(2^5), GF(2^12) and GF(2^13).
2. **Smaller Gate Counts for the AES S-box and Inverse S-box in the AND/XOR/XNOR Model.** [ResearchGate](https://www.researchgate.net/publication/415560965), PDF in [`papers/`](papers/), artifacts in [`sbox/`](sbox/).
   - AES S-box in **106 gates** (depth 24), inverse S-box in **109 gates** (depth 30), and 121 gates at depth 16.

Each paper's claims, including the exact comparisons with prior circuits and their depths, are in the paper. Please cite the papers rather than this README.

## Contributions

- [ahrazzle](https://github.com/ahrazzle) contributed verified multipliers for GF(2^9) (136 gates), GF(2^10), GF(2^11) (199 gates) and the GHASH field GF(2^128), built with the papers' method. They are in [`multipliers/contrib/`](multipliers/contrib/), outside the commitment.

## Checking the results

Each folder has its own README with the exact commands. The verifiers need only Python 3 (standard library):
- `multipliers/tools/verify.py` checks a circuit exhaustively over all input pairs, symbolically, and against must-fail controls;
- `sbox/tools/verify_sbox.py` does the same for the 256-entry S-box tables.

The `lean/` folders hold Lean 4 (v4.34.1, core only) kernel proofs (`decide +kernel`) for every circuit marked L in the papers, together with their outputs.

## Commitment

SHA-256 hashes of the circuit files were posted publicly before the papers went up. The papers list which files each commitment covers.
- [Gist v1](https://gist.github.com/Swapnil-jain/3b2c5d8c6b656e5a9cef2961d65434e0): root `f9cfddf4…`
- [Gist v2](https://gist.github.com/Swapnil-jain/6750e3f460658bc51c9a5f376c93af72): root `7139c329…`

## Prior work and third-party files

The circuits improve on, and are compared with, published circuits by Boyar, Peralta, Find, Calik and the Circuit Minimization Team; NIST's usnistgov/Circuits collection; and Bernstein's binary polynomial multiplication tables. Copies of some of their circuit files are included under `multipliers/sources/circuits/` and `sbox/prior/`, solely so that the comparisons can be re-checked. Each copy names its origin. See [NOTICE](NOTICE).

## License

Our code and circuits are licensed under Apache-2.0 ([LICENSE](LICENSE)); the papers are licensed under CC BY 4.0. Third-party files keep their original terms.
