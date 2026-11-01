# Only the file-pattern and output-name lines were changed from the original, to fit the flat repository layout.
#!/usr/bin/env python3
"""Independent checker for draft-wright-verdict-record-01 (Sections 2.1-2.3, 4).

Written from the draft text and blind/README.md only. Numbered readings (R#)
refer to blind/impl/readings.md.
"""
import base64
import glob
import hashlib
import json
import os
import re
import sys

MAX_DEPTH = 32
INT_MAX = 2 ** 53 - 1
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
TIME_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z\Z")

FMT_OPAQUE = "urn:example:verdict-record:format:opaque"
FMT_NEVER = "urn:example:verdict-record:format:never-verifies"
FMT_VR = "verdict-record/1"
RULE_AT_LEAST = "urn:example:verdict-record:rule:at-least"
KNOWN_FORMATS = {FMT_OPAQUE, FMT_NEVER, FMT_VR}
KNOWN_RULES = {RULE_AT_LEAST}

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT RUN"


class Refuse(Exception):
    pass


# ---------------------------------------------------------------- 2.1 parsing
class _Parser:
    def __init__(self, text):
        self.s = text
        self.i = 0

    def err(self, msg):
        raise Refuse("parse: %s at %d" % (msg, self.i))

    def peek(self):
        return self.s[self.i] if self.i < len(self.s) else ""

    def value(self, depth):
        c = self.peek()
        if c == "{":
            return self.obj(depth + 1)
        if c == "[":
            return self.arr(depth + 1)
        if c == '"':
            return self.string()
        if c == "-" or c.isdigit():
            return self.number()
        for lit, val in (("true", True), ("false", False), ("null", None)):
            if self.s.startswith(lit, self.i):
                self.i += len(lit)
                return val
        self.err("unexpected character")

    def obj(self, depth):
        if depth > MAX_DEPTH:
            self.err("nesting deeper than 32")  # R2
        self.i += 1
        out = {}
        if self.peek() == "}":
            self.i += 1
            return out
        while True:
            if self.peek() != '"':
                self.err("expected member name")
            k = self.string()
            if k in out:
                self.err("duplicate member name %r" % k)
            if self.peek() != ":":
                self.err("expected colon")
            self.i += 1
            out[k] = self.value(depth)
            c = self.peek()
            self.i += 1
            if c == "}":
                return out
            if c != ",":
                self.err("expected , or }")

    def arr(self, depth):
        if depth > MAX_DEPTH:
            self.err("nesting deeper than 32")
        self.i += 1
        out = []
        if self.peek() == "]":
            self.i += 1
            return out
        while True:
            out.append(self.value(depth))
            c = self.peek()
            self.i += 1
            if c == "]":
                return out
            if c != ",":
                self.err("expected , or ]")

    def string(self):
        self.i += 1
        buf = []
        while True:
            if self.i >= len(self.s):
                self.err("unterminated string")
            c = self.s[self.i]
            if c == '"':
                self.i += 1
                return "".join(buf)
            if ord(c) < 0x20:
                self.err("raw control character in string")
            if c != "\\":
                buf.append(c)
                self.i += 1
                continue
            e = self.s[self.i + 1:self.i + 2]
            simple = {'"': '"', "\\": "\\", "/": "/", "b": "\b", "f": "\f",
                      "n": "\n", "r": "\r", "t": "\t"}
            if e in simple:
                buf.append(simple[e])
                self.i += 2
                continue
            if e != "u":
                self.err("bad escape")
            cp = self._hex4(self.i + 2)
            self.i += 6
            if 0xD800 <= cp <= 0xDBFF:
                if self.s[self.i:self.i + 2] != "\\u":
                    self.err("lone surrogate")
                lo = self._hex4(self.i + 2)
                if not 0xDC00 <= lo <= 0xDFFF:
                    self.err("lone surrogate")
                self.i += 6
                cp = 0x10000 + ((cp - 0xD800) << 10) + (lo - 0xDC00)
            elif 0xDC00 <= cp <= 0xDFFF:
                self.err("lone surrogate")
            buf.append(chr(cp))

    def _hex4(self, at):
        h = self.s[at:at + 4]
        if not re.fullmatch(r"[0-9a-fA-F]{4}", h):
            self.err("bad \\u escape")
        return int(h, 16)

    def number(self):
        m = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?").match(self.s, self.i)
        if not m or m.end() == self.i:
            self.err("bad number")
        if m.group(2) or m.group(3):
            self.err("number is not an integer")  # R3
        self.i = m.end()
        v = int(m.group(0))
        if abs(v) > INT_MAX:
            self.err("integer out of range")
        return v


def _canon_str(s):
    out = ['"']
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif o < 0x20:  # R4
            out.append({8: "\\b", 9: "\\t", 10: "\\n", 12: "\\f", 13: "\\r"}.get(o, "\\u%04x" % o))
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def canon(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, str):
        return _canon_str(v)
    if isinstance(v, list):
        return "[" + ",".join(canon(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{" + ",".join(_canon_str(k) + ":" + canon(v[k]) for k in sorted(v)) + "}"
    raise TypeError(type(v))


def parse_strict(b):
    """Section 2.1: strict canonical JSON. Raises Refuse."""
    if b.startswith(b"\xef\xbb\xbf"):
        raise Refuse("parse: byte-order mark")
    try:
        text = b.decode("utf-8", errors="strict")
    except UnicodeDecodeError as e:
        raise Refuse("parse: invalid UTF-8 (%s)" % e)
    p = _Parser(text)
    v = p.value(0)
    if p.i != len(text):
        raise Refuse("parse: trailing bytes")
    if canon(v).encode("utf-8") != b:
        raise Refuse("parse: re-serialization differs (not canonical)")
    return v


# ------------------------------------------------------- 2.2/2.3 members (R5)
ALLOWED = {"v", "kind", "key", "version", "supersedes", "writer", "actor",
           "act_time", "evidence", "check", "body"}
REQUIRED = {"v", "kind", "key", "version", "writer", "body"}


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_entry(e):
    return (isinstance(e, dict) and set(e) == {"sha256", "format"}
            and isinstance(e["sha256"], str) and HEX64.match(e["sha256"])
            and isinstance(e["format"], str))


def check_members(r):
    if not isinstance(r, dict):
        raise Refuse("members: record is not an object")
    extra = set(r) - ALLOWED
    if extra:
        raise Refuse("members: member(s) not allowed: %s" % sorted(extra))
    missing = REQUIRED - set(r)
    if missing:
        raise Refuse("members: required member(s) missing: %s" % sorted(missing))
    # Members that no step of Section 4.3 reads are type-checked here (R5).
    if r["v"] != "verdict-record/1":
        raise Refuse("members: v is not verdict-record/1")
    if not isinstance(r["kind"], str):
        raise Refuse("members: kind is not a string")
    if not (isinstance(r["key"], str) and r["key"]):
        raise Refuse("members: key is not a non-empty string")
    if not (is_int(r["version"]) and r["version"] >= 1):
        raise Refuse("members: version is not an integer of 1 or more")
    if not (isinstance(r["writer"], str) and r["writer"]):
        raise Refuse("members: writer is not a non-empty string")
    if "supersedes" in r:
        s = r["supersedes"]
        if r["version"] == 1 and s is not None:
            raise Refuse("members: supersedes must be null for version 1")
        if r["version"] > 1 and not (isinstance(s, str) and HEX64.match(s)):
            raise Refuse("members: supersedes must be a digest for version > 1")
    if "act_time" in r and not (isinstance(r["act_time"], str) and TIME_RE.match(r["act_time"])):
        raise Refuse("members: act_time is not a time")
    if "actor" in r:
        a = r["actor"]
        if not isinstance(a, dict) or a.get("type") not in ("person", "system"):
            raise Refuse("members: actor malformed")
        want = {"type", "id"} | ({"model", "model_version"} if a["type"] == "system" else set())
        if set(a) != want:
            raise Refuse("members: actor members wrong")
    if not isinstance(r["body"], dict):
        raise Refuse("members: body is not an object")
    # 2.3 the claim (R6)
    c = r["body"].get("claim")
    if not (isinstance(c, dict) and len(c) == 1 and
            (("text" in c and isinstance(c["text"], str)) or ("ref" in c and is_entry(c["ref"])))):
        raise Refuse("claim: body.claim is not an object with exactly one of text/ref")
    if "ref" in c:
        ev = r.get("evidence")
        if not (isinstance(ev, list) and c["ref"] in ev):
            raise Refuse("claim: body.claim.ref does not appear in evidence")


# ---------------------------------------------------------------- policy 4.5
def policy_valid(p):
    return (isinstance(p, dict) and set(p) == {"judgement_kinds", "formats", "max_depth"}
            and isinstance(p["judgement_kinds"], list)
            and all(isinstance(x, str) for x in p["judgement_kinds"])
            and isinstance(p["formats"], list)
            and all(isinstance(x, str) for x in p["formats"])
            and is_int(p["max_depth"]) and p["max_depth"] >= 0)


# --------------------------------------------------------------- 4.3 steps
def json_eq(a, b):
    """Type-aware equality (Python treats True == 1)."""
    if type(a) is not type(b):
        return False
    if isinstance(a, list):
        return len(a) == len(b) and all(json_eq(x, y) for x, y in zip(a, b))
    if isinstance(a, dict):
        return set(a) == set(b) and all(json_eq(a[k], b[k]) for k in a)
    return a == b


def step1(r, policy):
    if "check" not in r:
        return FAIL, "check member absent"
    c = r["check"]
    if not isinstance(c, dict):
        return FAIL, "check is not an object"
    if set(c) - {"rule", "inputs", "result"}:
        return FAIL, "check has members other than rule/inputs/result"  # R7
    if not isinstance(c.get("rule"), str) or not c["rule"]:
        return FAIL, "check.rule missing or not a string"
    if "result" not in c:
        return FAIL, "check.result missing"
    if "inputs" in c and not isinstance(c["inputs"], dict):
        return FAIL, "check.inputs is not an object"
    if c["rule"] == "judgement" and r["kind"] not in policy["judgement_kinds"]:
        return FAIL, "rule judgement not allowed for kind %r by policy" % r["kind"]
    return PASS, None


def step2(r, ctx, depth, utb, readings):
    if "evidence" not in r:
        return FAIL, "evidence member absent"
    ev = r["evidence"]
    if not isinstance(ev, list):
        return FAIL, "evidence is not an array"
    for i, e in enumerate(ev):
        if not is_entry(e):
            readings.add(8)
            return FAIL, "evidence[%d] is not an entry as in Section 2.2" % i
    if not ev:
        readings.add(9)
    not_run = []
    for i, e in enumerate(ev):
        item = ctx["items"].get(e["sha256"])
        if item is None:
            not_run.append("evidence[%d] %s: item not held" % (i, e["sha256"][:12]))
            continue
        if e["format"] not in ctx["policy"]["formats"]:
            not_run.append("evidence[%d]: format %r not listed by policy" % (i, e["format"]))
            continue
        ok, why = verify_item(item, e["format"], ctx, depth, readings)
        if not ok:
            not_run.append("evidence[%d]: does not verify (%s)" % (i, why))
            continue
        iub = item.get("upper_time_bound")
        if iub is not None:
            readings.add(11)
        if iub is not None and iub > utb:  # R11 (fixed-width UTC strings)
            not_run.append("evidence[%d]: item upper time bound %s later than %s" % (i, iub, utb))
    if not_run:
        return NOT_RUN, "; ".join(not_run)
    return PASS, None


def verify_item(item, fmt, ctx, depth, readings):
    if fmt == FMT_OPAQUE:
        return True, None
    if fmt == FMT_NEVER:
        return False, "format never verifies"
    if fmt == FMT_VR:
        readings.add(10)
        if depth + 1 > ctx["policy"]["max_depth"]:
            return False, "citation depth %d beyond policy max_depth %d" % (depth + 1, ctx["policy"]["max_depth"])
        if item.get("upper_time_bound") is None:
            readings.add(12)
            return False, "nested record has no upper time bound"
        sub = check_record(item["bytes"], item["upper_time_bound"], ctx, depth + 1)
        readings |= set(sub["readings"])
        if sub["state"] != "released":
            return False, "nested record state %s" % sub["state"]
        return True, None
    return False, "checker holds no specification for format %r" % fmt  # R13


def step3(r, readings):
    c = r.get("check")
    if not isinstance(c, dict) or not isinstance(c.get("rule"), str):
        readings.add(14)
        return NOT_RUN, "needs check.rule"
    rule = c["rule"]
    if rule == "judgement":
        readings.add(15)
        return PASS, None
    if rule not in KNOWN_RULES:
        return NOT_RUN, "needs specification of rule %r" % rule
    if "result" not in c:
        readings.add(14)
        return NOT_RUN, "needs check.result"
    inp = c.get("inputs")
    body = r["body"]
    if not (isinstance(inp, dict) and set(inp) == {"value", "min"}
            and isinstance(inp["value"], str) and isinstance(inp["min"], str)):
        readings.add(16)
        return FAIL, "check.inputs not as the rule requires"
    val, mn = body.get(inp["value"]), body.get(inp["min"])
    if not (is_int(val) and is_int(mn)):
        if inp["value"] not in body or inp["min"] not in body:
            readings.add(16)
        return FAIL, "rule input of the wrong JSON type"
    got = "pass" if val >= mn else "fail"
    if not json_eq(got, c["result"]):
        return FAIL, "re-run gave %r, check.result is %r" % (got, c["result"])
    return PASS, None


def _depth(v):
    if isinstance(v, dict):
        return 1 + max([_depth(x) for x in v.values()] or [0])
    if isinstance(v, list):
        return 1 + max([_depth(x) for x in v] or [0])
    return 0


def check_record(b, utb, ctx, depth=0):
    readings = set()
    try:
        r = parse_strict(b)
        check_members(r)
    except Refuse as e:
        readings.add(1)
        m = str(e)
        if "nesting" in m: readings.add(2)
        if "not an integer" in m: readings.add(3)
        if m.startswith("members:"): readings.add(5)
        if m.startswith("claim:"): readings.add(6)
        return {"state": "refused", "steps": None, "readings": sorted(readings), "why": [str(e)]}
    if _depth(r) == MAX_DEPTH:
        readings.add(2)
    res = [step1(r, ctx["policy"]), step2(r, ctx, depth, utb, readings), step3(r, readings)]
    steps = [s for s, _ in res]
    why = ["step %d %s: %s" % (i + 1, s, w) for i, (s, w) in enumerate(res) if s != PASS]
    if FAIL in steps:
        state = "refused"
    elif NOT_RUN in steps:
        state = "held"
    else:
        state = "released"
    return {"state": state, "steps": steps, "readings": sorted(readings), "why": why}


def run_vector(v):
    readings = set()
    policy = v.get("policy")
    if not policy_valid(policy):
        return {"state": "no verdict", "steps": None, "readings": [], "why": ["policy invalid"]}
    utb = v["upper_time_bound"]
    if not (isinstance(utb, str) and TIME_RE.match(utb)):
        return {"state": "held", "steps": None, "readings": [17], "why": ["no upper time bound"]}
    items = {}
    for it in v["evidence_items"]:
        bts = base64.b64decode(it["b64"])
        items[hashlib.sha256(bts).hexdigest()] = {"bytes": bts, "upper_time_bound": it.get("upper_time_bound")}
    ctx = {"policy": policy, "items": items}
    out = check_record(base64.b64decode(v["record_b64"]), utb, ctx, 0)
    return out


def main(vec_dir, out_dir):
    results = []
    for f in sorted(glob.glob(os.path.join(vec_dir, "[a-f][0-9][0-9]-*.json"))):
        with open(f, "rb") as fh:
            v = json.loads(fh.read())
        r = run_vector(v)
        results.append({"name": v["name"], "state": r["state"], "steps": r["steps"],
                        "readings": r["readings"]})
        print("%-4s %-10s %-28s R%s  %s" % (v["name"], r["state"], r["steps"], r["readings"], " | ".join(r["why"])))
    with open(os.path.join(out_dir, "blind-checker-results.json"), "w") as fh:
        json.dump(results, fh, indent=1)
        fh.write("\n")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
