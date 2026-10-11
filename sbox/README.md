# Repro pack: AES S-box and inverse S-box circuits

Python 3 standard library only for the verifier. Run everything from this directory.

Layout: circuits/ (.json = machine form, .txt = readable listing), lean/ (.lean, and .out where the run has finished),
prior/ (prior-work circuits quoted in the paper: raw NIST/CMT files in prior/raw/, our JSON conversion), provenance/ (driver logs of the depth lane),
tools/ (verify_sbox.py, prior_circuits.py, overlap.py, and_depth.py, make_listing.py, gen_sbox_lean.py; rep_sweep.py is the representation-sweep builder, shown for
reference, it imports the search code of the author's working tree and is not runnable from this pack),
commitment/ (SHA256SUMS, SHA256SUMS.v1, ROOT.txt, GIST.txt, NAMEMAP.txt), verify_results.txt (output of step 1).

Gate model: {AND, XOR, XNOR}, cost 1 each, no NOT. XNOR(x,y) = 1 xor x xor y. Bit order MSB-first: signals 0..7 are
U0..U7 with U0 the most significant input bit; outputs S0..S7 with S0 the most significant output bit.
JSON: {"gates": [[op, x, y], ...], "outputs": [...]}; signal 8+i is gate i. Listing: `Ti = X + Y` (XOR), `x` (AND), `~` (XNOR).

## 1. Verify every circuit (exhaustive 256 inputs + symbolic ANF + 7 must-fail controls)
    for f in circuits/*.json; do python3 -I tools/verify_sbox.py $f; done
The table is computed inside the verifier from GF(2^8) inversion (modulus 0x11B) plus the FIPS-197 affine map; the inverse
table is its inverse permutation. The program auto-detects forward/inverse and prints `matches=sbox|invsbox`.
Expected: all 11 lines end in OK, controls_wrongly_accepted=[]. Saved output: verify_results.txt.

## 2. Commitment
    shasum -a 256 commitment/SHA256SUMS      # 7139c329... (v2 root, gist 6750e3f4...)
    shasum -a 256 commitment/SHA256SUMS.v1   # f9cfddf4... (first root, gist 3b2c5d8c...)
Both gists are weak timestamps (a gist is editable by its owner). The two files differ only in two lines, aes107_d13.slp and
aes108_d12.slp: GF(2^8) multiplier circuits of the companion multiplier paper, not S-box circuits (they are not in this pack, nor are
the other multiplier files). See NAMEMAP.txt for the seven circuit files that are under both roots. The four depth points sbox111_d21,
sbox112_d18, sbox112_d20 and invsbox109_d30 are released but NOT under either root. To check one circuit:
    grep sbox_106_d24.json commitment/SHA256SUMS; shasum -a 256 circuits/sbox106_d24.json

## 2b. Prior circuits, depth recount and lineage
    python3 -I tools/prior_circuits.py   # parses prior/raw/* (data only), checks each computes the S-box, recounts depth (prior_recount.txt)
    python3 -I tools/overlap.py          # gate-function overlap table and the baseline among prior circuits (overlap_results.txt)
    python3 -I tools/and_depth.py        # gate depth and AND depth of every circuit, ours and prior (and_depth_results.txt)
Recount: NIST aes-sbox-a34-ad4-g125-gd15-xx91-4 = 125 gates, depth 15; CMT AESDEPTH16SIZE125 = 125 gates, depth 16 (different circuits).
provenance/ holds the driver logs of the three depth-lane runs (Pareto front after most rounds; driver.log has no round 3, driver_n.log no round 5); per-circuit logs were not saved. front.md is the first lane's front (it lists 113/18 and 112/20 but not 112/18, which first appears in the second lane).

## 3. Lean (core Lean 4, no Mathlib; each check took 8.3 to 9.2 s, see the `real` line of lean/*.out)
    lean lean/Sbox106d24.lean          # likewise the other files; .out files are the saved outputs
All eleven files are Lean-checked (circuit_ok depends on axioms [propext]): Sbox106 (=sbox106_d34), Sbox106d24, Sbox110 (=sbox110_d38),
Sbox113d18, Sbox116d17, Sbox121d16, InvSbox109 (=invsbox109_d31), Sbox112d18, Sbox111d21, Sbox112d20, InvSbox109d30.
Lean proves equality with a literal 256-entry table only; gate counts and depth come from tools/verify_sbox.py.
All eleven .lean files were checked in their released form with Lean 4.34.1 (lean/lean_version.txt); each .out records exit=0 and timing.
lean/SHA256SUMS lists hashes of the .lean and .out files (not part of the commitment).
Regenerate a file (the gate list and theorem match the released file; only a header comment line differs, the released files came from a slightly earlier generator version): `python3 tools/gen_sbox_lean.py circuits/sbox106_d24.json Sbox106d24 Sbox106d24.lean` (INV=1 in the environment for inverse circuits).
The Lean files are not covered by the commitment hashes.

Note: a 110-gate depth-22 file was in our working tree but is gate-for-gate the NIST usnistgov/Circuits circuit (aes-sbox-a32-ad5-g110-gd22), so it is not our result and is not in this pack.

Only verification, the prior recount, the overlaps, AND depth and the Lean checks are reproducible from this pack; the search code is not released.
