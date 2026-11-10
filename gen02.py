"""Generates the vectors added for draft-wright-verdict-record-02 (g01-g30, h01-h04).

As in gen.py, each vector's expected outcome is written here by hand from the draft text, with the lines of
https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt it rests on and the duty ids of DUTIES.md, and is
NOT computed by the reference checker. gen.py (the -01 vectors a01-f01) is unchanged.
"""
import base64
import hashlib
import json

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
POLICY = {"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR], "max_depth": 2}
EO = dict(POLICY, inputs_from_evidence_only=True)

JITEM = b'{"m":5,"n":7,"s":"seven"}'          # a JSON evidence item, not canonical-relevant
OTHER = b"evidence item two: an opaque item that is not JSON"
NV = b"evidence item three: an item whose format's rules are never met"
P3 = {"1": "PASS", "2": "PASS", "3": "PASS"}
HELD3 = {"1": "PASS", "2": "NOT RUN", "3": "NOT RUN"}

def ent(b, fmt=OPAQUE): return {"format": fmt, "sha256": H(b)}

def rec(**over):
    r = {"v": "verdict-record/1", "kind": "check-run", "key": "k-0002", "version": 1,
         "supersedes": None, "writer": "issuer.example",
         "actor": {"type": "system", "id": "runner-1", "model": "none", "model_version": "0"},
         "act_time": "2026-11-01T10:00:00.000000Z",
         "evidence": [ent(JITEM)],
         "check": {"rule": AT_LEAST, "inputs": {"value": {"evidence": 0, "pointer": "/n"},
                                                "min": {"evidence": 0, "pointer": "/m"}}, "result": "pass"},
         "body": {"claim": {"text": "The value n of the cited item is at least its value m."}}}
    for k, v in over.items():
        if v is None and k != "supersedes":
            r.pop(k, None)
        else:
            r[k] = v
    return r

def body_rec(**over):
    r = rec(check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "pass"},
            body={"claim": {"text": "The measured value is at least the threshold."}, "measured": 7, "threshold": 5})
    r.update(over)
    return r

def inputs(**kw):
    return {"rule": AT_LEAST, "inputs": kw, "result": "pass"}

vectors = []
def V(name, lines, duties, desc, record, state, steps=None, items=(JITEM,), policy=POLICY, interp=None,
      hold=None, body_inputs_read=None, not_relied_on=None, raw=None, no_step_runs=False):
    rb = raw if raw is not None else C(record)
    v = {"name": name, "section": "draft-wright-verdict-record-02 lines " + lines, "duties": duties,
         "description": desc, "record_b64": B(rb), "record_sha256": H(rb),
         "evidence_items": [{"b64": B(b)} for b in items], "upper_time_bound": UB, "policy": policy,
         "policy_sha256": H(C(policy)), "expected": {"state": state, "steps": steps}}
    if body_inputs_read is not None: v["expected"]["body_inputs_read"] = body_inputs_read
    if not_relied_on is not None: v["expected"]["not_relied_on"] = not_relied_on
    if no_step_runs: v["expected"]["no_step_runs"] = True
    if interp: v["depends_on_interpretation"] = interp
    if hold: v["hold"] = hold
    vectors.append(v)

# ---- Group G: inputs bound to evidence, the evidence-only policy, the report, members (Appendix C of -02)
V("g01-bound-pointer-released", "285-298, 415-427", ["D14", "D16", "D29", "D34"],
  "Both inputs bound to one JSON item by JSON Pointer; the re-run equals the stated result.", rec(), "released", P3,
  body_inputs_read=[])
V("g02-bound-digest-released", "292-295", ["D15"],
  "An input bound to an item with no pointer is the digest the checker computes; the other reads that digest from a second item.",
  rec(evidence=[ent(OTHER), ent(C({"digest": H(OTHER)}))],
      check={"rule": EQUALS, "inputs": {"a": {"evidence": 0}, "b": {"evidence": 1, "pointer": "/digest"}}, "result": "equal"}),
  "released", P3, items=(OTHER, C({"digest": H(OTHER)})))
V("g03-body-inputs-named", "379-382, 438-439", ["D38"],
  "Inputs read from body under the default policy: released, and the report names each input read from body.",
  body_rec(), "released", P3, body_inputs_read=["min", "value"])
V("g04-evidence-only-body-input", "425-427, 476-482", ["D33", "D41"],
  "The same record under a policy that reads inputs from evidence only: an input read from body makes step 3 NOT RUN.",
  body_rec(), "held", {"1": "PASS", "2": "PASS", "3": "NOT RUN"}, policy=EO)
V("g05-evidence-only-bound", "425-427, 476-482", ["D33", "D41"],
  "Inputs bound to evidence under the evidence-only policy: the rule re-runs.", rec(), "released", P3, policy=EO)
V("g06-bound-item-not-held", "397-400, 417-419", ["D24", "D30"],
  "The item the inputs are bound to is not held: step 2 NOT RUN, and step 3 NOT RUN.", rec(), "held", HELD3, items=())
V("g07-bound-item-not-relied-on", "402-404, 417-419", ["D25", "D30"],
  "The item is held but its format's rules are not met, so step 2 does not rely on it, and step 3 is NOT RUN.",
  rec(evidence=[ent(JITEM, NEVER)]), "held", HELD3)
V("g08-binding-extra-member", "292-293, 419-421", ["D14", "D31"],
  "A binding object with a member other than evidence and pointer: a FAIL of step 3.",
  rec(check=inputs(value={"evidence": 0, "pointer": "/n", "index": 1}, min={"evidence": 0, "pointer": "/m"})),
  "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"})
V("g09-no-such-evidence-entry", "419-420", ["D31"],
  "An input bound to an evidence index the record does not have: a FAIL of step 3.",
  rec(check=inputs(value={"evidence": 3, "pointer": "/n"}, min={"evidence": 0, "pointer": "/m"})),
  "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"})
V("g10-pointer-does-not-resolve", "421", ["D16", "D31"],
  "A JSON Pointer that does not resolve in the item: a FAIL of step 3, not a result of the rule.",
  rec(check=inputs(value={"evidence": 0, "pointer": "/x"}, min={"evidence": 0, "pointer": "/m"})),
  "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"})
V("g11-item-not-json", "296-298, 421-422", ["D16", "D31"],
  "A pointer into an item that is not JSON: a FAIL of step 3.",
  rec(evidence=[ent(OTHER)], check=inputs(value={"evidence": 0, "pointer": "/n"}, min={"evidence": 0, "pointer": "/m"})),
  "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"}, items=(OTHER,))
V("g12-not-run-and-fail", "423-424", ["D32"],
  "One input bound to an item not held (NOT RUN), the other to a pointer that does not resolve (FAIL): the step FAILs.",
  rec(evidence=[ent(JITEM), ent(OTHER)],
      check=inputs(value={"evidence": 1, "pointer": "/n"}, min={"evidence": 0, "pointer": "/x"})),
  "refused", {"1": "PASS", "2": "NOT RUN", "3": "FAIL"})
V("g13-bound-input-wrong-type", "422-423", ["D31"],
  "A pointer that resolves to a string where the rule takes an integer: a FAIL of step 3.",
  rec(check=inputs(value={"evidence": 0, "pointer": "/s"}, min={"evidence": 0, "pointer": "/m"})),
  "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"})
V("g14-policy-evidence-only-not-boolean", "470-474", ["D41", "D42"],
  "The evidence-only statement written as a string: the policy is invalid and the checker gives no verdict.",
  rec(), "no verdict", None, policy=dict(POLICY, inputs_from_evidence_only="yes"), interp="O-2")
V("g15-policy-unknown-member", "467-474", ["D42"],
  "A policy with a member the checker does not know: lines 472-474 name no such ground for invalidity, so the member "
  "is read past and the policy runs without it; the record is released as under the base policy.",
  rec(), "released", P3, policy=dict(POLICY, max_evidence_age_seconds=3600), interp="O-2")
V("g16-policy-citation-depth", "467-469", ["D41"],
  "The depth stated as citation_depth, the name a second checker chose: read as the depth.",
  rec(), "released", P3, policy={"judgement_kinds": ["model-decision"], "formats": [OPAQUE], "citation_depth": 0},
  interp="O-1")
V("g17-policy-two-depths", "467-474", ["D42"],
  "The depth stated twice, under both names: invalid, no verdict.",
  rec(), "no verdict", None, policy=dict(POLICY, citation_depth=2), interp="O-1")
V("g18-step2-names-every-entry", "397-404", ["D24", "D25"],
  "Two entries step 2 cannot rely on, for two reasons: step 2 is NOT RUN and names both.",
  body_rec(evidence=[ent(NV, NEVER), ent(OTHER)]), "held", {"1": "PASS", "2": "NOT RUN", "3": "PASS"},
  items=(NV,), not_relied_on=2, interp="O-3")
V("g19-act-time-form", "213-214, 216-219", ["D05", "D08"],
  "act_time without six fraction digits: bytes that break Section 2.1 are refused before any step.",
  body_rec(act_time="2026-11-01T10:00:00Z"), "refused", None, no_step_runs=True)
V("g20-version-zero", "216-219, 250-251", ["D08", "D11"],
  "version 0: a record that breaks Section 2.2 other than in evidence and check is refused before any step.",
  body_rec(version=0), "refused", None, no_step_runs=True)
V("g21-supersedes-on-version-1", "253-254", ["D11"],
  "version 1 with a digest in supersedes: refused before any step.",
  body_rec(supersedes=H(b"an earlier record")), "refused", None, no_step_runs=True)
V("g22-version-2-supersedes-null", "253-254", ["D11"],
  "version 2 with supersedes null: refused before any step.", body_rec(version=2), "refused", None, no_step_runs=True)
V("g23-version-2-supersedes-digest", "253-254, 546-549", ["D11"],
  "version 2 naming the digest of a version 1 the checker does not hold: no step reads supersedes, released.",
  rec(version=2, supersedes=H(b"an earlier record")), "released", P3)
V("g24-key-empty", "247-248", ["D11"], "An empty key: refused before any step.", body_rec(key=""), "refused", None, no_step_runs=True)
V("g25-actor-person-with-model", "259-261", ["D11"],
  "An actor of type person with the members only a system has: refused before any step.",
  body_rec(actor={"type": "person", "id": "p-1", "model": "none", "model_version": "0"}), "refused", None, no_step_runs=True)
V("g26-v-other-value", "240, 216-219", ["D11"],
  "v other than the one value -02 defines: refused before any step.",
  body_rec(v="verdict-record/2"), "refused", None, no_step_runs=True, interp="O-13")
V("g27-check-extra-member", "271-273, 386-388", ["D13", "D23"],
  "check with a member other than rule, inputs and result: step 1 FAILs.",
  rec(check=dict(rec()["check"], note="x")), "refused", {"1": "FAIL", "2": "PASS", "3": "PASS"})
V("g28-claim-text-and-ref", "310-313", ["D17"],
  "body.claim with both text and ref: refused before any step.",
  body_rec(body={"claim": {"text": "t", "ref": ent(JITEM)}, "measured": 7, "threshold": 5}), "refused", None, no_step_runs=True, interp="O-14")
V("g29-body-not-object", "304-306, 216-219", ["D11"], "body as an array: refused before any step.",
  body_rec(body=[]), "refused", None, no_step_runs=True)
V("g30-claim-text-not-string", "310-313", ["D17"], "body.claim.text as an integer: refused before any step.",
  body_rec(body={"claim": {"text": 7}, "measured": 7, "threshold": 5}), "refused", None, no_step_runs=True, interp="O-14")

# ---- Group H: Appendix A.2, its record and the four outcomes it predicts (lines 1185-1194)
DURGA = "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/"
PARENT = b'{"expires_at":1793463600,"granted_scopes":["mcp:tool:erp.ledger.read","mcp:max_rows:100"],"issued_at":1793460000}'
def child(scopes):
    return C({"expires_at": 1793463600, "granted_scopes": scopes, "issued_at": 1793460000,
              "parent_record_hash": H(PARENT)})
CHILD = child(["mcp:tool:erp.ledger.read"])
def a2(child_bytes):
    return {"act_time": "2026-10-31T18:00:00.000000Z",
            "actor": {"id": "agenttrust-trace-checker", "model": "none", "model_version": "0", "type": "system"},
            "body": {"claim": {"text": "hop[1] preserves SHA-256 parent_record_hash continuity and monotonic scope attenuation from hop[0]"}},
            "check": {"inputs": {"child_scopes": {"evidence": 1, "pointer": "/granted_scopes"},
                                 "parent_digest": {"evidence": 0},
                                 "parent_hash": {"evidence": 1, "pointer": "/parent_record_hash"},
                                 "parent_scopes": {"evidence": 0, "pointer": "/granted_scopes"}},
                      "result": "attenuated_and_linked",
                      "rule": "urn:example:verdict-record:rule:hop-continuity-attenuation:v1"},
            "evidence": [{"format": DURGA, "sha256": H(PARENT)}, {"format": DURGA, "sha256": H(child_bytes)}],
            "key": "agenttrust/trace/hop-1", "kind": "check-run", "supersedes": None, "v": "verdict-record/1",
            "version": 1, "writer": "agenttrust-reference-verifier"}
# -02 lines 1095-1096, 1102-1104 and 1183 give these digests; the generator refuses to write if they differ.
assert H(PARENT) == "1336337e88adc67853b80b4998363210dc5c0797cc7b7c722128cecc56a38c14"
assert H(CHILD) == "8886795d4403b5cd8820eb813ee0724f1d6d5d383124364b09cdc5020639e00c"
assert H(C(a2(CHILD))) == "62017940a8ddddd5ddd7ff46c8ff2a6ce79dfcccb775d767b8dff8db0ebe19ed"
APOL = {"judgement_kinds": [], "formats": [DURGA], "max_depth": 0, "inputs_from_evidence_only": True}
RULE = ["appendix_a2_rule.py"]
V("h01-a2-hops-without-signature-released", "1187-1190", ["D14", "D15", "D16", "D33", "A.2"],
  "Appendix A.2's record, both hops held, under hop format rules that need no signature: released.",
  a2(CHILD), "released", P3, items=(PARENT, CHILD), policy=APOL, hold=RULE + ["appendix_a2_hops_parse_only.py"],
  interp="I-9")
V("h02-a2-hops-signature-required-held", "1185-1187, 417-419", ["D25", "D30", "A.2"],
  "The same, under hop format rules that require the signature the hops lack: held, at step 2.",
  a2(CHILD), "held", HELD3, items=(PARENT, CHILD), policy=APOL,
  hold=RULE + ["appendix_a2_hops_signature_required.py"])
WIDE = child(["mcp:tool:erp.ledger.read", "mcp:tool:erp.ledger.write"])
V("h03-a2-child-widened-refused", "1190-1192", ["D34", "A.2"],
  "The child hop widens the scopes; the record (re-made to cite it) still states attenuated_and_linked: refused at step 3.",
  a2(WIDE), "refused", {"1": "PASS", "2": "PASS", "3": "FAIL"}, items=(PARENT, WIDE), policy=APOL,
  hold=RULE + ["appendix_a2_hops_parse_only.py"])
V("h04-a2-child-not-held", "1192-1193", ["D24", "D30", "A.2"],
  "Appendix A.2's record with the child hop not held: held.",
  a2(CHILD), "held", HELD3, items=(PARENT,), policy=APOL, hold=RULE + ["appendix_a2_hops_parse_only.py"])

for v in vectors:
    with open(v["name"] + ".json", "w", encoding="utf-8") as f:
        json.dump(v, f, indent=2, ensure_ascii=False)
        f.write("\n")
print(len(vectors), "vectors written")
