"""Reference checker for draft-wright-verdict-record-01 (Sections 2 and 4).

Reads one test-vector file and reports the record's state and each step's result.
Signing and containers are out of scope (Section 3): the upper time bound of the
record, and of each evidence item, is a checker input supplied by the vector.

Where -01 leaves a choice open, this checker takes the reading named in
INTERPRETATIONS.md and the vector that depends on it carries the same label.
"""
import base64
import hashlib
import json
import sys

MAX_DEPTH = 32
INT_MAX = 2**53 - 1
TOP_MEMBERS = {"v", "kind", "key", "version", "supersedes", "writer", "actor",
               "act_time", "evidence", "check", "body"}
REQUIRED = {"v", "kind", "key", "version", "writer", "body"}


class ParseError(Exception):
    pass


# ---------- Section 2.1: strict JSON, canonical form ----------

def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:
            raise ParseError("duplicate member name: %s" % k)
        seen[k] = v
    return seen


def _bad_constant(name):
    raise ParseError("non-standard number: %s" % name)


def _depth(x, d=1):
    # Only objects and arrays count as levels (interpretation I-10).
    if not isinstance(x, (dict, list)):
        return
    if d > MAX_DEPTH:
        raise ParseError("nested deeper than 32 levels")
    if isinstance(x, dict):
        for v in x.values():
            _depth(v, d + 1)
    elif isinstance(x, list):
        for v in x:
            _depth(v, d + 1)


def _check_values(x):
    if isinstance(x, bool) or x is None:
        return
    if isinstance(x, float):
        raise ParseError("number is not an integer")
    if isinstance(x, int):
        if abs(x) > INT_MAX:
            raise ParseError("integer out of range")
        return
    if isinstance(x, str):
        for ch in x:
            if 0xD800 <= ord(ch) <= 0xDFFF:
                raise ParseError("lone surrogate")
        return
    if isinstance(x, dict):
        for v in x.values():
            _check_values(v)
    elif isinstance(x, list):
        for v in x:
            _check_values(v)


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _sort_key_codepoints(obj):
    # json.dumps sort_keys sorts by Python str order, which is code-point order.
    return obj


def parse_strict(b):
    if b.startswith(b"\xef\xbb\xbf"):
        raise ParseError("byte-order mark")
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise ParseError("not valid UTF-8")
    # Depth is checked on the raw text first so a deep nest cannot exhaust the parser.
    d = mx = 0
    instr = esc = False
    for ch in s:
        if instr:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                instr = False
        elif ch == '"':
            instr = True
        elif ch in "[{":
            d += 1
            mx = max(mx, d)
            if mx > MAX_DEPTH:
                raise ParseError("nested deeper than 32 levels")
        elif ch in "]}":
            d -= 1
    try:
        obj = json.loads(s, object_pairs_hook=_no_dupes, parse_constant=_bad_constant)
    except ParseError:
        raise
    except ValueError as e:
        raise ParseError("not JSON: %s" % e)
    _depth(obj)
    _check_values(obj)
    if canonical(obj) != b:
        raise ParseError("not in canonical form (re-serialization differs)")
    return obj


def sha256hex(b):
    return hashlib.sha256(b).hexdigest()


def is_hex64(s):
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


# ---------- Section 2.2: members ----------

def member_errors(r):
    """Returns a list of reasons the record breaks Section 2.2, other than check/evidence
    (which Section 2.2 sends to steps 1 and 2)."""
    errs = []
    if not isinstance(r, dict):
        return ["record is not a JSON object"]
    extra = set(r) - TOP_MEMBERS
    if extra:
        errs.append("member not allowed: %s" % ",".join(sorted(extra)))
    missing = REQUIRED - set(r)
    if missing:
        errs.append("required member missing: %s" % ",".join(sorted(missing)))
    return errs


# ---------- Section 4.5: policy ----------

def policy_valid(p):
    if not isinstance(p, dict):
        return False
    if set(p) != {"judgement_kinds", "formats", "max_depth"}:
        return False
    if not (isinstance(p["judgement_kinds"], list) and all(isinstance(k, str) for k in p["judgement_kinds"])):
        return False
    if not (isinstance(p["formats"], list) and all(isinstance(k, str) for k in p["formats"])):
        return False
    if not (is_int(p["max_depth"]) and p["max_depth"] >= 0):
        return False
    return True


# ---------- Rules held by this checker (suite-defined, Section 4.3 step 3) ----------

class RuleTypeError(Exception):
    pass


def rule_at_least(body, inputs):
    # urn:example:verdict-record:rule:at-least  (defined in RULES.md)
    if not isinstance(inputs, dict) or set(inputs) != {"value", "min"}:
        raise RuleTypeError("inputs must name value and min")
    vals = {}
    for p, m in inputs.items():
        if not isinstance(m, str) or m not in body:
            raise RuleTypeError("input %s names no member of body" % p)
        if not is_int(body[m]):
            raise RuleTypeError("input %s is not an integer" % p)
        vals[p] = body[m]
    return "pass" if vals["value"] >= vals["min"] else "fail"


RULES = {"urn:example:verdict-record:rule:at-least": rule_at_least}

TEST_FORMATS = {
    "urn:example:verdict-record:format:opaque": True,       # every item verifies
    "urn:example:verdict-record:format:never-verifies": False,
}


# ---------- Section 4: the check ----------

def check(record_bytes, ctx, depth=0):
    """ctx: policy, upper_time_bound, items {sha256: {bytes, upper_time_bound?}}.
    Returns (state, steps, reasons)."""
    steps = {1: "PASS", 2: "PASS", 3: "PASS"}
    reasons = {}

    try:
        r = parse_strict(record_bytes)
    except ParseError as e:
        return "refused", None, {"parse": str(e)}
    errs = member_errors(r)
    if errs:
        return "refused", None, {"members": "; ".join(errs)}

    pol = ctx["policy"]

    # Step 1
    c = r.get("check")
    if not isinstance(c, dict):
        steps[1] = "FAIL"; reasons[1] = "check missing or not an object"
    elif not isinstance(c.get("rule"), str) or c.get("rule") == "" or "result" not in c:
        steps[1] = "FAIL"; reasons[1] = "check must name a rule and give a result"
    elif set(c) - {"rule", "inputs", "result"}:
        steps[1] = "FAIL"; reasons[1] = "check has a member not allowed"
    elif c["rule"] == "judgement" and r.get("kind") not in pol["judgement_kinds"]:
        steps[1] = "FAIL"; reasons[1] = "judgement not allowed for kind %r by policy" % r.get("kind")

    # Step 2
    ev = r.get("evidence")
    ok_shape = isinstance(ev, list) and all(
        isinstance(e, dict) and set(e) == {"sha256", "format"} and is_hex64(e["sha256"])
        and isinstance(e["format"], str) and e["format"] != "" for e in ev)
    if not ok_shape:
        steps[2] = "FAIL"; reasons[2] = "evidence missing or an entry is malformed"
    else:
        body = r.get("body")
        claim = body.get("claim") if isinstance(body, dict) else None
        if isinstance(claim, dict) and "ref" in claim and claim["ref"] not in ev:
            steps[2] = "FAIL"; reasons[2] = "body.claim.ref does not appear in evidence"
        else:
            for i, e in enumerate(ev):
                it = ctx["items"].get(e["sha256"])
                if it is None or sha256hex(it["bytes"]) != e["sha256"]:
                    steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: item not held" % i; break
                if e["format"] not in pol["formats"]:
                    steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: format not listed by policy" % i; break
                if e["format"] == "verdict-record/1":
                    if depth + 1 > pol["max_depth"]:
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: beyond citation depth" % i; break
                    sub_ctx = dict(ctx, upper_time_bound=it.get("upper_time_bound"))
                    if sub_ctx["upper_time_bound"] is None:
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: no upper time bound for cited record" % i; break
                    st, _, _ = check(it["bytes"], sub_ctx, depth + 1)
                    if st != "released":
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: cited record is %s" % (i, st); break
                elif e["format"] in TEST_FORMATS:
                    if not TEST_FORMATS[e["format"]]:
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: does not verify" % i; break
                else:
                    steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: checker cannot verify this format" % i; break
                ub = it.get("upper_time_bound")
                if ub is not None and ub > ctx["upper_time_bound"]:
                    steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: its upper time bound is later than the record's" % i; break

    # Step 3
    if isinstance(c, dict) and isinstance(c.get("rule"), str) and c.get("rule") not in ("judgement", "") and "result" in c:
        fn = RULES.get(c["rule"])
        if fn is None:
            steps[3] = "NOT RUN"; reasons[3] = "rule specification not held: %s" % c["rule"]
        else:
            body = r.get("body")
            try:
                got = fn(body if isinstance(body, dict) else {}, c.get("inputs"))
            except RuleTypeError as e:
                steps[3] = "FAIL"; reasons[3] = "rule input: %s" % e
            else:
                if got != c["result"]:
                    steps[3] = "FAIL"; reasons[3] = "re-run gave %r, record states %r" % (got, c["result"])
    elif not (isinstance(c, dict) and isinstance(c.get("rule"), str) and c.get("rule") != "" and "result" in c):
        steps[3] = "NOT RUN"; reasons[3] = "needs a check that names a rule and gives a result"

    if "FAIL" in steps.values():
        state = "refused"
    elif "NOT RUN" in steps.values():
        state = "held"
    else:
        state = "released"
    return state, steps, reasons


def run_vector(v):
    pol_bytes = canonical(v["policy"])
    if not policy_valid(v["policy"]):
        return {"state": "no verdict", "steps": None, "reasons": {"policy": "invalid"},
                "policy_sha256": sha256hex(pol_bytes)}
    items = {}
    for it in v.get("evidence_items", []):
        b = base64.b64decode(it["b64"])
        items[sha256hex(b)] = {"bytes": b, "upper_time_bound": it.get("upper_time_bound")}
    ctx = {"policy": v["policy"], "upper_time_bound": v["upper_time_bound"], "items": items}
    st, steps, reasons = check(base64.b64decode(v["record_b64"]), ctx)
    return {"state": st, "steps": ({str(k): s for k, s in steps.items()} if steps else None), "reasons": {str(k): s for k, s in reasons.items()},
            "policy_sha256": sha256hex(pol_bytes)}


if __name__ == "__main__":
    for path in sys.argv[1:]:
        v = json.load(open(path, encoding="utf-8"))
        print(path, json.dumps(run_vector(v), ensure_ascii=False))
