"""Generates the test vectors for draft-wright-verdict-record (groups a-e written against -01; f01 holds the
Appendix A.1 example of -03; policies use the member names of -03 Section 4.5).
Each vector's expected outcome is written here by hand from the draft text, with the
section it rests on, and is NOT computed by the reference checker."""
import base64, hashlib, json, os

OUT = "."
os.makedirs(OUT, exist_ok=True)

def C(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def H(b): return hashlib.sha256(b).hexdigest()
def B(b): return base64.b64encode(b).decode()

OPAQUE = "urn:example:verdict-record:format:opaque"
NEVER = "urn:example:verdict-record:format:never-verifies"
VR = "verdict-record/1"
AT_LEAST = "urn:example:verdict-record:rule:at-least"
UB = "2026-11-01T12:00:00.000000Z"

POLICY = {"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "citation_depth": 2}

ITEM1 = b"evidence item one: an opaque test item"
ITEM2 = b"evidence item two: an item that never verifies"

def ent(b, fmt=OPAQUE): return {"format": fmt, "sha256": H(b)}

def rec(**over):
    r = {"v": "verdict-record/1", "kind": "check-run", "key": "k-0001", "version": 1,
         "supersedes": None, "writer": "issuer.example",
         "actor": {"type": "system", "id": "runner-1", "model": "none", "model_version": "0"},
         "act_time": "2026-11-01T10:00:00.000000Z",
         "evidence": [ent(ITEM1)],
         "check": {"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "pass"},
         "body": {"claim": {"text": "The measured value is at least the threshold."}, "measured": 7, "threshold": 5}}
    for k, v in over.items():
        if v is DEL: r.pop(k, None)
        else: r[k] = v
    return r

class _Del: pass
DEL = _Del()

vectors = []
def V(name, section, desc, record_bytes, expected_state, expected_steps=None, items=(ITEM1,),
      policy=POLICY, ub=UB, interp=None, item_bounds=None, extra=None):
    its = []
    for b in items:
        e = {"b64": B(b)}
        if item_bounds and H(b) in item_bounds: e["upper_time_bound"] = item_bounds[H(b)]
        its.append(e)
    v = {"name": name, "section": section, "description": desc,
         "record_b64": B(record_bytes), "record_sha256": H(record_bytes),
         "evidence_items": its, "upper_time_bound": ub, "policy": policy,
         "policy_sha256": H(C(policy)),
         "expected": {"state": expected_state, "steps": expected_steps}}
    if interp: v["depends_on_interpretation"] = interp
    if extra: v["expected"].update(extra)
    vectors.append(v)

P3 = {"1": "PASS", "2": "PASS", "3": "PASS"}

# ---- Group A: encoding and members (Sections 2.1, 2.2) ----
base = C(rec())
V("a01-baseline-released", "2.1, 2.2, 4.3", "A canonical record whose rule re-runs to its stated result, citing one item that verifies.", base, "released", P3)
V("a02-whitespace", "2.1", "The baseline with one space after a colon: not canonical.", base.replace(b'"v":', b'"v": '), "refused", None, interp="I-1")
V("a03-member-order", "2.1", "Two members out of code-point order.", base.replace(b'"v":"verdict-record/1","version":1', b'"version":1,"v":"verdict-record/1"'), "refused", None, interp="I-1")
V("a04-duplicate-member", "2.1", "The member key appears twice.", base.replace(b'"key":"k-0001",', b'"key":"k-0001","key":"k-0001",'), "refused", None, interp="I-1")
V("a05-byte-order-mark", "2.1", "The baseline preceded by a UTF-8 byte-order mark.", b"\xef\xbb\xbf" + base, "refused", None, interp="I-1")
V("a06-fraction", "2.1", "A number with a fraction.", base.replace(b'"measured":7', b'"measured":7.5'), "refused", None, interp="I-1")
V("a07-integer-range", "2.1", "An integer of 2^53, one above the range.", base.replace(b'"measured":7', b'"measured":9007199254740992'), "refused", None, interp="I-1")
V("a08-escaped-non-ascii", "2.1", "A non-ASCII character written as an escape instead of its UTF-8 bytes.",
  C(rec(writer="issuer-é.example")).replace("é".encode(), b"\\u00e9"), "refused", None, interp="I-1")
V("a09-utf8-bytes", "2.1", "The same character written as its UTF-8 bytes: canonical.", C(rec(writer="issuer-é.example")), "released", P3)
V("a10-lone-surrogate", "2.1", "A string holding an escaped lone surrogate.", base.replace(b'"issuer.example"', b'"issuer\\ud800.example"'), "refused", None, interp="I-1")
def nest(n):
    x = 1
    for _ in range(n): x = {"a": x}
    return x
# depth: record object 1, body 2, deep member adds n levels of objects
V("a11-depth-32", "2.1", "Nesting exactly 32 levels deep (record, body, then 30 objects).",
  C(rec(body={"claim": {"text": "t"}, "measured": 7, "threshold": 5, "deep": nest(30)})), "released", P3)
V("a12-depth-33", "2.1", "Nesting 33 levels deep: a checker MUST refuse it.",
  C(rec(body={"claim": {"text": "t"}, "measured": 7, "threshold": 5, "deep": nest(31)})), "refused", None, interp="I-1")
r = rec(); r["note"] = "x"
V("a13-unknown-member", "2.2", "A member the draft does not define.", C(r), "refused", None, interp="I-1")
V("a14-missing-writer", "2.2", "The required member writer is absent.", C(rec(writer=DEL)), "refused", None, interp="I-1")

# ---- Group B: step 1 ----
V("b01-check-missing", "2.2, 4.3 step 1", "No check member: step 1 FAILs; step 3 cannot run.", C(rec(check=DEL)), "refused", {"1": "FAIL", "2": "PASS", "3": "NOT RUN"})
V("b02-check-no-result", "4.3 step 1", "check names a rule but gives no result.", C(rec(check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}})), "refused", {"1": "FAIL", "2": "PASS", "3": "NOT RUN"})
V("b03-judgement-kind-not-listed", "4.3 step 1, 4.5", "Rule judgement on a kind the policy does not list.", C(rec(check={"rule": "judgement", "result": "supported"})), "refused", {"1": "FAIL", "2": "PASS", "3": "PASS"}, interp="I-4")
V("b04-judgement-kind-listed", "4.3 steps 1 and 3", "Rule judgement on a kind the policy lists: no rule is re-run.",
  C(rec(kind="model-decision", check={"rule": "judgement", "result": "supported"})), "released", P3, interp="I-4")

# ---- Group C: step 2 ----
V("c01-evidence-missing", "2.2, 4.3 step 2", "No evidence member: step 2 FAILs.", C(rec(evidence=DEL)), "refused", {"1": "PASS", "2": "FAIL", "3": "PASS"})
V("c02-entry-extra-member", "2.2, 4.3 step 2", "An evidence entry with a third member.", C(rec(evidence=[dict(ent(ITEM1), size=38)])), "refused", {"1": "PASS", "2": "FAIL", "3": "PASS"})
V("c03-entry-uppercase-hex", "2.1, 4.3 step 2", "An entry whose sha256 is upper-case hex.", C(rec(evidence=[{"format": OPAQUE, "sha256": H(ITEM1).upper()}])), "refused", {"1": "PASS", "2": "FAIL", "3": "PASS"})
V("c04-item-not-held", "4.3 step 2", "The checker does not hold the cited item.", base, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=())
V("c05-format-not-in-policy", "4.3 step 2, 4.5", "The item is held but its format is not one the policy lists.", base, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"},
  policy={"judgement_kinds": ["model-decision"], "formats": [NEVER, VR], "citation_depth": 2})
V("c06-item-does-not-verify", "4.3 step 2", "The item does not verify by its format.", C(rec(evidence=[ent(ITEM2, NEVER)])), "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(ITEM2,))
inner = C(rec(key="k-inner"))
outer = C(rec(key="k-outer", evidence=[ent(inner, VR)]))
IB_OK = {H(inner): "2026-11-01T11:00:00.000000Z"}
V("c07-cites-released-record", "4.3 step 2", "Cites a verdict record that is itself released, with an earlier upper time bound.", outer, "released", P3, items=(inner, ITEM1), item_bounds=IB_OK)
V("c08-beyond-depth", "4.3 step 2, 4.5", "Same, but the policy follows no citations (citation_depth 0).", outer, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(inner, ITEM1), item_bounds=IB_OK,
  policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "citation_depth": 0}, interp="I-5")
V("c09-cited-bound-later", "4.3 step 2", "The cited record's upper time bound is later than the citing record's.", outer, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(inner, ITEM1),
  item_bounds={H(inner): "2026-11-01T13:00:00.000000Z"})
bad_inner = C(rec(key="k-bad", check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "fail"}))
outer_bad = C(rec(key="k-outer2", evidence=[ent(bad_inner, VR)]))
V("c10-cites-refused-record", "4.3 step 2", "Cites a verdict record that is itself refused: the item does not verify.", outer_bad, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(bad_inner, ITEM1),
  item_bounds={H(bad_inner): "2026-11-01T11:00:00.000000Z"}, interp="I-6")
V("c11-claim-ref-not-in-evidence", "-03 2.1, 2.3", "body.claim.ref names an item that evidence does not list: the record breaks Section 2.3 and is refused before any step, the refusal named by Section 2.3. Under -02 the reference checker refused it at step 2 (I-2); -03 settles it.",
  C(rec(body={"claim": {"ref": ent(ITEM2)}, "measured": 7, "threshold": 5})), "refused", None,
  extra={"no_step_runs": True})
V("c12-empty-evidence", "4.3 step 2", "An empty evidence array: every entry (none) is held and verifies.", C(rec(evidence=[])), "released", P3, items=(), interp="I-3")

# ---- Group D: step 3 ----
V("d01-result-mismatch", "4.3 step 3", "The rule re-runs to pass; the record states fail.", bad_inner, "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"})
V("d02-input-wrong-type", "4.3 step 3", "A rule input is a string, not an integer: FAIL, not a rule result.",
  C(rec(body={"claim": {"text": "t"}, "measured": "7", "threshold": 5})), "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"}, interp="I-7")
V("d03-rule-not-held", "4.3 step 3", "The checker holds no specification for the named rule.",
  C(rec(check={"rule": "urn:example:verdict-record:rule:unknown", "result": "pass"})), "held", {"1": "PASS", "2": "PASS", "3": "NOT RUN"})
V("d04-not-run-then-fail", "4.1", "Step 2 cannot run and step 3 FAILs: the check FAILs at step 3.", bad_inner, "refused", {"1": "PASS", "2": "NOT RUN", "3": "FAIL"}, items=())
V("d05-rule-false-low", "4.3 step 3", "The rule re-runs to fail and the record states fail.",
  C(rec(body={"claim": {"text": "t"}, "measured": 3, "threshold": 5}, check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "fail"})), "released", P3)

# ---- Group F: the draft's own Appendix A ----
# The bytes come from appendix-objects.json, written by the draft's tools/appendix_gen.py from the same objects that
# produce Appendix A of -03. No digest is copied: each is computed here from those bytes.
APPX = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "appendix-objects.json"), encoding="utf-8"))
A1_REC = base64.b64decode(APPX["A.1"]["record_b64"])
A1_ITEMS = tuple(base64.b64decode(i["b64"]) for i in APPX["A.1"]["items"])
V("f01-appendix-a", "Appendix A.1", "The draft's first example (-03), digest " + H(A1_REC)[:8] + "...: a model decision citing a claim record and the receipt of vector P1 of draft-gruszka-signed-evaluation-receipts-04, both printed in the draft. The checker holds both items; the policy lists neither format, so step 2 is NOT RUN.",
  A1_REC, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=A1_ITEMS,
  policy={"judgement_kinds": ["model-decision"], "formats": [], "citation_depth": 2}, interp="I-4")

# ---- Group E: policy ----
V("e01-invalid-policy", "4.4, 4.5", "The checker's policy is invalid: no verdict.", base, "no verdict", None,
  policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE], "citation_depth": -1}, interp="I-8")

for v in vectors:
    with open(os.path.join(OUT, v["name"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")
print(len(vectors), "vectors")
