"""Generates the test vectors for draft-wright-verdict-record-01.
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

POLICY = {"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "max_depth": 2}

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
      policy=POLICY, ub=UB, interp=None, item_bounds=None):
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
  policy={"judgement_kinds": ["model-decision"], "formats": [NEVER, VR], "max_depth": 2})
V("c06-item-does-not-verify", "4.3 step 2", "The item does not verify by its format.", C(rec(evidence=[ent(ITEM2, NEVER)])), "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(ITEM2,))
inner = C(rec(key="k-inner"))
outer = C(rec(key="k-outer", evidence=[ent(inner, VR)]))
IB_OK = {H(inner): "2026-11-01T11:00:00.000000Z"}
V("c07-cites-released-record", "4.3 step 2", "Cites a verdict record that is itself released, with an earlier upper time bound.", outer, "released", P3, items=(inner, ITEM1), item_bounds=IB_OK)
V("c08-beyond-depth", "4.3 step 2, 4.5", "Same, but the policy follows no citations (max_depth 0).", outer, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(inner, ITEM1), item_bounds=IB_OK,
  policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "max_depth": 0}, interp="I-5")
V("c09-cited-bound-later", "4.3 step 2", "The cited record's upper time bound is later than the citing record's.", outer, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(inner, ITEM1),
  item_bounds={H(inner): "2026-11-01T13:00:00.000000Z"})
bad_inner = C(rec(key="k-bad", check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "fail"}))
outer_bad = C(rec(key="k-outer2", evidence=[ent(bad_inner, VR)]))
V("c10-cites-refused-record", "4.3 step 2", "Cites a verdict record that is itself refused: the item does not verify.", outer_bad, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(bad_inner, ITEM1),
  item_bounds={H(bad_inner): "2026-11-01T11:00:00.000000Z"}, interp="I-6")
V("c11-claim-ref-not-in-evidence", "2.3", "body.claim.ref names an item that evidence does not list.",
  C(rec(body={"claim": {"ref": ent(ITEM2)}, "measured": 7, "threshold": 5})), "refused", None, interp="I-2")
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
APPX_CLAIM = b'{"made_by":"builder.example","statement":"Release 2.1 of example-service passed its acceptance suite."}'
APPX_REC = C({"act_time":"2026-10-23T10:00:00.000000Z","actor":{"id":"checker-7","model":"example-model","model_version":"1","type":"system"},
 "body":{"claim":{"ref":{"format":"application/json","sha256":H(APPX_CLAIM)}}},
 "check":{"result":"supported","rule":"judgement"},
 "evidence":[{"format":"application/json","sha256":H(APPX_CLAIM)},
  {"format":"https://datatracker.ietf.org/doc/draft-gruszka-signed-evaluation-receipts/","sha256":"0c964f45c450a0253fc09eb2316e6ad271944be201c46ebf2c5d40e529f35306"}],
 "key":"verdict-0001","kind":"model-decision","supersedes":None,"v":"verdict-record/1","version":1,"writer":"verifier.example"})
assert H(APPX_REC) == "2a85c94e39c56f50185b3b69b8f56026946364631799774a83b4f93399841c45"
assert H(APPX_CLAIM) == "f4747f1fa1ad63eaad90e41b587794f8f5c82f9215b9a8e23a6c204edabc7d48"
V("f01-appendix-a", "Appendix A", "The draft's own example. Its digest is 2a85c94e...; the second evidence item's bytes are not published, so an outside checker holds only the claim record.",
  APPX_REC, "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"}, items=(APPX_CLAIM,),
  policy={"judgement_kinds": ["model-decision"], "formats": [], "max_depth": 2}, interp="I-4")

# ---- Group F (cont.): Appendix A.2 (-02): rule re-run on cited delegation records ----
A2_FMT = "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/"
A2_RULE = "urn:example:verdict-record:rule:hop-continuity-attenuation:v1"
A2_HOP0 = b'{"expires_at":1793463600,"granted_scopes":["mcp:tool:erp.ledger.read","mcp:max_rows:100"],"issued_at":1793460000}'
A2_HOP1_POS = b'{"expires_at":1793463600,"granted_scopes":["mcp:tool:erp.ledger.read"],"issued_at":1793460000,"parent_record_hash":"1336337e88adc67853b80b4998363210dc5c0797cc7b7c722128cecc56a38c14"}'
A2_HOP1_N1 = b'{"expires_at":1793463600,"granted_scopes":["mcp:tool:erp.ledger.read","mcp:tool:erp.ledger.write"],"issued_at":1793460000,"parent_record_hash":"1336337e88adc67853b80b4998363210dc5c0797cc7b7c722128cecc56a38c14"}'
A2_HOP1_N2 = b'{"expires_at":1793463600,"granted_scopes":["mcp:tool:erp.ledger.read"],"issued_at":1793460000,"parent_record_hash":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"}'
assert H(A2_HOP0) == "1336337e88adc67853b80b4998363210dc5c0797cc7b7c722128cecc56a38c14"
assert H(A2_HOP1_POS) == "8886795d4403b5cd8820eb813ee0724f1d6d5d383124364b09cdc5020639e00c"
assert H(A2_HOP1_N1) == "4f94097c428f758a9f8119e0f35dd834f2d544e9ad31c06314361dadbf43ff29"
assert H(A2_HOP1_N2) == "968c3cd4a186b5d5324c55061aaa4cd0f214dd925ca2800b6afffac3b442a171"

def a2_rec(hop1_bytes, key="agenttrust/trace/hop-1"):
    return C({
        "act_time": "2026-10-31T18:00:00.000000Z",
        "actor": {"id": "agenttrust-trace-checker", "model": "none", "model_version": "0", "type": "system"},
        "body": {"claim": {"text": "hop[1] preserves SHA-256 parent_record_hash continuity and monotonic scope attenuation from hop[0]"}},
        "check": {
            "inputs": {
                "child_scopes": {"evidence": 1, "pointer": "/granted_scopes"},
                "parent_digest": {"evidence": 0},
                "parent_hash": {"evidence": 1, "pointer": "/parent_record_hash"},
                "parent_scopes": {"evidence": 0, "pointer": "/granted_scopes"}
            },
            "result": "attenuated_and_linked",
            "rule": A2_RULE
        },
        "evidence": [ent(A2_HOP0, A2_FMT), ent(hop1_bytes, A2_FMT)],
        "key": key,
        "kind": "check-run",
        "supersedes": None,
        "v": "verdict-record/1",
        "version": 1,
        "writer": "agenttrust-reference-verifier"
    })

A2_REC_POS = a2_rec(A2_HOP1_POS, "agenttrust/trace/hop-1")
assert H(A2_REC_POS) == "62017940a8ddddd5ddd7ff46c8ff2a6ce79dfcccb775d767b8dff8db0ebe19ed"
A2_REC_N1 = a2_rec(A2_HOP1_N1, "agenttrust/trace/hop-1-neg-widened-scope")
A2_REC_N2 = a2_rec(A2_HOP1_N2, "agenttrust/trace/hop-1-neg-broken-parent-hash")
A2_POLICY = {"judgement_kinds": ["model-decision"], "formats": [A2_FMT], "max_depth": 2}

V("f02-appendix-a2-released", "Appendix A.2, 4.3, 4.5",
  "Appendix A.2 positive example (digest 62017940...): hop[1] preserves parent_record_hash continuity and attenuates granted_scopes from hop[0]. Under signature-exempt JSON hop verification, the rule re-runs to attenuated_and_linked and the record is released.",
  A2_REC_POS, "released", P3, items=(A2_HOP0, A2_HOP1_POS), policy=A2_POLICY)
V("f03-appendix-a2-widened-scope", "Appendix A.2, 4.3 step 3, 4.4",
  "Appendix A.2 negative vector N1 (scope widening): hop[1] appends 'mcp:tool:erp.ledger.write' not present in hop[0].granted_scopes while the record states 'attenuated_and_linked'. The rule re-runs to 'not_attenuated_or_not_linked' and step 3 FAILs (refused).",
  A2_REC_N1, "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"}, items=(A2_HOP0, A2_HOP1_N1), policy=A2_POLICY)
V("f04-appendix-a2-broken-parent-hash", "Appendix A.2, 4.3 step 3, 4.4",
  "Appendix A.2 negative vector N2 (broken parent_record_hash): hop[1] attenuates scopes but alters parent_record_hash to 'ffff...ffff', breaking digest continuity from hop[0]. The rule re-runs to 'not_attenuated_or_not_linked' and step 3 FAILs (refused).",
  A2_REC_N2, "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"}, items=(A2_HOP0, A2_HOP1_N2), policy=A2_POLICY)
V("f05-appendix-a2-withheld-child-hop", "Appendix A.2, 4.3 steps 2 and 3, 4.4",
  "Appendix A.2 negative vector N3 (withheld child hop): the positive Appendix A.2 record (digest 62017940...) is presented with hop[0] only; evidence[1] (hop[1]) is not held, so steps 2 and 3 are NOT RUN and the record is held.",
  A2_REC_POS, "held", {"1": "PASS", "2": "NOT RUN", "3": "NOT RUN"}, items=(A2_HOP0,), policy=A2_POLICY)

# ---- Group E: policy ----
V("e01-invalid-policy", "4.4, 4.5", "The checker's policy is invalid: no verdict.", base, "no verdict", None,
  policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE], "max_depth": -1}, interp="I-8")

for v in vectors:
    with open(os.path.join(OUT, v["name"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False, sort_keys=False)
        f.write("\n")
print(len(vectors), "vectors")
