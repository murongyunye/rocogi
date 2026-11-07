"""lua_literal.py - parse the pure-literal Lua data tables BWIKI ships in Module: pages.

The wiki's generated data modules are of the form

    -- 请勿直接修改本页面的数据。
    return {skill_000001={category="特性",energy=0,name="偏振",desc="..."}, ...}

i.e. a single `return <table>` with no control flow, so a small recursive-descent
parser is enough and we avoid shipping a Lua interpreter.
"""
import re

TOKEN = re.compile(r"""
    (?P<ws>\s+)
  | (?P<comment>--\[\[.*?\]\]|--[^\n]*)
  | (?P<str>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
  | (?P<num>-?\d+\.\d+(?:[eE][-+]?\d+)?|-?\d+(?:[eE][-+]?\d+)?)
  | (?P<name>[A-Za-z_][A-Za-z0-9_]*)
  | (?P<sym>[{}\[\]=,;()])
""", re.S | re.X)

ESCAPES = {"n": "\n", "t": "\t", "r": "\r", "\\": "\\", '"': '"', "'": "'", "0": "\0"}


def _unescape(body: str) -> str:
    out, i = [], 0
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body):
            nxt = body[i + 1]
            if nxt == "u" and body[i + 2:i + 3] == "{":
                end = body.index("}", i + 2)
                out.append(chr(int(body[i + 3:end], 16)))
                i = end + 1
                continue
            if nxt in ESCAPES:
                out.append(ESCAPES[nxt])
                i += 2
                continue
            if nxt.isdigit():
                j = i + 1
                while j < len(body) and body[j].isdigit() and j - i < 4:
                    j += 1
                out.append(chr(int(body[i + 1:j])))
                i = j
                continue
            out.append(nxt)
            i += 2
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def tokenize(text):
    pos, toks = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise ValueError(f"cannot tokenize at {pos}: {text[pos:pos + 40]!r}")
        pos = m.end()
        kind = m.lastgroup
        if kind in ("ws", "comment"):
            continue
        toks.append((kind, m.group()))
    return toks


class Parser:
    def __init__(self, toks):
        self.toks = toks
        self.i = 0

    def peek(self, offset=0):
        j = self.i + offset
        return self.toks[j] if j < len(self.toks) else (None, None)

    def take(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, sym):
        kind, val = self.take()
        if val != sym:
            raise ValueError(f"expected {sym!r}, got {val!r}")

    def parse_value(self):
        kind, val = self.peek()
        if val == "{":
            return self.parse_table()
        if kind == "str":
            self.take()
            return _unescape(val[1:-1])
        if kind == "num":
            self.take()
            return float(val) if ("." in val or "e" in val.lower()) else int(val)
        if kind == "name":
            self.take()
            if val == "true":
                return True
            if val == "false":
                return False
            if val == "nil":
                return None
            raise ValueError(f"bare name {val!r} is not a literal")
        raise ValueError(f"unexpected token {kind}:{val!r}")

    def parse_table(self):
        self.expect("{")
        positional, keyed = [], {}
        while True:
            kind, val = self.peek()
            if val == "}":
                self.take()
                break
            if val in (",", ";"):
                self.take()
                continue
            if val == "[":
                self.take()
                key = self.parse_value()
                self.expect("]")
                self.expect("=")
                keyed[key] = self.parse_value()
                continue
            if kind == "name" and self.peek(1)[1] == "=":
                key = self.take()[1]
                self.take()  # '='
                keyed[key] = self.parse_value()
                continue
            positional.append(self.parse_value())
        if keyed and positional:
            for n, v in enumerate(positional, start=1):
                keyed[n] = v
            return keyed
        if keyed:
            return keyed
        return positional


def loads(text: str):
    """Parse `-- comments\\nreturn { ... }` and return the Python value."""
    toks = tokenize(text)
    parser = Parser(toks)
    if parser.peek()[1] == "return":
        parser.take()
    value = parser.parse_value()
    return value


def loads_file(path: str):
    with open(path, encoding="utf-8") as fh:
        return loads(fh.read())


if __name__ == "__main__":
    import json
    import sys

    data = loads_file(sys.argv[1])
    print(json.dumps(data, ensure_ascii=False)[:800])
    if isinstance(data, dict):
        print(f"\n{len(data)} entries; sample key: {list(data)[0]}")
