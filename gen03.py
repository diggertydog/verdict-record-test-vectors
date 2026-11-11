"""Vectors added for draft-wright-verdict-record-03, and two members -03 adds to every vector's expected answer.

Run after gen.py and gen02.py. As there, every expected answer is written here by hand from the draft text and is NOT
computed by any checker.

1. New vectors (a15-a17, g31-g42): one for each behaviour that -02 left to the checker and -03 states, where the
   reference checker and an independent checker of -02 (MolTrust, reproduction-runs tag run-20261111-verdict-record-02)
   were shown, by a differential run over mutated records, to answer differently or where no vector pinned it.
2. expected.named, on every vector: what -03 says the check names. "FAIL at step N" or "NOT RUN at step N" or "PASS"
   (-03 Section 4.1: the first step that FAILed, else the first that could not run); "Section 2.N" for a record
   refused before any step (-03 Section 2.1: the first of 2.1, 2.2, 2.3 whose rule the record breaks, written by hand
   below for each such vector); null for no verdict.
3. decided_by, on every vector whose expected answer -03 changes or adds: the sentence of -03 that decides it,
   verbatim. run_all.py --draft <-03 xml> refuses a vector whose sentence is not in the draft.
"""
import base64
import glob
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def C(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def H(b): return hashlib.sha256(b).hexdigest()
def B(b): return base64.b64encode(b).decode()


OPAQUE = "urn:example:verdict-record:format:opaque"
NEVER = "urn:example:verdict-record:format:never-verifies"
VR = "verdict-record/1"
AT_LEAST = "urn:example:verdict-record:rule:at-least"
EQUALS = "urn:example:verdict-record:rule:equals"
UB = "2026-11-01T12:00:00.000000Z"
POLICY = {"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "citation_depth": 2}
JITEM = b'{"m":5,"n":7,"s":"seven"}'
NUMS = b'{"x":1.0,"y":1,"z":[1,{"w":2.50}],"t":[1,{"w":2.5}]}'
NV = b"evidence item three: an item whose format's rules are never met"
P3 = {"1": "PASS", "2": "PASS", "3": "PASS"}


def ent(b, fmt=OPAQUE): return {"format": fmt, "sha256": H(b)}


def rec(**over):
    r = {"v": "verdict-record/1", "kind": "check-run", "key": "k-0003", "version": 1,
         "supersedes": None, "writer": "issuer.example",
         "actor": {"type": "system", "id": "runner-1", "model": "none", "model_version": "0"},
         "act_time": "2026-11-01T10:00:00.000000Z",
         "evidence": [ent(JITEM)],
         "check": {"rule": AT_LEAST, "inputs": {"value": {"evidence": 0, "pointer": "/n"},
                                                "min": {"evidence": 0, "pointer": "/m"}}, "result": "pass"},
         "body": {"claim": {"text": "The value n of the cited item is at least its value m."}}}
    for k, v in over.items():
        if v is DEL:
            r.pop(k, None)
        else:
            r[k] = v
    return r


class _Del: pass
DEL = _Del()

vectors = []


def V(name, section, desc, record=None, state=None, steps=None, items=(JITEM,), policy=POLICY, raw=None,
      no_step_runs=False, decided_by=None, policy_members_not_used=None):
    rb = raw if raw is not None else C(record)
    v = {"name": name, "section": "draft-wright-verdict-record-03 " + section, "description": desc,
         "record_b64": B(rb), "record_sha256": H(rb), "evidence_items": [{"b64": B(b)} for b in items],
         "upper_time_bound": UB, "policy": policy, "policy_sha256": H(C(policy)),
         "expected": {"state": state, "steps": steps}}
    if no_step_runs:
        v["expected"]["no_step_runs"] = True
    if policy_members_not_used is not None:
        v["expected"]["policy_members_not_used"] = policy_members_not_used
    v["decided_by"] = decided_by
    vectors.append(v)


# ---------------------------------------------------------------- Section 2.1: escapes and time
base = C(rec())
nl = base.replace(b'"text":"The value', b'"text":"line one\\nThe value', 1)
V("a15-control-short-escape", "Section 2.1",
  "A claim text holding U+000A written as \\n, the short form canonical form uses: canonical, released.",
  raw=nl, state="released", steps=P3,
  decided_by="each written as \\b, \\t, \\n, \\f or \\r where one of those applies")
V("a16-control-u-escape", "Section 2.1",
  "The same U+000A written as \\u000a: not canonical, refused before any step, named by Section 2.1.",
  raw=nl.replace(b"\\n", b"\\u000a", 1), state="refused", no_step_runs=True,
  decided_by="each written as \\b, \\t, \\n, \\f or \\r where one of those applies and otherwise as \\u followed by four lowercase hex digits")
V("a17-leap-second", "Section 2.1",
  "act_time names second 60: not a time, refused before any step, named by Section 2.1.",
  rec(act_time="2026-12-31T23:59:60.000000Z"), state="refused", no_step_runs=True,
  decided_by="names a day that exists in the Gregorian calendar and a second from 00 to 59")

_two = rec(act_time="2026-02-30T10:00:00.000000Z")
_two["note"] = "a member not allowed"
V("a18-breaks-2-1-and-2-2", "Section 2.1",
  "A record with a member not allowed (Section 2.2) and an act_time naming 30 February (a form Section 2.1 states): "
  "refused before any step, named by the first section in the order 2.1, 2.2, 2.3, which is 2.1.",
  _two, state="refused", no_step_runs=True,
  decided_by="Where a record breaks rules of more than one of the three sections, the refusal is named by the first of them in that order.")

# ---------------------------------------------------------------- Section 4.5: policy
V("g31-policy-max-depth-only", "Section 4.5",
  "The depth stated only as max_depth, the name the -02 vectors used: the policy lacks citation_depth and is "
  "invalid; no verdict. (max_depth is a member -03 does not define.)",
  rec(), state="no verdict", policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR],
                                     "max_depth": 2},
  decided_by="A policy that is not a JSON object, that lacks one of the first three members, or that states any of these four members in a form other than these, is invalid")

# ---------------------------------------------------------------- Section 2.2 and 2.3: members
V("g32-kind-empty", "Section 2.2", "kind is the empty string: any string is read as a kind; released.",
  rec(kind=""), state="released", steps=P3,
  decided_by="A checker reads any string as a kind, including one this document does not define")
V("g33-actor-id-not-string", "Section 2.2", "actor.id is an integer: refused before any step, Section 2.2.",
  rec(actor={"type": "system", "id": 5, "model": "none", "model_version": "0"}), state="refused", no_step_runs=True,
  decided_by="The values of id, model and model_version are strings.")
V("g34-version-2-supersedes-absent", "Section 2.2",
  "version 2 with no supersedes member: refused before any step, Section 2.2.",
  rec(version=2, supersedes=DEL), state="refused", no_step_runs=True,
  decided_by="For a later version it MUST be present and is the digest of the previous version.")
V("g35-claim-missing", "Section 2.2, 2.3", "body has no claim: refused before any step, Section 2.3.",
  rec(body={"note": "no claim"}), state="refused", no_step_runs=True,
  decided_by="which MUST be present")
V("g36-claim-ref-no-evidence", "Section 2.3",
  "body.claim.ref with no evidence member at all: refused before any step, Section 2.3.",
  rec(evidence=DEL, body={"claim": {"ref": ent(JITEM)}}), state="refused", no_step_runs=True,
  decided_by="including a record with no evidence array, breaks this section and is refused before any step runs")
V("g37-entry-format-empty", "Section 2.2, 4.3",
  "An evidence entry whose format is the empty string: not an entry as in Section 2.2, so step 2 FAILs; step 3's "
  "inputs are bound to that entry, which step 2 does not rely on: NOT RUN. Refused, FAIL at step 2.",
  rec(evidence=[{"format": "", "sha256": H(JITEM)}]), state="refused",
  steps={"1": "PASS", "2": "FAIL", "3": "NOT RUN"},
  decided_by="a non-empty string that names the format by whose rules the item is verified")
V("g38-rule-empty", "Section 2.2, 4.3",
  "check.rule is the empty string: step 1 FAILs (it names no rule) and step 3 is NOT RUN.",
  rec(check={"rule": "", "inputs": {}, "result": "pass"}), state="refused",
  steps={"1": "FAIL", "2": "PASS", "3": "NOT RUN"},
  decided_by="If check does not name a rule and give a result, step 3 is NOT RUN.")
V("g39-unresolvable-input-rule-not-held", "Section 4.3",
  "A rule the checker does not hold, with an input bound to an evidence entry that does not exist: inputs are "
  "resolved whether or not the rule is held, and the unresolvable input FAILs step 3.",
  rec(check={"rule": "urn:example:verdict-record:rule:not-held", "inputs": {"x": {"evidence": 5}},
             "result": "pass"}), state="refused", steps={"1": "PASS", "2": "PASS", "3": "FAIL"},
  decided_by="whether or not it holds the rule's specification")
V("g44-inputs-not-object-rule-not-held", "Section 4.3",
  "check.inputs is an array, and the checker does not hold the rule: inputs are resolved whether or not the rule is "
  "held, and inputs that are not an object FAIL step 3.",
  rec(check={"rule": "urn:example:verdict-record:rule:not-held", "inputs": [], "result": "pass"}),
  state="refused", steps={"1": "PASS", "2": "PASS", "3": "FAIL"},
  decided_by="If check.inputs is present and is not an object")
V("g45-supersedes-uppercase-hex", "Section 2.1",
  "version 2 whose supersedes is a SHA-256 digest written in uppercase hex: the form of hex is a rule of Section "
  "2.1, so the refusal before any step is named by Section 2.1, not 2.2.",
  rec(version=2, supersedes="A" * 64), state="refused", no_step_runs=True,
  decided_by="such as the form of a time or of hex, is a rule of this section.")
V("g46-claim-ref-uppercase-hex", "Section 2.1, 2.3",
  "body.claim.ref whose sha256 is written in uppercase hex (and so equals no evidence entry): it breaks Sections 2.1 "
  "and 2.3; the refusal is named by the first, Section 2.1.",
  rec(body={"claim": {"ref": {"format": OPAQUE, "sha256": H(JITEM).upper()}}}), state="refused", no_step_runs=True,
  decided_by="Where a record breaks rules of more than one of the three sections, the refusal is named by the first of them in that order.")
V("g40-fail-outranks-not-run", "Section 4.3",
  "Two inputs: one bound to an item step 2 does not rely on (NOT RUN), one of the wrong type for the held rule "
  "(FAIL). The FAIL outranks: refused, FAIL at step 3.",
  rec(evidence=[ent(JITEM), ent(NV, NEVER)],
      check={"rule": AT_LEAST, "inputs": {"value": {"evidence": 1, "pointer": "/n"},
                                          "min": {"evidence": 0, "pointer": "/s"}}, "result": "pass"}),
  items=(JITEM, NV), state="refused", steps={"1": "PASS", "2": "NOT RUN", "3": "FAIL"},
  decided_by="Within step 3, a FAIL outranks a NOT RUN")
V("g41-two-steps-fail", "Section 4.1",
  "check carries a member not allowed (step 1 FAILs) and states a result the re-run does not give (step 3 FAILs): "
  "the check names the first step that FAILed, step 1.",
  rec(check={"rule": AT_LEAST, "inputs": {"value": {"evidence": 0, "pointer": "/n"},
                                          "min": {"evidence": 0, "pointer": "/m"}}, "result": "fail", "note": "x"}),
  state="refused", steps={"1": "FAIL", "2": "PASS", "3": "FAIL"},
  decided_by="the check FAILs at the first step that FAILed")
V("g42-equal-numbers-written-differently", "Section 4.3",
  "The equals rule on 1.0 and 1, and on two arrays holding 2.50 and 2.5: equal as JSON values (same mathematical "
  "value); the record states equal for the first pair and is released.",
  rec(evidence=[ent(NUMS)],
      check={"rule": EQUALS, "inputs": {"a": {"evidence": 0, "pointer": "/x"}, "b": {"evidence": 0, "pointer": "/y"}},
             "result": "equal"}),
  items=(NUMS,), state="released", steps=P3,
  decided_by="both are numbers with the same mathematical value")
V("g43-equal-nested-numbers", "Section 4.3",
  "The equals rule on [1,{\"w\":2.50}] and [1,{\"w\":2.5}]: equal; released.",
  rec(evidence=[ent(NUMS)],
      check={"rule": EQUALS, "inputs": {"a": {"evidence": 0, "pointer": "/z"}, "b": {"evidence": 0, "pointer": "/t"}},
             "result": "equal"}),
  items=(NUMS,), state="released", steps=P3,
  decided_by="both are arrays of the same length whose members are equal in order")

for v in vectors:
    with open(os.path.join(HERE, v["name"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False)
        f.write("\n")

# ---------------------------------------------------------------- expected.named and decided_by on every vector
# A record refused before any step: the section that names the refusal, written by hand from -03 Section 2.1.
PRESTEP = {
    "a02-whitespace": "2.1", "a03-member-order": "2.1", "a04-duplicate-member": "2.1", "a05-byte-order-mark": "2.1",
    "a06-fraction": "2.1", "a07-integer-range": "2.1", "a08-escaped-non-ascii": "2.1", "a10-lone-surrogate": "2.1",
    "a12-depth-33": "2.1", "a13-unknown-member": "2.2", "a14-missing-writer": "2.2",
    "a16-control-u-escape": "2.1", "a17-leap-second": "2.1", "a18-breaks-2-1-and-2-2": "2.1",
    "c11-claim-ref-not-in-evidence": "2.3",
    "g19-act-time-form": "2.1", "g20-version-zero": "2.2", "g21-supersedes-on-version-1": "2.2",
    "g22-version-2-supersedes-null": "2.2", "g24-key-empty": "2.2", "g25-actor-person-with-model": "2.2",
    "g26-v-other-value": "2.2", "g28-claim-text-and-ref": "2.3", "g29-body-not-object": "2.2",
    "g30-claim-text-not-string": "2.3",
    "g33-actor-id-not-string": "2.2", "g34-version-2-supersedes-absent": "2.2", "g35-claim-missing": "2.3",
    "g36-claim-ref-no-evidence": "2.3", "g45-supersedes-uppercase-hex": "2.1", "g46-claim-ref-uppercase-hex": "2.1",
}
# Vectors from -01/-02 whose expected answer -03 changes, and the -03 sentence that changes it.
CHANGED = {
    "c11-claim-ref-not-in-evidence": "A record whose ref does not appear in evidence, including a record with no evidence array, breaks this section and is refused before any step runs",
    "g15-policy-unknown-member": "A policy member that this document does not define does not make the policy invalid.",
    "g17-policy-two-depths": "A policy member that this document does not define does not make the policy invalid.",
    "f01-appendix-a": "The second evidence item is a Signed Evaluation Receipt",
    "h01-a2-hops-without-signature-released": "the rule reads every scope as a grant and none as a limit",
}
DEPTH_SENTENCE = "An integer of 0 or more: the depth of citation the checker follows"


def named(name, e):
    if e["state"] == "no verdict":
        return None
    s = e.get("steps")
    if s is None:
        if e["state"] != "refused" or name not in PRESTEP:
            raise SystemExit("%s: no steps and no pre-step section written" % name)
        return "Section " + PRESTEP[name]
    for k in "123":
        if s[k] == "FAIL":
            return "FAIL at step " + k
    for k in "123":
        if s[k] == "NOT RUN":
            return "NOT RUN at step " + k
    return "PASS"


n_named = n_dec = 0
for p in sorted(glob.glob(os.path.join(HERE, "[a-h][0-9][0-9]-*.json"))):
    v = json.load(open(p, encoding="utf-8"))
    name = v["name"]
    v["expected"]["named"] = named(name, v["expected"])
    n_named += 1
    if name in PRESTEP:
        v["expected"]["no_step_runs"] = True
    if name in CHANGED:
        v["decided_by"] = CHANGED[name]
    if "decided_by" not in v and "citation_depth" in v["policy"]:
        v["decided_by"] = DEPTH_SENTENCE      # every policy now names the depth citation_depth (-03 4.5)
    n_dec += "decided_by" in v
    with open(p, "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False)
        f.write("\n")
print("%d new vectors; expected.named set on %d; decided_by on %d" % (len(vectors), n_named, n_dec))
