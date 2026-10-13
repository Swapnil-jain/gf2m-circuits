# GF(2^m) field multipliers

Model: AND + XOR fan-in 2, polynomial basis. Method: keep the FP19 product set, merge the reduced output map, and re-synthesise with tools/linear_opt.py (paar/bp/rnbp). Sweep tools/depth.py. tools/window_sat.py found no local improvement. Baselines use tools/naive_reduction.py.

| field | polynomial | record | ours (total = AND+XOR) | depth | sha256 (12) | file | status |
|---|---|---|---|---|---|---|---|
| GF(2^9) | x^9+x^4+1 (0x211) | none | 136 = 54+82 | 7 | 1dd6f01bc71a | f9_d7.slp | verified. no dedicated published circuit found (Mastrovito formula count 2m²−1 is higher). below the M(9)+naive-reduction baseline by 6 |
| GF(2^9) | x^9+x^4+1 (0x211) | none | 144 = 54+90 | 6 | 66a78d059c4a | f9_d6.slp | verified. no dedicated published circuit found (Mastrovito formula count 2m²−1 is higher). depth-6 variant |
| GF(2^10) | x^10+x^3+1 (0x409) | none | 172 = 52+120 | 8 | c09e79e866ad | f10_d8.slp | verified. no dedicated published circuit found (Mastrovito formula count 2m²−1 is higher). equals the baseline. no gain claimed |
| GF(2^11) | x^11+x^2+1 (0x805) | none | 199 = 78+121 | 8 | b78e46259382 | f11_d8.slp | verified. no dedicated published circuit found (Mastrovito formula count 2m²−1 is higher). below the M(11)+naive-reduction baseline by 7 |
| GF(2^128) GHASH | x^128+x^7+x^2+x+1 | none found (author gives M(128) only) | 11972 = 3888+8084 | 20 | 74e3fe5bd998 | ghash_base.slp | verified symbolically. equals the baseline. no gain claimed |
| GF(2^14) | x^14+x^5+1 (0x4021) | none | 307 = 120+187 | 9 | aa41b4488e39 | f14_d9.slp | verified, exhaustive over all 2^28 pairs. 8 below the M(14)+naive-reduction baseline of 315, and 2 shallower. Mastrovito formula count 2m^2-1 is 391 |
| GF(2^14) | x^14+x^5+1 (0x4021) | none | 308 = 120+188 | 8 | b4f3ded8f06c | f14_d8.slp | verified, exhaustive over all 2^28 pairs. 7 below the M(14)+naive-reduction baseline of 315, and 3 shallower. Mastrovito formula count 2m^2-1 is 391 |
| GF(2^15) | x^15+x+1 (0x8003) | none | 340 = 117+223 | 10 | dd19bada8beb | f15_d10.slp | verified, exhaustive over all 2^30 pairs. equal to the baseline of 340, and 2 shallower. Mastrovito formula count 2m^2-1 is 449 |
| GF(2^16) | x^16+x^5+x^3+x+1 (0x1002b) | none | 402 = 144+258 | 10 | 3167ee8a671a | f16_d10.slp | verified, symbolic only, 2^32 pairs is past the verifier limit. 7 below the M(16)+naive-reduction baseline of 409, and 2 shallower. Mastrovito formula count 2m^2-1 is 511 |

Verification commands, run from multipliers:

    python3 -I tools/verify.py contrib/circuits/f9_d7.slp --field 0x211 --controls 12
    python3 -I tools/verify.py contrib/circuits/f9_d6.slp --field 0x211 --controls 12
    python3 -I tools/verify.py contrib/circuits/f10_d8.slp --field 0x409 --controls 12
    python3 -I tools/verify.py contrib/circuits/f11_d8.slp --field 0x805 --controls 12
    python3 -I tools/verify.py contrib/circuits/ghash_base.slp --field 0x100000000000000000000000000000087 --controls 3
    python3 -I tools/verify.py contrib/circuits/f128.slp --field 0x100000000000000000000000000000087 --controls 3
    python3 -I tools/verify.py contrib/circuits/f131.slp --field 0x80000000000000000000000000000010d --controls 3
    python3 -I tools/verify.py contrib/circuits/f163.slp --field 0x800000000000000000000000000000000000000c9 --controls 3
    python3 -I tools/verify.py contrib/circuits/f233.slp --field 0x20000000000000000000000000000000000000004000000000000000001 --controls 3
    python3 -I tools/verify.py contrib/circuits/f251.slp --field 0x800000000000000000000000000000000000000000000000000000000000095 --controls 3
    python3 -I tools/verify.py contrib/circuits/f283.slp --field 0x800000000000000000000000000000000000000000000000000000000000000000010a1 --controls 3
    python3 -I tools/verify.py contrib/circuits/f14_d9.slp --field 0x4021 --controls 12
    python3 -I tools/verify.py contrib/circuits/f14_d8.slp --field 0x4021 --controls 12
    python3 -I tools/verify.py contrib/circuits/f15_d10.slp --field 0x8003 --controls 12
    python3 -I tools/verify.py contrib/circuits/f16_d10.slp --field 0x1002b --controls 12
    python3 -I tools/verify.py contrib/circuits/f16_d9.slp --field 0x1002b --controls 12

Baseline commands and results: `python3 -I tools/naive_reduction.py 0x211 126` gives 142. `python3 -I tools/naive_reduction.py 0x409 154` gives 172. `python3 -I tools/naive_reduction.py 0x805 186` gives 206. `python3 -I tools/naive_reduction.py 0x4021 289` gives 315, `0x8003 312` gives 340 and `0x1002b 349` gives 409.

Run the included builders from `multipliers/`, for example: `python3 -I contrib/scripts/build_field.py --m 9 --poly 0x211 --out /tmp/f9.slp`. They use `tools/` by a path relative to the script.

Timings (one core per job): build_field 507 s / 755 s / 1003 s for m=9/10/11. GHASH naive merge 200 s (verify 193 s). Depth sweep about 500 s per field. Window SAT: m=9 1900 windows, 1892 UNSAT at w−1, 0 hits. m=10 1361 windows, 1342 UNSAT, 0 hits. m=11 1609 windows, 1602 UNSAT, 0 hits. Verification: 1.2 s / 1.3 s / 1.4 s for m=9/10/11. GHASH about 3 minutes total.

## The reduction layer is not naive for a pentanomial

`tools/naive_reduction.py` prices reduction as a fold cascade: 2(m-1) XORs for a trinomial and
4(m-1) for a pentanomial. Treating that same reduction map as a linear program over the 2m-1
product coefficients, and running `tools/linear_opt.py` on it, leaves every trinomial cascade
unchanged but shortens every pentanomial one.

| field | polynomial weight | naive cascade | optimised | saved |
|---|---|---|---|---|
| every trinomial here: GF(2^9), (2^10), (2^11), (2^12), (2^14), (2^15), (2^233) | 3 | 2(m-1) | the same | 0 |
| GF(2^8), AES | 5 | 28 | 21 | 7 |
| GF(2^13) | 5 | 48 | 39 | 9 |
| GF(2^16) | 5 | 60 | 53 | 7 |
| GF(2^128), GHASH | 5 | 508 | 448 | 60 |
| GF(2^131) | 5 | 520 | 520 | 0 |
| GF(2^163) | 5 | 648 | 576 | 72 |
| GF(2^251) | 5 | 1000 | 886 | 114 |
| GF(2^283) | 5 | 1128 | 912 | 216 |

Every trinomial cascade checked is already optimal, which is what the sparsity predicts. Most of the
pentanomials give something back, between 10 and 25 per cent of the layer, but GF(2^131) gives nothing, so
the saving depends on the exponent pattern and not on the weight alone. The only way to know is to run it.
| GF(2^16) | x^16+x^5+x^3+x+1 (0x1002b) | none | 404 = 144+260 | 9 | 479062dfd378 | f16_d9.slp | verified, symbolic only, 2^32 pairs is past the verifier limit. 5 below the M(16)+naive-reduction baseline of 409, and 3 shallower. Mastrovito formula count 2m^2-1 is 511 |
| GF(2^128) | x^128+x^7+x^2+x+1 (0x10000000...) | none | 11912 = 3888+8024 | 20 | ad942df47bf2 | f128.slp | verified symbolically. reduction 448 against the naive 508. 60 below the baseline of 11972. the GHASH field of AES-GCM |
| GF(2^131) | x^131+x^8+x^3+x^2+1 (0x80000000...) | none | 12481 = 3520+8961 | 145 | 6232fed87f08 | f131.slp | verified symbolically. reduction 520 against the naive 520. equal to the baseline of 12481. the sect131 curves |
| GF(2^163) | x^163+x^7+x^6+x^3+1 (0x80000000...) | none | 17499 = 5292+12207 | 179 | 908a168f39f9 | f163.slp | verified symbolically. reduction 576 against the naive 648. 72 below the baseline of 17571. the sect163 curves |
| GF(2^233) | x^233+x^74+1 (0x20000000...) | none | 29818 = 9610+20208 | 246 | 36cf8ffa5e43 | f233.slp | verified symbolically. reduction 464 against the naive 464. equal to the baseline of 29818. the sect233 curves |
| GF(2^251) | x^251+x^7+x^4+x^2+1 (0x80000000...) | none | 33982 = 9455+24527 | 266 | 2ec135b61ace | f251.slp | verified symbolically. reduction 886 against the naive 1000. 114 below the baseline of 34096. the BBE251 binary Edwards curve |
| GF(2^283) | x^283+x^12+x^7+x^5+1 (0x80000000...) | none | 39647 = 10897+28750 | 299 | da44d52ab3e9 | f283.slp | verified symbolically. reduction 912 against the naive 1128. 216 below the baseline of 39863. the sect283 curves |

Both GF(2^16) circuits are built that way, by `scripts/opt_reduction.py`: the published M(16) circuit
is kept whole and only its reduction layer is re-synthesised. Four independent 4,000-restart runs
all reach 53. The same construction run on the two trinomials reproduces their quoted baselines
exactly, 315 for m=14 and 340 for m=15, both verified exhaustively.

This does not improve the fields already covered here. For GF(2^13), M(13) plus the optimised
reduction is 294, against 303 for the quoted baseline and 283 for `circuits/final_f13.slp`.

## Depth

`scripts/iterate_depth.py` re-runs `tools/depth.py sweep` on its own output until a round stops
improving, keeping the best circuit at each depth. The sweep drops gates as well as depth: the
GF(2^14) circuit went from 308 gates at depth 14 to 308 at depth 8 and then 307 at depth 9.

## Window SAT

`tools/window_sat.py` was run on each shipped circuit with the ANF semantics, windows 4 to 10, several seeds. It found no local improvement anywhere, which is the same outcome as the first contribution.

| circuit | seeds | windows | proved UNSAT at one gate fewer |
|---|---|---|---|
| f14_d8.slp, 308 gates | 2 | 1,193 and 1,188 | 1,095 and 1,068 |
| f15_d10.slp, 340 gates | 3 | 1,272, 1,167 and 1,177 | 1,136, 1,028 and 1,033 |

For reference, the same tool run for 40 minutes on `circuits/final_f7.slp` covered 895 windows with 794 proved UNSAT and did not move its 87 gates either.
