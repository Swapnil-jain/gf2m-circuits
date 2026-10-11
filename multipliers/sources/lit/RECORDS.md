# RECORDS: best known circuits for GF(2)[x] and GF(2^m) multiplication (lit-records, 2026-10-11)

PRIVATE. Web pages were read as data; circuit files were downloaded as data (provenance and hashes in
`circuits/PROVENANCE.md`, `circuits/SHA256SUMS`) and parsed only by our own code in `lit/scripts/`.

Labels: **[ver]** we parsed the published circuit and verified it ourselves (symbolic ANF check of every output,
or exhaustive / 256-lane random simulation where stated); **[src]** read in the primary source this session;
**[mem]** from memory, not re-checked; **[heur]** our judgement.

Gate model unless stated: 2-input AND and XOR, each cost 1, no free constants needed (all records below use none
except where XNOR is listed). "Depth" = longest gate path, all gates depth 1.

Verifier: `lit/scripts/slpcheck.py <file> poly|field:<hex poly>|any`. Must-fail controls passed: an AND turned into
XOR, a rewired operand, and the 117 checked against the wrong modulus (0x11d) are all rejected [ver].

## 1. Binary polynomial multiplication M(n), n x n -> 2n-1 coefficients, polynomial (monomial) basis

Two sources hold every record for n <= 100:
- **Bernstein**, binary.cr.yp.to/m.html, page version **2009.05.31**, entries dated 2000.08 or 2009.05. Circuits for
  every n <= 1000 at `bbe251/<n>.gz` (downloadable).
- **Find–Peralta (FP19)**, "Better Circuits for Binary Polynomial Multiplication", IEEE TC 68(4) 2019,
  doi 10.1109/TC.2018.2874662 (PMC6774206) [src]. Their Table 5 numbers equal, entry for entry, the circuits in
  Peralta's `BinPolMult.tar.gz` (files dated **2016-04-27**), which we verified for all n = 2..100 [ver]. M(11) = 186
  and M(12) = 207 first appeared on the CMT page (June 2012); M(15) = 312 improves Cenk–Hasan 2015 (317).
- The previous-best column of FP19 is Cenk–Hasan ("sCH": ePrint 2015/094 and the Cenk–Hasan–Nègre TC 2014 line).
  No published improvement on any n after FP19 was found: web, arXiv API and GitHub searches for 2019-2026 came
  back empty [src, negative].

No AND/XOR/depth record exists separately; FP19 also tabulates depth, and the CMT page has a size-depth pair for
n = 10: `binary_pol_mult/B10size154depth7` is 154 gates at depth 7 and `B10size155depth6` is 155 at depth 6 [ver]; the
tarball's 154-gate copy (used in the table) has depth 9.

Bilinear rank (= the least number of ANDs in a bilinear circuit) over F2: LB from Chengu Wang arXiv 2603.07280
(v11 2026-08-29, certificates on GitHub `wcgbg/tensor-rank-lower-bound`) [src]; UB from Montgomery IEEE TC 2005
(13/17/22 for 5/6/7 terms) and [16] in Wang for 26 at n = 8 [src]. Exact for n <= 5. **Correction to the brief:
22 is the best UPPER bound for n = 7; the lower bound is 19 (Wang 2026, up from 18).** Unrestricted (non-bilinear)
multiplicative complexity: MC(Mul3) = 6, MC(Mul4) = 9 (Morse arXiv 2608.30238, 2026-08-31, Lean 4) [src].

Lower bounds on TOTAL gates: none beyond trivial ones were found [src, negative]. Optimality of M(n) is not
proved for any n >= 3 as far as we know [heur]; for n = 2, 5 gates is the trivial optimum [heur, unproved here].

Table (all rows [ver]: circuit downloaded and checked by `slpcheck.py`, both FP19 and Bernstein files):

| n | record total | AND | XOR | depth | holder | Bernstein 2009 (total/AND/depth) | bilinear rank over F2 (LB-UB) | notes |
|---|---|---|---|---|---|---|---|---|
| 2 | 5 | 4 | 1 | 2 | tie FP19 = Bernstein | 5/4/2 | 3 |  |
| 3 | 13 | 9 | 4 | 3 | tie FP19 = Bernstein | 13/9/3 | 6 |  |
| 4 | 25 | 16 | 9 | 3 | tie FP19 = Bernstein | 25/16/4 | 9 |  |
| 5 | 41 | 25 | 16 | 4 | tie FP19 = Bernstein | 41/25/5 | 13 |  |
| 6 | 57 | 27 | 30 | 6 | tie FP19 = Bernstein | 57/27/6 | 16-17 |  |
| 7 | 81 | 40 | 41 | 6 | tie FP19 = Bernstein | 81/40/7 | 19-22 |  |
| 8 | 100 | 48 | 52 | 6 | tie FP19 = Bernstein | 100/48/7 | 21-26 |  |
| 9 | 126 | 54 | 72 | 6 | FP19 (circuit 2016) | 132/65/8 |  |  |
| 10 | 154 | 52 | 102 | 9 | FP19 (circuit 2016) | 155/75/8 |  | also 155 gates / depth 6 (CMT B10size155depth6, 75 AND) |
| 11 | 186 | 78 | 108 | 7 | FP19 (circuit 2016) | 189/78/9 |  |  |
| 12 | 207 | 81 | 126 | 8 | FP19 (circuit 2016) | 208/81/8 |  |  |
| 13 | 255 | 106 | 149 | 8 | FP19 (circuit 2016) | 256/106/9 |  |  |
| 14 | 289 | 120 | 169 | 9 | tie FP19 = Bernstein | 289/120/10 |  |  |
| 15 | 312 | 117 | 195 | 10 | FP19 (circuit 2016) | 329/135/10 |  |  |
| 16 | 349 | 144 | 205 | 8 | FP19 (circuit 2016) | 350/144/9 |  |  |
| 17 | 406 | 155 | 251 | 9 | FP19 (circuit 2016) | 414/177/10 |  |  |
| 18 | 438 | 162 | 276 | 9 | FP19 (circuit 2016) | 456/195/11 |  |  |
| 19 | 495 | 157 | 338 | 12 | FP19 (circuit 2016) | 502/214/10 |  |  |
| 20 | 522 | 208 | 314 | 11 | FP19 (circuit 2016) | 528/225/10 |  |  |
| 21 | 573 | 198 | 375 | 13 | FP19 (circuit 2016) | 602/230/12 |  |  |
| 22 | 632 | 234 | 398 | 10 | FP19 (circuit 2016) | 641/234/12 |  |  |
| 23 | 675 | 239 | 436 | 11 | FP19 (circuit 2016) | 678/239/10 |  |  |
| 24 | 702 | 243 | 459 | 11 | FP19 (circuit 2016) | 704/243/10 |  |  |
| 25 | 784 | 325 | 459 | 11 | FP19 (circuit 2016) | 800/292/12 |  |  |
| 26 | 853 | 318 | 535 | 11 | FP19 (circuit 2016) | 856/318/12 |  |  |
| 27 | 912 | 324 | 588 | 10 | FP19 (circuit 2016) | 922/345/12 |  |  |
| 28 | 944 | 352 | 592 | 14 | FP19 (circuit 2016) | 956/360/12 |  |  |
| 29 | 1009 | 353 | 656 | 13 | FP19 (circuit 2016) | 1044/389/13 |  |  |
| 30 | 1038 | 351 | 687 | 13 | FP19 (circuit 2016) | 1085/404/13 |  |  |
| 31 | 1113 | 404 | 709 | 12 | FP19 (circuit 2016) | 1129/422/12 |  |  |
| 32 | 1156 | 432 | 724 | 11 | FP19 (circuit 2016) | 1158/432/11 |  |  |
| 33 | 1271 | 453 | 818 | 12 | FP19 (circuit 2016) | 1286/497/13 |  |  |
| 34 | 1333 | 464 | 869 | 12 | FP19 (circuit 2016) | 1358/531/13 |  |  |
| 35 | 1392 | 478 | 914 | 11 | FP19 (circuit 2016) | 1441/566/13 |  |  |
| 36 | 1428 | 486 | 942 | 11 | FP19 (circuit 2016) | 1483/585/13 |  |  |
| 37 | 1552 | 475 | 1077 | 15 | FP19 (circuit 2016) | 1585/622/14 |  |  |
| 38 | 1604 | 574 | 1030 | 14 | FP19 (circuit 2016) | 1636/641/14 |  |  |
| 39 | 1669 | 520 | 1149 | 14 | FP19 (circuit 2016) | 1687/663/13 |  |  |
| 40 | 1703 | 624 | 1079 | 14 | FP19 (circuit 2016) | 1720/675/12 |  |  |
| 41 | 1806 | 603 | 1203 | 16 | FP19 (circuit 2016) | 1871/684/15 |  |  |
| 42 | 1862 | 594 | 1268 | 16 | FP19 (circuit 2016) | 1950/690/15 |  |  |
| 43 | 1982 | 665 | 1317 | 15 | FP19 (circuit 2016) | 2020/697/14 |  |  |
| 44 | 2036 | 702 | 1334 | 12 | FP19 (circuit 2016) | 2064/702/14 |  |  |
| 45 | 2105 | 702 | 1403 | 14 | FP19 (circuit 2016) | 2150/711/15 |  |  |
| 46 | 2179 | 692 | 1487 | 14 | FP19 (circuit 2016) | 2192/717/13 |  |  |
| 47 | 2228 | 724 | 1504 | 13 | FP19 (circuit 2016) | 2239/724/13 |  |  |
| 48 | 2259 | 729 | 1530 | 13 | FP19 (circuit 2016) | 2268/729/12 |  |  |
| 49 | 2436 | 892 | 1544 | 14 | FP19 (circuit 2016) | 2460/826/14 |  |  |
| 50 | 2523 | 676 | 1847 | 17 | FP19 (circuit 2016) | 2572/876/15 |  |  |
| 51 | 2663 | 960 | 1703 | 14 | FP19 (circuit 2016) | 2677/927/14 |  |  |
| 52 | 2725 | 954 | 1771 | 13 | FP19 (circuit 2016) | 2735/954/14 |  |  |
| 53 | 2841 | 910 | 1931 | 24 | FP19 (circuit 2016) | 2881/1007/15 |  |  |
| 54 | 2878 | 918 | 1960 | 24 | FP19 (circuit 2016) | 2948/1034/15 |  |  |
| 55 | 2987 | 1027 | 1960 | 17 | FP19 (circuit 2016) | 3017/1064/14 |  |  |
| 56 | 3022 | 1056 | 1966 | 17 | FP19 (circuit 2016) | 3060/1080/14 |  |  |
| 57 | 3145 | 999 | 2146 | 15 | FP19 (circuit 2016) | 3239/1137/16 |  |  |
| 58 | 3212 | 1050 | 2162 | 17 | FP19 (circuit 2016) | 3320/1164/16 |  |  |
| 59 | 3273 | 1054 | 2219 | 15 | FP19 (circuit 2016) | 3406/1197/15 |  |  |
| 60 | 3306 | 1053 | 2253 | 15 | FP19 (circuit 2016) | 3456/1214/15 |  |  |
| 61 | 3472 | 1158 | 2314 | 15 | FP19 (circuit 2016) | 3552/1247/16 |  |  |
| 62 | 3553 | 1212 | 2341 | 15 | FP19 (circuit 2016) | 3595/1264/15 |  |  |
| 63 | 3626 | 1267 | 2359 | 14 | FP19 (circuit 2016) | 3651/1285/15 |  |  |
| 64 | 3673 | 1296 | 2377 | 13 | FP19 (circuit 2016) | 3682/1296/13 |  |  |

Ties at n = 2..8: the FP19 files equal Bernstein's sizes but have smaller depth at n = 4, 5, 7, 8. The n = 2..5
circuits are schoolbook (n^2 AND); n = 6 and 8 are 2000.08 Bernstein; n = 7 is undated in Bernstein's table.

### 1b. Large n (crypto sizes) [ver: counts; 256-lane random simulation passed for 113, 163, 233, 283]

| n | record total | AND | XOR | depth | holder | file? | note |
|---|---|---|---|---|---|---|---|
| 113 | 9534 | 3227 | 6307 | 124 | Bernstein 2009.05 | yes | |
| 128 | 11486 | 3888 | 7598 | 16 | Bernstein 2009.05 | yes | **3·M(64)+7·64−3 = 11464 with FP19's M(64) = 3673**: a derivable bound 22 gates below the table, no published circuit [ver arithmetic, `scripts/recurrence_bounds.py`] |
| 131 | 11961 | 3520 | 8441 | 142 | Bernstein 2009.05 | yes | |
| 163 | 16923 | 5292 | 11631 | 175 | Bernstein 2009.05 | yes | |
| 193 | 21865 | 6504 | 15361 | 205 | Bernstein 2009.05 | yes | |
| 233 | 29354 | 9610 | 19744 | 244 | Bernstein 2009.05 | yes | |
| 251 | 33096 | 9455 | 23641 | 262 | Bernstein 2009.05 | yes | |
| 256 | 34079 | 9752 | 24327 | 268 | Bernstein 2009.05 | yes | |
| 283 | 38735 | 10897 | 27838 | 295 | Bernstein 2009.05 | yes | |

The FP19 recurrences alone (seeded with the n <= 100 circuits) beat Bernstein only at 127/128 among these sizes;
Bernstein's large-n codes win elsewhere through other splits. The huge depths come from his size-only goal.

## 2. GF(2^m) field multiplication

| m | basis / modulus | total | AND | XOR | depth | holder, date | file? | status |
|---|---|---|---|---|---|---|---|---|
| 2 | poly x^2+x+1 | 7 | 3 or 4 | 4 or 3 | 2 | folklore (Karatsuba or schoolbook) | - | [heur] no published record; trivially SAT-checkable |
| 3, 4, 5 | poly | - | - | - | - | **no published total-gate record found** | - | gap [src, negative] |
| 6 | poly x^6+x^3+1 | 57 | 27 | 30 | 5 | CMT (Peralta et al.), July 2010 | yes `slp_630.txt` | [ver]; previous best 61 / depth 5 |
| 7 | poly x^7+x^4+1 | 84 | 40 | 44 | 5 | CMT, July 2010 | yes `slp_740.txt` | [ver]; previous best 100 / depth 7 |
| 7 | poly x^7+x^3+1 | 85 | 40 | 45 | 5 | CMT, July 2010 | yes `slp_730.txt` | [ver] |
| 8 | **AES poly x^8+x^4+x^3+x+1** | **117** | 48 | 69 | 6 | CMT, July 2010 | yes `slp_84310.txt` | [ver]; previous published 135 / depth 7 |
| 8 | custom tower basis (unit = all-ones vector; basis undisclosed, "email for details") | **106** | 27 | 79 | 6 | CMT, 2017-09-20 | yes `GF256mult.s106.d6` | [ver] exhaustively: commutative, unit 0xFF, no zero divisors, associative on sampled triples, so a field multiplication in SOME basis |
| 9..15 | poly | - | - | - | - | **no published total-gate record found** (incl. m = 12, 13 for Classic McEliece) | - | gap [src, negative] |
| 16 | CMT tower | 520 (header says 519) | 108 | 412 | 19 | CMT (for the K3LR S-box), ~2017 | yes `multcircuit` | counted [ver], correctness not checked by us; Peralta calls it "not very good" [src] |
| 163/233/283 | NIST pentanomials/trinomial | - | - | - | - | no dedicated total-gate record; polynomial part = §1b plus a reduction of a few hundred XORs [heur] | - | gap |

Bilinear complexity of the field multiplication (min ANDs in a bilinear circuit): μ2(m) = 3, 6, 9 exact for
m = 2, 3, 4; m = 5: 13 UB; m = 6: 15; m = 7: ≤ 22; m = 8: ≤ 24 [src: Cotardo–Zullo arXiv 2605.12295, May 2026,
Table 1 (symmetric rank), which lists LBs only 10, 14, 16 for m = 5, 7, 8; mem for exactness of 15 at m = 6 via
Barbulescu–Detrey–Estibals–Zimmermann WAIFI 2012, whose PDF we could not fetch]. So the field-multiplication
lower bounds for m >= 5 are only about 2m: much weaker than the polynomial ones.

Bernstein–Lange "Type-II optimal polynomial bases" (2010) gives field-multiplication bit-op costs in type-II bases
for large m (binary Edwards sizes); no per-m table or circuits on type2.html (version 2017.01.22) [src].

## 3. Squaring and inversion

- **Squaring** is linear (free in a normal basis; an XOR count in a polynomial basis). No record table found for
  any m [src, negative]. Low value; SAT can settle m <= 16 exactly [heur].
- **AES S-box (= GF(2^8) inversion + affine), {AND, XOR, XNOR}:** 113 gates = 32 AND + 77 XOR + 4 XNOR, depth 27
  (Boyar–Peralta, improved by Calik; CMT `SLP_AES_113.txt`) [ver exhaustively, MSB-first]; low depth 125 gates /
  depth 16 (34 AND) [ver]; inverse S-box 121 gates / depth 21 (34 AND) [counted].
- **Richer basis {XOR, XNOR, NAND, NOR, MUX, NMUX}:** forward S-box 102 gates / depth 24 ("bonus":
  58 XOR + 6 XNOR + 27 NAND + 5 NOR + 6 MUX), inverse 101(+1 NOT), combined 127 (Maximov–Ekdahl TCHES 2019(4),
  ePrint 2019/802) [src: paper downloaded, listings in Appendix D]. Area records in GE (Reyhani-Masoleh–Taha–
  Ashmawy TCHES 2018; Ueno et al. CHES 2015) use a different metric and are not gate-count records.
- **GF(2^16) inversion:** 387 gates = 113 AND + 274 XOR, depth 31, tower basis (CMT) [counted]. The K3LR S-box
  built on it: 446 gates (113 AND, 324 XOR, 9 XNOR) [src].
- **GF(2^4) inversion:** used inside every S-box above; standalone records are embedded in the S-box papers only
  [mem]. Not tabulated separately.

## 4. Gaps: where the records are oldest or weakest

1. **Field multipliers for m = 3, 4, 5 and 9..16 have no published total-gate record at all**, including the
   Classic McEliece fields GF(2^12) and GF(2^13) and the tower subfields GF(2^4). Any verified circuit is a first
   entry, so the bar is "best derivable": FP19's M(m) plus a minimised reduction [heur].
2. **M(n) for n = 2..8 has not moved since 2000-2009** (FP19 only tied it), and these small cases feed every
   recurrence. No lower bound on total gates exists.
3. **M(n) for n > 100 is Bernstein 2009** for all n up to 1000. FP19 stopped at 100. M(128) is already beatable
   on paper by 22 gates from a known recurrence, with no circuit published.
4. **GF(2^8) AES-basis 117 is from July 2010**; the 106 tower circuit (2017) has an undisclosed basis. Peralta's
   pages have not changed for these since 2017 [src].
5. **Field-multiplication bilinear lower bounds for m >= 5 are about 2m** (Cotardo–Zullo table), while Wang's
   automated method has only been run on the polynomial (not field) tensors [src]. A cheap lower-bound lead,
   separate from our upper-bound goal.
6. Depth-constrained records exist only as FP19's depth column and a few CMT pairs: the size-depth Pareto front is
   largely unpublished.

## 5. Where the gap between multiplicative complexity and the record's AND count is largest (most room)

The record circuits buy fewer XORs with surplus ANDs. "AND surplus" = ANDs in the total-gate record minus the best
bilinear-rank upper bound; for composite n the rank UB uses the nesting bound R(ab) <= R(a)R(b) [heur, standard].

| target | record total | its ANDs | rank UB | rank LB | AND surplus |
|---|---|---|---|---|---|
| M(6) | 57 | 27 | 17 | 16 | 10 |
| M(7) | 81 | 40 | 22 | 19 | 18 |
| M(8) | 100 | 48 | 26 | 21 | 22 |
| M(9) | 126 | 54 | 36 (6·6) | - | 18 |
| M(10) | 154 | 52 | 39 (13·3) | - | 13 |
| M(12) | 207 | 81 | 51 (17·3) | - | 30 |
| M(14) | 289 | 120 | 66 (22·3) | - | 54 |
| M(15) | 312 | 117 | 78 (13·6) | - | 39 |
| M(16) | 349 | 144 | 78 (26·3) | - | 66 |
| GF(2^7), x^7+x^4+1 | 84 | 40 | 22 | 13 (14 symmetric) | 18 |
| GF(2^8), AES poly | 117 | 48 | 24 | 15 (16 symmetric) | 24 |
| GF(2^8), tower | 106 | 27 | 24 | 15 (16 symmetric) | 3 |

Largest relative room: **M(7), M(8) and the AES-basis GF(2^8)**, which use about twice the minimum AND count.
Nobody has published total-gate circuits built on the 22-, 26- or 24-AND bilinear formulas; whether their XOR
layers can be made cheap enough is open [heur]. At n = 14..16 the surplus is largest in absolute terms.
(Internal note: leads/LEADS.md reports a 114-gate AES-basis candidate with 43 ANDs; that is our candidate, not a
published record, and is not verified here.)

## 6. Crowding (who is active in 2025-26, and on which count)

| who | count / model | latest | threat to total-gate records |
|---|---|---|---|
| Gregory Morse (ELTE; AI-assisted, discloses GPT-5.6 and Opus 5) | unrestricted AND count, Mul4 = 9, n5/n6 workflows in repo | arXiv 2608.30238 (2026-08-31); repo pushed 2026-09-22 | low-medium: AND only, but has the circuit machinery |
| Chengu Wang | bilinear-rank LOWER bounds (poly products; 3x3 matmul ≥ 20, then ≥ 21 in repo `matrix-multiplication-n333r21f2`, 2026-09) | v11 2026-08-29 | low: lower bounds, not circuits |
| Cotardo–Zullo | symmetric rank of field multiplication | arXiv 2605.12295 (2026-05) | low |
| Perminov (`dronperminov/linear-expressions-optimization`) | additive (XOR-type) complexity of bilinear schemes, matmul focus | pushed 2026-10-10 | **medium: the XOR side of a bilinear scheme is exactly our lever** |
| Jérémy Jean; GitHub Joe-b-20 | XOR count of AES MixColumns (88) | 2026-07..10 | medium if they turn to multipliers |
| Saarinen (ePrint 2026/1786) | aggregate bit-op costs of McEliece attacks | 2026-09 | none (no circuits) |
| Find, Peralta, Boyar, Cenk, Hasan, Bernstein | total gates | last records 2016-2019 | dormant on this target |
| `yukiaraisnow/MPC` | AND counts of the AES S-box for MPC | 2026-09 | none |

Nobody published on total gate count of M(n) or GF(2^m) multipliers in 2020-2026 [src, negative: web, arXiv API,
GitHub].

## 7. Sources

binary.cr.yp.to/m.html, type2.html, linearmod2.html; www.cs.yale.edu/homes/peralta/CircuitStuff/CMT.html;
csrc.nist.gov/Projects/Circuit-Complexity; pmc.ncbi.nlm.nih.gov/articles/PMC6774206 (FP19); arxiv.org/abs/2603.07280
(+ html tables); arxiv.org/abs/2608.30238; github.com/GregoryMorse/unrestricted-boolean-mul;
github.com/wcgbg/tensor-rank-lower-bound; arxiv.org/abs/2605.12295; arxiv.org/abs/1705.07728 (Covanov: full product
only up to small cases); eprint.iacr.org/2012/110 (BDEZ, abstract only: PDF blocked); eprint.iacr.org/2022/921
(Fan: low-delay 4/5/6-term formulas, XOR counts not read); TCHES 2019(4) Maximov–Ekdahl; eprint.iacr.org/2026/1786.

## 8. Summary (10 lines)

1. M(n), n <= 100: FP19 (circuits dated 2016) holds n = 9..100; n = 2..8 are Bernstein 2000/2009 ties. All 99 + 63 circuits verified by us.
2. M(n), n > 100 (113, 128, 163, 233, 283, ...): Bernstein 2009, circuits downloadable; M(128) is 22 gates beatable on paper by a known recurrence.
3. GF(2^8) AES basis: 117 = 48 AND + 69 XOR, depth 6 (CMT, July 2010). Tower: 106 = 27 AND + 79 XOR (2017, basis undisclosed). Both verified.
4. GF(2^6) 57 and GF(2^7) 84/85 (CMT 2010) verified. No published total-gate record for m = 3, 4, 5, 9..16 (incl. McEliece 12, 13).
5. AES S-box: 113 {AND, XOR, XNOR} (verified exhaustively); 102 in the richer ME19 basis. GF(2^16) inversion 387.
6. Rank bounds over F2: P6 16-17, P7 19-22, P8 21-26 (Wang 2026). The brief's "22 is a lower bound for n = 7" is wrong: 22 is the upper bound.
7. Most room: M(7), M(8) and AES-basis GF(2^8) use about 2x the minimum ANDs (40/22, 48/26, 48/24). No total-gate circuit built on the rank-optimal formulas is published.
8. Weakest records: small field multipliers (none), n = 2..8 (frozen since 2009, no lower bounds), n > 100 (2009).
9. Crowding: nobody on total gates since 2019. Morse (AND counts, n5/n6) and Perminov (XOR side of bilinear schemes) are the nearest pivots.
10. All circuit files are in circuits/ with provenance and SHA-256; the verifier and tables are in lit/scripts/.
