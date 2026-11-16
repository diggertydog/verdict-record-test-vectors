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


class RuleNotRun(Exception):
    pass


def _json_pointer(doc, ptr):
    if not isinstance(ptr, str) or (ptr != "" and not ptr.startswith("/")):
        raise RuleTypeError("invalid JSON Pointer: %r" % (ptr,))
    if ptr == "":
        return doc
    cur = doc
    for raw_tok in ptr.split("/")[1:]:
        tok = raw_tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            if tok not in cur:
                raise RuleTypeError("pointer %r does not resolve" % ptr)
            cur = cur[tok]
        elif isinstance(cur, list):
            if not tok.isdigit() or (len(tok) > 1 and tok.startswith("0")):
                raise RuleTypeError("pointer %r array index invalid" % ptr)
            idx = int(tok)
            if idx < 0 or idx >= len(cur):
                raise RuleTypeError("pointer %r array index out of bounds" % ptr)
            cur = cur[idx]
        else:
            raise RuleTypeError("pointer %r traverses scalar" % ptr)
    return cur


def resolve_inputs(r, ctx, relied_indices, expected_keys):
    inputs = r.get("check", {}).get("inputs")
    if not isinstance(inputs, dict) or set(inputs) != expected_keys:
        raise RuleTypeError("inputs must name %s" % ",".join(sorted(expected_keys)))
    body = r.get("body") if isinstance(r.get("body"), dict) else {}
    ev = r.get("evidence") if isinstance(r.get("evidence"), list) else []
    vals = {}
    not_run_reasons = []
    type_errors = []
    for k in sorted(inputs):
        spec = inputs[k]
        if isinstance(spec, str):
            if spec not in body:
                type_errors.append("input %s names no member of body" % k)
            else:
                vals[k] = body[spec]
        elif isinstance(spec, dict):
            if not ("evidence" in spec and set(spec) <= {"evidence", "pointer"} and is_int(spec["evidence"])):
                type_errors.append("input %s binding object malformed" % k)
                continue
            idx = spec["evidence"]
            if idx < 0 or idx >= len(ev):
                type_errors.append("input %s evidence index out of range" % k)
                continue
            if idx not in relied_indices:
                not_run_reasons.append(k)
                continue
            ent = ev[idx]
            it = ctx["items"].get(ent["sha256"])
            if "pointer" not in spec:
                vals[k] = sha256hex(it["bytes"])
            else:
                try:
                    # Section 2.2: parsed as strict JSON by Section 2.1; need not be canonical.
                    s = it["bytes"].decode("utf-8")
                    if it["bytes"].startswith(b"\xef\xbb\xbf"):
                        raise ParseError("BOM")
                    doc = json.loads(s, object_pairs_hook=_no_dupes, parse_constant=_bad_constant)
                    _depth(doc)
                    _check_values(doc)
                    vals[k] = _json_pointer(doc, spec["pointer"])
                except (UnicodeDecodeError, ValueError, ParseError, RuleTypeError) as e:
                    type_errors.append("input %s: %s" % (k, e))
        else:
            type_errors.append("input %s binding has wrong type" % k)
    # Section 4.3 step 3: "If one input cannot be read for the first reason [NOT RUN]
    # and another for the second [FAIL], the step FAILs."
    if type_errors:
        raise RuleTypeError("; ".join(type_errors))
    if not_run_reasons:
        raise RuleNotRun("missing or unrelied evidence for input(s): %s" % ", ".join(not_run_reasons))
    return vals


def rule_at_least(r, ctx, relied_indices):
    vals = resolve_inputs(r, ctx, relied_indices, {"value", "min"})
    for p in ("value", "min"):
        if not is_int(vals[p]):
            raise RuleTypeError("input %s is not an integer" % p)
    return "pass" if vals["value"] >= vals["min"] else "fail"


def rule_hop_continuity_attenuation(r, ctx, relied_indices):
    # Appendix A.2 (-02): urn:example:verdict-record:rule:hop-continuity-attenuation:v1
    vals = resolve_inputs(r, ctx, relied_indices,
                          {"parent_hash", "parent_digest", "parent_scopes", "child_scopes"})
    if not (isinstance(vals["parent_hash"], str) and isinstance(vals["parent_digest"], str)):
        raise RuleTypeError("parent_hash and parent_digest must be strings")
    for sname in ("parent_scopes", "child_scopes"):
        arr = vals[sname]
        if not (isinstance(arr, list) and all(isinstance(x, str) for x in arr)):
            raise RuleTypeError("%s must be an array of strings" % sname)
    linked = (vals["parent_hash"] == vals["parent_digest"])
    attenuated = all(s in vals["parent_scopes"] for s in vals["child_scopes"])
    return "attenuated_and_linked" if (linked and attenuated) else "not_attenuated_or_not_linked"


RULES = {
    "urn:example:verdict-record:rule:at-least": rule_at_least,
    "urn:example:verdict-record:rule:hop-continuity-attenuation:v1": rule_hop_continuity_attenuation,
    "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/#rule-hop-continuity-attenuation-v1": rule_hop_continuity_attenuation,
}

TEST_FORMATS = {
    "urn:example:verdict-record:format:opaque": True,       # every item verifies
    "urn:example:verdict-record:format:never-verifies": False,
    "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/": True,  # Appendix A.2 unsigned hop test format
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
            relied_indices = set()
            for i, e in enumerate(ev):
                it = ctx["items"].get(e["sha256"])
                if it is None or sha256hex(it["bytes"]) != e["sha256"]:
                    if steps[2] == "PASS":
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: item not held" % i
                    continue
                if e["format"] not in pol["formats"]:
                    if steps[2] == "PASS":
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: format not listed by policy" % i
                    continue
                if e["format"] == "verdict-record/1":
                    if depth + 1 > pol["max_depth"]:
                        if steps[2] == "PASS":
                            steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: beyond citation depth" % i
                        continue
                    sub_ctx = dict(ctx, upper_time_bound=it.get("upper_time_bound"))
                    if sub_ctx["upper_time_bound"] is None:
                        if steps[2] == "PASS":
                            steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: no upper time bound for cited record" % i
                        continue
                    st, _, _ = check(it["bytes"], sub_ctx, depth + 1)
                    if st != "released":
                        if steps[2] == "PASS":
                            steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: cited record is %s" % (i, st)
                        continue
                elif e["format"] in TEST_FORMATS:
                    if not TEST_FORMATS[e["format"]]:
                        if steps[2] == "PASS":
                            steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: does not verify" % i
                        continue
                else:
                    if steps[2] == "PASS":
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: checker cannot verify this format" % i
                    continue
                ub = it.get("upper_time_bound")
                if ub is not None and ub > ctx["upper_time_bound"]:
                    if steps[2] == "PASS":
                        steps[2] = "NOT RUN"; reasons[2] = "evidence[%d]: its upper time bound is later than the record's" % i
                    continue
                relied_indices.add(i)

    # Step 3
    if not isinstance(ev, list) or not ok_shape or (isinstance(claim, dict) and "ref" in claim and claim["ref"] not in ev):
        relied_indices = set()
    if isinstance(c, dict) and isinstance(c.get("rule"), str) and c.get("rule") not in ("judgement", "") and "result" in c:
        fn = RULES.get(c["rule"])
        if fn is None:
            steps[3] = "NOT RUN"; reasons[3] = "rule specification not held: %s" % c["rule"]
        else:
            try:
                got = fn(r, ctx, relied_indices)
            except RuleNotRun as e:
                steps[3] = "NOT RUN"; reasons[3] = "rule input: %s" % e
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
