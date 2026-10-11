"""One internal format for fan-in-2 AND/XOR circuits (optionally XNOR and NOT), plus parsers for the CMT
(Peralta) and Bernstein bbe text formats.

Downloaded circuit files are DATA: they are read line by line with regular expressions and never executed.

Internal format (class Circuit):
  signals 0 .. na-1        are a_0 .. a_{na-1}
  signals na .. na+nb-1    are b_0 .. b_{nb-1}
  signal  na+nb+i          is gate i = (op, x, y) with op in AND, XOR, XNOR, NOT (y = None for NOT) and x, y < that signal
  outputs[k]               is the signal holding output coefficient k (c_k)
Output aliases such as "h0 = t25" or "C4 = T108" cost nothing; they only name an output.

JSON form: {"na":.., "nb":.., "gates":[[op,x,y],..], "outputs":[..], "meta":{..}}

CLI:  python3 circuit.py FILE [FILE ...]      prints gate counts by type and depth
"""
import gzip
import json
import re
import sys

OPS = ("AND", "XOR", "XNOR", "NOT")
_OPMAP = {"x": "AND", "*": "AND", "&": "AND", "AND": "AND",
          "+": "XOR", "^": "XOR", "XOR": "XOR", "XNOR": "XNOR", "#": "XNOR"}
_NAME = r"[A-Za-z_]\w*"
_BIN = re.compile(rf"^\s*({_NAME})\s*=\s*({_NAME})\s*(x|\*|&|\+|\^|#|AND|XOR|XNOR)\s*({_NAME})\s*(?://.*)?$")
_NOT = re.compile(rf"^\s*({_NAME})\s*=\s*(?:NOT|~|!)\s*\(?\s*({_NAME})\s*\)?\s*$")
_ALIAS = re.compile(rf"^\s*({_NAME})\s*=\s*({_NAME})\s*$")
# Input and output names used by the formats we read: A/a/f/U for the first operand, B/b/g for the second,
# C/c/h for outputs. A name like "x" is never an input (it is the AND token in CMT files).
_IN_A = re.compile(r"^(?:A|a|f)(\d+)$")
_IN_B = re.compile(r"^(?:B|b|g)(\d+)$")
_OUT = re.compile(r"^(?:C|c|h)(\d+)$")


class Circuit:
    def __init__(self, na, nb, gates, outputs, meta=None):
        self.na, self.nb = na, nb
        self.gates = [tuple(g) for g in gates]
        self.outputs = list(outputs)
        self.meta = dict(meta or {})

    @property
    def nin(self):
        return self.na + self.nb

    def copy(self):
        return Circuit(self.na, self.nb, list(self.gates), list(self.outputs), dict(self.meta))

    def check_wellformed(self):
        n = self.nin
        for i, (op, x, y) in enumerate(self.gates):
            s = n + i
            assert op in OPS, op
            assert 0 <= x < s, (i, x)
            if op == "NOT":
                assert y is None
            else:
                assert y is not None and 0 <= y < s, (i, y)
        for o in self.outputs:
            assert o is not None and 0 <= o < n + len(self.gates), o
        return True

    def counts(self):
        c = {op: 0 for op in OPS}
        for g in self.gates:
            c[g[0]] += 1
        c["total"] = len(self.gates)
        c["live"] = len(self.live_gates())
        c["depth"] = self.depth()
        return c

    def depth(self):
        n = self.nin
        d = [0] * (n + len(self.gates))
        for i, (op, x, y) in enumerate(self.gates):
            d[n + i] = 1 + max(d[x], d[y] if y is not None else 0)
        return max((d[o] for o in self.outputs), default=0)

    def live_gates(self):
        n = self.nin
        live = set()
        stack = [o for o in self.outputs if o >= n]
        while stack:
            s = stack.pop()
            if s in live:
                continue
            live.add(s)
            op, x, y = self.gates[s - n]
            for p in (x, y):
                if p is not None and p >= n:
                    stack.append(p)
        return sorted(live)

    def prune(self):
        """Drop dead gates and renumber. Never adds gates; keeps every output function."""
        n = self.nin
        live = set(self.live_gates())
        remap = {s: s for s in range(n)}
        gates = []
        for i, (op, x, y) in enumerate(self.gates):
            if n + i in live:
                remap[n + i] = n + len(gates)
                gates.append((op, remap[x], None if y is None else remap[y]))
        return Circuit(self.na, self.nb, gates, [remap[o] for o in self.outputs], self.meta)

    def to_json(self):
        return {"na": self.na, "nb": self.nb, "gates": [list(g) for g in self.gates],
                "outputs": self.outputs, "meta": self.meta}

    @staticmethod
    def from_json(d):
        return Circuit(d["na"], d["nb"], [tuple(g) for g in d["gates"]], d["outputs"], d.get("meta"))

    def to_text(self):
        """Plain SLP text in the CMT style (a_i, b_j inputs, t_k gates, c_k outputs). Readable by parse_text."""
        n = self.nin

        def nm(s):
            if s < self.na:
                return f"a{s}"
            if s < n:
                return f"b{s - self.na}"
            return f"t{s - n + 1}"
        sym = {"AND": "x", "XOR": "+", "XNOR": "#"}
        lines = [f"# {len(self.gates)} gates, na={self.na} nb={self.nb}, {len(self.outputs)} outputs"]
        for i, (op, x, y) in enumerate(self.gates):
            if op == "NOT":
                lines.append(f"t{i + 1} = NOT {nm(x)}")
            else:
                lines.append(f"t{i + 1} = {nm(x)} {sym[op]} {nm(y)}")
        for k, o in enumerate(self.outputs):
            lines.append(f"c{k} = {nm(o)}")
        return "\n".join(lines) + "\n"


def _read(path):
    if str(path).endswith(".gz"):
        with gzip.open(path, "rt") as f:
            return f.read()
    with open(path) as f:
        return f.read()


def parse_text(text, meta=None):
    """Parse CMT / Bernstein / our own SLP text. Lines that are not assignments (headers, prose, the
    'Begin'/'end' markers, comments) are ignored; an assignment line that does not parse is an error."""
    env = {}            # name -> ('a', i) | ('b', j) | ('g', gate index)
    raw = []            # (dest, op, x, y)
    for ln, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(("#", "//")) or "=" not in s:
            continue
        m = _BIN.match(s)
        if m:
            d, x, op, y = m.groups()
            raw.append((d, _OPMAP[op], x, y))
            continue
        m = _NOT.match(s)
        if m:
            raw.append((m.group(1), "NOT", m.group(2), None))
            continue
        m = _ALIAS.match(s)
        if m:
            raw.append((m.group(1), "ALIAS", m.group(2), None))
            continue
        # prose lines with '=' (e.g. "//verified 1011 * 1101 = 1111") are skipped only when they start a comment
        if re.match(rf"^\s*{_NAME}\s*=", s) and not s.startswith("//"):
            raise ValueError(f"line {ln}: cannot parse assignment: {line!r}")
    # input sizes from names that are read before being defined
    defined = set()
    amax = bmax = -1
    for d, op, x, y in raw:
        for v in (x, y):
            if v is None or v in defined:
                continue
            ma, mb = _IN_A.match(v), _IN_B.match(v)
            if ma:
                amax = max(amax, int(ma.group(1)))
            elif mb:
                bmax = max(bmax, int(mb.group(1)))
            else:
                raise ValueError(f"name {v!r} read before definition and not an input")
        defined.add(d)
    na, nb = amax + 1, bmax + 1
    for i in range(na):
        for nm in ("A", "a", "f"):
            env[f"{nm}{i}"] = i
    for j in range(nb):
        for nm in ("B", "b", "g"):
            env[f"{nm}{j}"] = na + j
    gates, outs = [], {}
    for d, op, x, y in raw:
        if op == "ALIAS":
            sig = env[x]
        elif op == "NOT":
            gates.append(("NOT", env[x], None))
            sig = na + nb + len(gates) - 1
        else:
            gates.append((op, env[x], env[y]))
            sig = na + nb + len(gates) - 1
        env[d] = sig
        mo = _OUT.match(d)
        if mo:
            outs[int(mo.group(1))] = sig
    if not outs:
        raise ValueError("no outputs (C/c/h names) found")
    nout = max(outs) + 1
    missing = [k for k in range(nout) if k not in outs]
    if missing:
        raise ValueError(f"outputs missing: {missing}")
    c = Circuit(na, nb, gates, [outs[k] for k in range(nout)], meta)
    c.check_wellformed()
    return c


def load(path):
    """Load a circuit from our JSON or from any supported text format."""
    p = str(path)
    if p.endswith(".json"):
        with open(p) as f:
            return Circuit.from_json(json.load(f))
    c = parse_text(_read(p), {"source": p})
    return c


def main(argv):
    for p in argv:
        c = load(p)
        print(p, f"na={c.na} nb={c.nb} outputs={len(c.outputs)}", c.counts())


if __name__ == "__main__":
    main(sys.argv[1:])
