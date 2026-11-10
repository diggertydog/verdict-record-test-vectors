"""Reference checker for draft-wright-verdict-record-02 (Sections 2, 3 and 4).

This file is the text of draft-wright-verdict-record-02 made executable. Each duty the draft gives a checker
carries its id (D01 ...) and the line of the published -02 text it comes from, as
https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt numbers them (md5 e02052750dc143f4aaea2d56abcfc5dc).
DUTIES.md lists every duty with the vector that shows it.

What this checker holds besides the draft -- rule specifications, format rules and container rules -- is not
written into it. Each is a separate module under held/, given to the checker as an input (Section 4.2: the rule
specifications and trust anchors a checker holds are its own inputs), and each names its published source by commit.
The report lists what was held, so a rule's author can see exactly which reading of the rule ran.

Where -02 leaves a choice open, the choice is marked READING with the open point it rests on (README, "Open points"),
where the reading is stated in one sentence.

Signing and containers: the vectors supply the record's upper time bound directly (Section 3 leaves containers to the
container). A presenter that holds a container hands it in with a held container rule; see check_container.
"""
import base64
import datetime
import hashlib
import importlib.util
import json
import os
import re
import sys

DRAFT = "draft-wright-verdict-record-02"
MAX_DEPTH = 32                       # D03, -02 line 207
INT_MAX = 2**53 - 1                  # D04, -02 lines 211-213
TOP_MEMBERS = {"v", "kind", "key", "version", "supersedes", "writer", "actor",
               "act_time", "evidence", "check", "body"}                      # D10, -02 lines 235-236
REQUIRED = {"v", "kind", "key", "version", "writer", "body"}                  # D10, -02 lines 236-237
TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")       # D05, -02 lines 213-214
VERDICT_FORMAT = "verdict-record/1"                                         # -02 lines 576-577
FORBIDDEN_WORDS = ("verified", "valid", "true", "trusted", "correct", "proven", "confirmed", "ok")  # D39, -02 l. 453-455


class ParseError(Exception):
    pass


# ======================================================================= Section 2.1: strict JSON, canonical form

def _no_dupes(pairs):
    seen = {}
    for k, v in pairs:
        if k in seen:                                   # D02, -02 lines 205-206: no member name twice at any depth
            raise ParseError("Section 2.1: duplicate member name: %s" % k)
        seen[k] = v
    return seen


def _bad_constant(name):
    raise ParseError("Section 2.1: non-standard number: %s" % name)


def _check_depth_text(s):
    # D03, -02 lines 206-209: refuse nesting deeper than 32; the record is level 1, each object or array adds one.
    # Checked on the raw text first so that a deep nest cannot exhaust the parser.
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
                raise ParseError("Section 2.1: nested deeper than 32 levels")
        elif ch in "]}":
            d -= 1


def _check_strings(x):
    # D02, -02 line 206: no escape forms a lone surrogate.
    if isinstance(x, str):
        for ch in x:
            if 0xD800 <= ord(ch) <= 0xDFFF:
                raise ParseError("Section 2.1: lone surrogate")
    elif isinstance(x, dict):
        for k, v in x.items():
            _check_strings(k)
            _check_strings(v)
    elif isinstance(x, list):
        for v in x:
            _check_strings(v)


def _check_numbers(x):
    # D04, -02 lines 201 and 211-213: numbers are integers, between -(2^53 - 1) and 2^53 - 1.
    if isinstance(x, bool) or x is None:
        return
    if isinstance(x, float):
        raise ParseError("Section 2.1: number is not an integer")
    if isinstance(x, int):
        if abs(x) > INT_MAX:
            raise ParseError("Section 2.1: integer out of range")
    elif isinstance(x, dict):
        for v in x.values():
            _check_numbers(v)
    elif isinstance(x, list):
        for v in x:
            _check_numbers(v)


def canonical(obj):
    # D01, -02 lines 196-201: members sorted by code point (Python str order), no whitespace, only the quotation mark,
    # reverse solidus and control characters escaped, everything else as UTF-8 bytes.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def parse_strict_json(b):
    """Strict JSON by the rules of Section 2.1 (D02, D03): valid UTF-8, no byte-order mark, no member name twice,
    no lone surrogate, no deeper than 32 levels. This is what Section 2.2 asks of an evidence item a pointer reads
    (-02 lines 296-298): the item need not be canonical.
    READING (open point O-12): the integer rule of Section 2.1 is applied to the verdict record, not to an evidence
    item read by pointer; -02 line 297 says 'strict JSON by the rules of Section 2.1' and the integer rule is a rule
    of the record's canonical form."""
    if b.startswith(b"\xef\xbb\xbf"):
        raise ParseError("Section 2.1: byte-order mark")
    try:
        s = b.decode("utf-8")
    except UnicodeDecodeError:
        raise ParseError("Section 2.1: not valid UTF-8")
    _check_depth_text(s)
    try:
        obj = json.loads(s, object_pairs_hook=_no_dupes, parse_constant=_bad_constant)
    except ParseError:
        raise
    except (ValueError, RecursionError) as e:
        raise ParseError("Section 2.1: not JSON: %s" % e)
    _check_strings(obj)
    return obj


def parse_record(b):
    obj = parse_strict_json(b)
    _check_numbers(obj)
    if canonical(obj) != b:                             # D01, -02 lines 201-202
        raise ParseError("Section 2.1: not in canonical form (re-serialization differs)")
    return obj


def sha256hex(b):
    return hashlib.sha256(b).hexdigest()                # D09, -02 lines 229-230


def is_hex64(s):
    # -02 lines 214-215: hex is lowercase, two characters per byte, no prefix.
    return isinstance(s, str) and len(s) == 64 and all(c in "0123456789abcdef" for c in s)


def is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def is_time(s):
    # D05, -02 lines 213-214: UTC, YYYY-MM-DDTHH:MM:SS.ffffffZ, exactly six fraction digits; and a real instant.
    if not isinstance(s, str) or not TIME_RE.match(s):
        return False
    try:
        datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ")
    except ValueError:
        return False
    return True


def is_entry(e):
    # -02 lines 266-269: exactly sha256 and format.
    return (isinstance(e, dict) and set(e) == {"sha256", "format"} and is_hex64(e["sha256"])
            and isinstance(e["format"], str) and e["format"] != "")


# ======================================================================= Sections 2.2 and 2.3: members

def member_errors(r):
    """D10, D11, D17: the reasons the record breaks Section 2.2 or 2.3 other than in evidence and check, which -02
    lines 216-219 refuse before any step runs and lines 237-238 send to steps 1 and 2."""
    if not isinstance(r, dict):
        return ["Section 2.2: the record is not a JSON object"]
    errs = []
    extra = set(r) - TOP_MEMBERS
    if extra:                                           # D10, -02 lines 235-236
        errs.append("Section 2.2: member not allowed: %s" % ",".join(sorted(extra)))
    missing = REQUIRED - set(r)
    if missing:                                         # D10, -02 lines 236-237
        errs.append("Section 2.2: required member missing: %s" % ",".join(sorted(missing)))
    # D11, -02 line 240. READING (O-13): a v other than the one value this document defines is refused.
    if "v" in r and r["v"] != "verdict-record/1":
        errs.append("Section 2.2: v is not \"verdict-record/1\"")
    # D11, -02 lines 242-245. READING (O-13): any non-empty string kind is read; only judgement depends on it (step 1).
    if "kind" in r and not (isinstance(r["kind"], str) and r["kind"] != ""):
        errs.append("Section 2.2: kind is not a non-empty string")
    if "key" in r and not (isinstance(r["key"], str) and r["key"] != ""):          # D11, -02 lines 247-248
        errs.append("Section 2.2: key is not a non-empty string")
    if "version" in r and not (is_int(r["version"]) and r["version"] >= 1):       # D11, -02 lines 250-251
        errs.append("Section 2.2: version is not an integer of 1 or more")
    if is_int(r.get("version")) and r["version"] >= 1:                           # D11, -02 lines 253-254
        sup = r.get("supersedes")
        if r["version"] == 1 and sup is not None:
            errs.append("Section 2.2: supersedes is not null for version 1")
        if r["version"] > 1 and not is_hex64(sup):
            errs.append("Section 2.2: supersedes is not the digest of the previous version")
    if "writer" in r and not (isinstance(r["writer"], str) and r["writer"] != ""):  # D11, -02 lines 256-257
        errs.append("Section 2.2: writer is not a non-empty string")
    if "actor" in r:                                                              # D11, -02 lines 259-261
        a = r["actor"]
        ok = isinstance(a, dict) and a.get("type") in ("person", "system") and isinstance(a.get("id"), str)
        if ok:
            want = {"type", "id"} | ({"model", "model_version"} if a["type"] == "system" else set())
            ok = set(a) == want and all(isinstance(a[k], str) for k in want)
        if not ok:
            errs.append("Section 2.2: actor is not an object of type and id (and model, model_version for a system)")
    if "act_time" in r and not is_time(r["act_time"]):                            # D05, D11, -02 lines 263-264
        errs.append("Section 2.1: act_time is not a time in the form YYYY-MM-DDTHH:MM:SS.ffffffZ")
    if "body" in r:
        b = r["body"]
        if not isinstance(b, dict):                                               # D11, -02 lines 304-306
            errs.append("Section 2.2: body is not an object")
        elif "claim" in b:
            # D17, -02 lines 310-313: exactly one of text (a string) or ref (an evidence entry).
            # READING (O-14): a claim of another shape breaks Sections 2.2-2.3 and is refused before any step;
            # a body with no claim is read (-02 does not say claim is required).
            c = b["claim"]
            ok = isinstance(c, dict) and len(c) == 1 and (
                ("text" in c and isinstance(c["text"], str)) or ("ref" in c and is_entry(c["ref"])))
            if not ok:
                errs.append("Section 2.3: body.claim is not an object with exactly one of text or ref")
    return errs


# ======================================================================= Section 4.5: policy

POLICY_DEPTH_NAMES = ("citation_depth", "max_depth")
POLICY_MEMBERS = {"judgement_kinds", "formats", "inputs_from_evidence_only"}   # with a depth name: what is read (O-2)


def read_policy(p):
    """D41, D42, -02 lines 467-474. Returns (policy, None) or (None, reason) when invalid.

    -02 names what a policy states but not the member names. READING (O-1, stopgap): this checker reads
    judgement_kinds, formats, the depth as citation_depth or max_depth (exactly one), and inputs_from_evidence_only
    (optional, a boolean). citation_depth and inputs_from_evidence_only are the names a second checker of -02 chose
    (Laurent Lemonnier's, interop/verdict-record); max_depth is the name these vectors used under -01. Retires when
    -03 names the members: the alias that -03 does not adopt is then dropped and the vectors regenerated.
    READING (O-2): a member this checker does not know is read past, and the policy runs without it. -02 lines
    472-474 make a policy invalid only when it lacks one of the first three members or states one in another form;
    an unknown member is neither. This is the second checker's reading too (Laurent Lemonnier's, interop/verdict-record,
    on p05). Its cost: a limit stated under a name this checker does not know is not applied. The report's policy
    digest covers the whole policy as given, unknown members included, so another checker can see what was stated."""
    if not isinstance(p, dict):
        return None, "the policy is not an object"
    depth_names = [n for n in POLICY_DEPTH_NAMES if n in p]
    if len(depth_names) != 1:
        return None, "the depth of citation is not stated exactly once"
    jk, fm, dp = p.get("judgement_kinds"), p.get("formats"), p[depth_names[0]]
    if not (isinstance(jk, list) and all(isinstance(k, str) for k in jk)):
        return None, "judgement_kinds is not a list of strings"
    if not (isinstance(fm, list) and all(isinstance(k, str) for k in fm)):
        return None, "formats is not a list of strings"
    if not (is_int(dp) and dp >= 0):
        return None, "the depth of citation is not an integer of 0 or more"
    eo = p.get("inputs_from_evidence_only", False)
    if not isinstance(eo, bool):
        return None, "inputs_from_evidence_only is not a boolean"
    return {"judgement_kinds": jk, "formats": fm, "depth": dp, "evidence_only": eo}, None


def policy_valid(p):
    return read_policy(p)[0] is not None


# ======================================================================= held inputs: rules, formats, containers

class Held:
    """What the checker holds besides this document: rule specifications, format rules, container rules. Each is a
    module under held/ (or given by path) that names its published source. -02 lines 367-369: these are the
    checker's own inputs and are never taken from the record or from the issuer."""

    def __init__(self, modules=()):
        self.rules, self.formats, self.containers, self.sources = {}, {}, {}, []
        for m in modules:
            for r in getattr(m, "RULES", ()):
                self.rules[r.NAME] = r
            for f in getattr(m, "FORMATS", ()):
                self.formats[f.NAME] = f
            for c in getattr(m, "CONTAINERS", ()):
                self.containers[c.KIND] = c
            self.sources.append({"module": m.__name__, "source": m.SOURCE,
                                 "rules": [r.NAME for r in getattr(m, "RULES", ())],
                                 "formats": [f.NAME for f in getattr(m, "FORMATS", ())],
                                 "containers": [c.KIND for c in getattr(m, "CONTAINERS", ())]})


def load_held(paths):
    mods = []
    for p in paths:
        name = "held_" + os.path.splitext(os.path.basename(p))[0]
        spec = importlib.util.spec_from_file_location(name, p)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        mods.append(m)
    return Held(mods)


HERE = os.path.dirname(os.path.abspath(__file__))
TEST_SUITE = os.path.join(HERE, "held", "test_suite.py")


# ======================================================================= Section 4: the check

class Unresolved(Exception):
    """An input of step 3 that cannot be read. kind is 'fail' (-02 lines 419-423) or 'not_run' (-02 lines 417-419,
    425-426)."""

    def __init__(self, kind, why):
        super().__init__(why)
        self.kind, self.why = kind, why


def resolve_pointer(doc, ptr):
    # RFC 6901, as -02 lines 295-297 ask: "" is the whole document; each token unescaped ~1 -> /, ~0 -> ~.
    if ptr == "":
        return doc
    if not ptr.startswith("/"):
        raise KeyError("a JSON Pointer is empty or starts with /")
    cur = doc
    for tok in ptr[1:].split("/"):
        tok = tok.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            if tok not in cur:
                raise KeyError("no member %r" % tok)
            cur = cur[tok]
        elif isinstance(cur, list):
            if not re.fullmatch(r"0|[1-9][0-9]*", tok) or int(tok) >= len(cur):
                raise KeyError("no array index %r" % tok)
            cur = cur[int(tok)]
        else:
            raise KeyError("token %r below a value that is not an object or array" % tok)
    return cur


def resolve_input(name, where, r, ev, relied, items, pol, body_read):
    """D14-D16, D30, D31, D33: one input of check.inputs, -02 lines 285-298 and 415-427."""
    body = r.get("body") if isinstance(r.get("body"), dict) else {}
    if isinstance(where, str):                                       # -02 lines 289-290: a member of body
        if pol["evidence_only"]:                                     # D33, -02 lines 425-427, 480-481
            raise Unresolved("not_run", "input %s is read from body and the policy reads inputs from evidence only"
                             % name)
        if where not in body:                                        # D31, -02 lines 419-420
            raise Unresolved("fail", "input %s names no member of body" % name)
        body_read.append(name)                                       # D38, -02 lines 379-382, 438-439
        return body[where]
    if not isinstance(where, dict):
        raise Unresolved("fail", "input %s is neither a member name nor a binding object" % name)
    if "evidence" not in where or set(where) - {"evidence", "pointer"}:   # D31, -02 lines 292-293, 420-421
        raise Unresolved("fail", "input %s: a binding object with another member, or without evidence" % name)
    i = where["evidence"]
    if not is_int(i) or not isinstance(ev, list) or not (0 <= i < len(ev)):  # D31, -02 line 420
        raise Unresolved("fail", "input %s: no such evidence entry %r" % (name, i))
    if "pointer" in where and not isinstance(where["pointer"], str):
        raise Unresolved("fail", "input %s: pointer is not a string" % name)
    e = ev[i]
    it = items.get(e["sha256"]) if is_entry(e) else None
    if it is None:                                                   # D30, -02 lines 417-419
        raise Unresolved("not_run", "input %s is bound to evidence[%d], which the checker does not hold" % (name, i))
    if i not in relied:                                              # D30, -02 lines 418-419
        raise Unresolved("not_run", "input %s is bound to evidence[%d], which step 2 does not rely on" % (name, i))
    if "pointer" not in where:                                       # D15, -02 lines 294-295
        return sha256hex(it["bytes"])
    try:                                                             # D16, -02 lines 295-298
        doc = parse_strict_json(it["bytes"])
    except ParseError as x:
        raise Unresolved("fail", "input %s: evidence[%d] is not JSON by the rules of Section 2.1 (%s)" % (name, i, x))
    try:
        return resolve_pointer(doc, where["pointer"])
    except KeyError as x:                                            # D31, -02 line 421
        raise Unresolved("fail", "input %s: pointer %r does not resolve (%s)" % (name, where["pointer"], x))


def check(record_bytes, ctx, depth=0):
    """ctx: policy (as read_policy returns it), upper_time_bound, items {sha256: {bytes, upper_time_bound?}},
    held (Held), anchors {name: object}. Returns a report dict (Section 4.4)."""
    steps = {"1": "PASS", "2": "PASS", "3": "PASS"}
    reasons = {}
    rep = {"state": None, "steps": None, "reasons": reasons, "body_inputs_read": [], "not_relied_on": []}

    try:
        r = parse_record(record_bytes)
    except ParseError as e:                                          # D08, -02 lines 216-219
        rep.update(state="refused", reasons={"before_steps": str(e)})
        return rep
    errs = member_errors(r)
    if errs:                                                         # D08, D11, -02 lines 216-219
        rep.update(state="refused", reasons={"before_steps": "; ".join(errs)})
        return rep

    pol, held = ctx["policy"], ctx["held"]

    # ---- Step 1 (D23, -02 lines 386-388)
    c = r.get("check")
    check_ok = isinstance(c, dict) and isinstance(c.get("rule"), str) and c.get("rule") != "" and "result" in c
    if not isinstance(c, dict):
        steps["1"] = "FAIL"; reasons["1"] = "check is missing or not an object"
    elif not check_ok:
        steps["1"] = "FAIL"; reasons["1"] = "check must name a rule and give a result"
    elif set(c) - {"rule", "inputs", "result"}:                      # D13, -02 lines 271-273: exactly these members
        steps["1"] = "FAIL"; reasons["1"] = "check has a member not allowed"
    elif c["rule"] == "judgement" and r.get("kind") not in pol["judgement_kinds"]:
        steps["1"] = "FAIL"; reasons["1"] = "judgement is not allowed for kind %r by the policy" % r.get("kind")

    # ---- Step 2 (D24-D28, -02 lines 397-413). Every entry is examined, and each one not relied on is named.
    # READING (O-3): -02 line 400 says step 2 is NOT RUN "naming the entry"; this checker names every entry it
    # could not rely on, not only the first, because step 3 needs to know which entries step 2 relies on.
    ev = r.get("evidence")
    relied = set()
    if not (isinstance(ev, list) and all(is_entry(e) for e in ev)):
        steps["2"] = "FAIL"; reasons["2"] = "evidence is missing or an entry is not as in Section 2.2"
    else:
        claim = r["body"].get("claim")
        if isinstance(claim, dict) and "ref" in claim and claim["ref"] not in ev:
            # D17, -02 lines 313-314. READING (I-2): the ref missing from evidence is a FAIL of step 2.
            steps["2"] = "FAIL"; reasons["2"] = "body.claim.ref does not appear in evidence"
        else:
            not_relied = []
            for i, e in enumerate(ev):
                why = entry_problem(i, e, ctx, depth)
                if why is None:
                    relied.add(i)
                else:
                    not_relied.append(why)
            if not_relied:
                steps["2"] = "NOT RUN"; reasons["2"] = "; ".join(not_relied)
                rep["not_relied_on"] = not_relied

    # ---- Step 3 (D29-D35, -02 lines 415-427)
    if check_ok and c["rule"] == "judgement":
        pass  # READING (I-4): for judgement step 3 re-runs nothing and PASSes, as Appendix A.1 implies.
    elif not check_ok:
        steps["3"] = "NOT RUN"; reasons["3"] = "needs a check that names a rule and gives a result"
    else:
        steps["3"], why, rerun = step3(r, c, ev if isinstance(ev, list) else None, relied, ctx, rep["body_inputs_read"])
        if why:
            reasons["3"] = why
        if rerun is not None:
            rep["re_run_result"] = rerun

    # ---- State (D19, D36, -02 lines 354-356, 433-436)
    if "FAIL" in steps.values():
        state = "refused"
    elif "NOT RUN" in steps.values():
        state = "held"
    else:
        state = "released"
    rep.update(state=state, steps=steps)
    rep["first_failed_step"] = next((s for s in "123" if steps[s] == "FAIL"), None)
    rep["first_not_run_step"] = next((s for s in "123" if steps[s] == "NOT RUN"), None)
    return rep


def entry_problem(i, e, ctx, depth):
    """D24-D28: why step 2 cannot rely on evidence[i], or None."""
    pol, held = ctx["policy"], ctx["held"]
    it = ctx["items"].get(e["sha256"])
    if it is None or sha256hex(it["bytes"]) != e["sha256"]:          # D24, -02 lines 398-400
        return "evidence[%d]: no item held with this digest" % i
    if e["format"] not in pol["formats"]:                             # D25, -02 lines 402-404
        return "evidence[%d]: format not listed by the policy" % i
    ub = it.get("upper_time_bound")
    if e["format"] == VERDICT_FORMAT:                                 # D26, D28, -02 lines 406-413
        if depth + 1 > pol["depth"]:
            return "evidence[%d]: beyond the citation depth %d" % (i, pol["depth"])
        if ub is None:
            return "evidence[%d]: no upper time bound for the cited record" % i
        sub = check(it["bytes"], dict(ctx, upper_time_bound=ub), depth + 1)
        if sub["state"] != "released":
            return "evidence[%d]: the cited record is %s" % (i, sub["state"])
    else:
        fr = held.formats.get(e["format"])
        if fr is None:
            # READING (O-4): a format the policy lists but the checker holds no rules for is not relied on.
            return "evidence[%d]: the checker holds no rules for this format" % i
        met, why, fub = fr.check_item(it["bytes"], ctx)
        if not met:
            return "evidence[%d]: the format's rules are not met (%s)" % (i, why)
        ub = fub if fub is not None else ub
    if ub is not None and ub > ctx["upper_time_bound"]:              # D27, -02 lines 408-410
        return "evidence[%d]: its upper time bound is later than the record's" % i
    return None


def step3(r, c, ev, relied, ctx, body_read):
    """Returns (result, reason, re-run result)."""
    pol, held = ctx["policy"], ctx["held"]
    inputs = c.get("inputs", {})
    if not isinstance(inputs, dict):                                  # -02 line 285: inputs is an object
        return "FAIL", "check.inputs is not an object", None
    fails, not_runs, values = [], [], {}
    # READING (O-5): inputs are resolved before the rule is looked up, since resolution is defined by -02 alone; a
    # binding that cannot be resolved FAILs step 3 even when the checker does not hold the rule.
    for name in sorted(inputs):
        try:
            values[name] = resolve_input(name, inputs[name], r, ev, relied, ctx["items"], pol, body_read)
        except Unresolved as u:
            (fails if u.kind == "fail" else not_runs).append(u.why)
    rule = held.rules.get(c["rule"])
    if rule is None and not fails:                                    # D29, -02 lines 415-416. READING (I-8)
        return "NOT RUN", "; ".join(["rule specification not held: %s" % c["rule"]] + not_runs), None
    if rule is not None:
        fails += rule.input_problems(values, sorted(inputs))           # D31, -02 line 422: wrong JSON type
    if fails:                                                         # D31, D32, -02 lines 419-424
        return "FAIL", "; ".join(fails + not_runs), None
    if not_runs:                                                      # D30, D33
        return "NOT RUN", "; ".join(not_runs), None
    try:
        got = rule.rerun(values, ctx)
    except Exception as x:  # READING (O-7): a held rule that cannot be run on resolved inputs leaves step 3 NOT RUN.
        return "NOT RUN", "the held rule could not be re-run: %s: %s" % (type(x).__name__, x), None
    if got != c["result"]:                                            # D34, -02 line 427
        return "FAIL", "the re-run gave %s, the record states %s" % (
            json.dumps(got, ensure_ascii=False), json.dumps(c["result"], ensure_ascii=False)), got
    return "PASS", None, got


# ======================================================================= Section 3: container (presenter-supplied)

def check_container(record_bytes, record, container, held, anchors):
    """D18, -02 lines 318-330. Returns None when the container shows the record, else the reason it does not.
    A container is held only through a container rule the checker holds."""
    if container is None:
        return "no container was presented"
    rule = held.containers.get(container.get("kind")) if isinstance(container, dict) else None
    if rule is None:
        return "the checker holds no rule for this container"
    return rule.shows(record_bytes, record.get("writer") if isinstance(record, dict) else None, container, anchors)


# ======================================================================= Section 4.4: the report

def summary_line(rep):
    # D39, -02 lines 456-457: a summary line names the state and every step's result.
    if rep["steps"] is None:
        return "state %s; no step ran" % rep["state"]
    return "state %s; step 1 %s; step 2 %s; step 3 %s" % (rep["state"], rep["steps"]["1"], rep["steps"]["2"],
                                                          rep["steps"]["3"])


def run(record_bytes, policy, upper_time_bound, items, held, anchors=None, container=None, container_presented=False):
    """One check, with the report Section 4.4 asks for (D36-D40)."""
    anchors = anchors or {}
    out = {"checker": "vrcheck.py, reference checker for " + DRAFT,
           "policy_sha256": sha256hex(canonical(policy)),            # D40, -02 lines 460-461: over canonical form
           "trust_anchors_sha256": {k: sha256hex(canonical(v)) for k, v in sorted(anchors.items())},  # D40
           "upper_time_bound": upper_time_bound,                     # D40, -02 line 459-460
           "held": held.sources}
    pol, why = read_policy(policy)
    if pol is None:                                                   # D42, -02 lines 472-474
        out.update(state="no verdict", steps=None, reasons={"policy": "invalid: " + why})
        out["summary"] = summary_line(out)
        return out
    ctx = {"policy": pol, "upper_time_bound": upper_time_bound, "items": items, "held": held, "anchors": anchors}
    rep = check(record_bytes, ctx)
    out.update(rep)
    if ctx.get("rule_detail"):
        out["rule_detail"] = ctx["rule_detail"]
    if not pol["evidence_only"]:
        out["body_inputs_read"] = rep["body_inputs_read"]             # D38, -02 lines 438-439
    else:
        out.pop("body_inputs_read", None)
    if container_presented and rep["steps"] is not None:
        try:
            rec = json.loads(record_bytes)
        except ValueError:
            rec = None
        shown = check_container(record_bytes, rec, container, held, anchors)
        out["container"] = "shows the record" if shown is None else shown
        if shown is not None and out["state"] != "held":
            # D18, -02 lines 329-330: if the container does not show the record, the state is held, with the reason.
            # READING (O-6): the steps still run and are reported; a FAIL on bytes not shown to be the writer's is
            # reported, and the state is held.
            out["state_from_steps"] = out["state"]
            out["state"] = "held"
    out["summary"] = summary_line(out)
    return out


def items_from_vector(v):
    items = {}
    for it in v.get("evidence_items", []):
        b = base64.b64decode(it["b64"])
        items[sha256hex(b)] = {"bytes": b, "upper_time_bound": it.get("upper_time_bound")}
    return items


def run_vector(v, extra_hold=()):
    """A vector names, in hold, the modules under held/ it needs beyond the test suite (vectors from -02 on)."""
    held = load_held([TEST_SUITE] + [os.path.join(HERE, "held", h) for h in v.get("hold", [])] + list(extra_hold))
    return run(base64.b64decode(v["record_b64"]), v["policy"], v["upper_time_bound"], items_from_vector(v), held)


if __name__ == "__main__":
    args = sys.argv[1:]
    hold = []
    while args and args[0] == "--hold":
        hold.append(args[1])
        args = args[2:]
    for path in args:
        v = json.load(open(path, encoding="utf-8"))
        print(path, json.dumps(run_vector(v, hold), ensure_ascii=False))
