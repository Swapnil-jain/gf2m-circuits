# Circuit files: provenance (lit-records, 2026-10-11)

All files were fetched with curl as DATA and never executed. Parsed only by our own regex parser
(lit/scripts/slpcheck.py), which accepts lines of the form `x = y op z` / `x = y`.

| dir | origin URL | what | fetched |
|---|---|---|---|
| bernstein_bbe251/ | https://binary.cr.yp.to/bbe251/<n>.gz, n = 1..64, 113, 128, 131, 163, 193, 233, 251, 256, 283; m.html, type2.html, linearmod2.html | Bernstein straight-line code behind binary.cr.yp.to/m.html (page version 2009.05.31) | 2026-10-11 |
| peralta_cmt/ | https://www.cs.yale.edu/homes/peralta/CircuitStuff/<file> (CMT.html) | CMT field multipliers (slp_630, slp_740, slp_730, slp_84310 = AES 117, GF256mult.s106.d6 = tower 106), GF(2^16) mult and inversion, AES S-box SLPs, M(10/11/12/15) SLPs, BinPolMult.tar.gz (= Find–Peralta 2019 Table 5 circuits, n = 2..100, files dated 2016-04-27, README 2018-06-13), extracted copy in BinPolMult_extracted/ | 2026-10-11 |
| maximov_ekdahl_2019/ | https://tches.iacr.org/index.php/TCHES/article/download/8346/7695 | TCHES 2019(4) paper; S-box circuits are text listings in Appendix D (bonus 102-gate forward S-box) | 2026-10-11 |
| cmt/ | (copies of 4 CMT circuit files, from the CMT page) | | |
