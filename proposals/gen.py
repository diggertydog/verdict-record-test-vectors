"""Generates the proposal cases: open questions for IETF 127, each written as a case a checker can run.

Each case states two things, by hand, and neither is computed by a checker:
- expected_under_02: what draft-wright-verdict-record-02 gives today, with the section it rests on;
- proposed: what the proposal named in the case would change, in prose. These are proposals, not draft text.

Run from the repository root:  python3 proposals/gen.py
"""
import base64, hashlib, json, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)))

def C(o):
    return json.dumps(o, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
def H(b): return hashlib.sha256(b).hexdigest()
def B(b): return base64.b64encode(b).decode()

OPAQUE = "urn:example:verdict-record:format:opaque"
NEVER = "urn:example:verdict-record:format:never-verifies"
VR = "verdict-record/1"
ATTEST = "urn:example:verdict-record:format:provider-attestation"
PROOF = "urn:example:verdict-record:format:inference-proof"
SALTED = "urn:example:verdict-record:format:salted-commitment"
AT_LEAST = "urn:example:verdict-record:rule:at-least"
UB = "2026-11-01T12:00:00.000000Z"

POLICY = {"judgement_kinds": ["model-decision"], "formats": [OPAQUE, NEVER, VR, ATTEST, PROOF], "citation_depth": 2}

ITEM1 = b"evidence item one: an opaque test item"

def ent(b, fmt=OPAQUE): return {"format": fmt, "sha256": H(b)}

class _Del: pass
DEL = _Del()

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

def decision(**over):
    base = dict(kind="model-decision",
                actor={"type": "system", "id": "assessor-1", "model": "example-model", "model_version": "1"},
                check={"rule": "judgement", "result": "supported"},
                body={"claim": {"text": "The request meets the stated policy."}})
    base.update(over)
    return rec(**base)

cases = []
def P(name, proposal, question, desc, record_bytes, expected_state, expected_steps, proposed,
      items=(ITEM1,), item_bounds=None, policy=POLICY, ub=UB, rests_on=""):
    its = []
    for b in items:
        e = {"b64": B(b)}
        if item_bounds and H(b) in item_bounds: e["upper_time_bound"] = item_bounds[H(b)]
        its.append(e)
    cases.append({
        "name": name, "proposal": proposal, "open_question": question, "description": desc,
        "record_b64": B(record_bytes), "record_sha256": H(record_bytes),
        "evidence_items": its, "upper_time_bound": ub, "policy": policy, "policy_sha256": H(C(policy)),
        "expected_under_02": {"state": expected_state, "steps": expected_steps, "rests_on": rests_on},
        "proposed": proposed,
        "status": "PROPOSAL: not draft text. For discussion at IETF 127."})

P3 = {"1": "PASS", "2": "PASS", "3": "PASS"}
HELD2 = {"1": "PASS", "2": "NOT RUN", "3": "PASS"}

# p01 / p02 -- which model gave the answer, and how strongly that is shown
r01 = C(decision())
P("p01-model-declared",
  "V13-06 binding strength",
  "Should a checker report how strongly a record shows which model produced it, derived from what is attached rather than from what the writer says?",
  "A model decision that names its model only in actor.model, with nothing attached about the model.",
  r01, "released", P3,
  "Same state. The report adds: model binding 'declared' -- the writer's statement only, nothing attached shows it. The record carries no new member; the strength is derived by the checker.",
  rests_on="Sections 2.2 (actor), 4.2 (a statement by the issuer alone can be reported but cannot make a step pass)")

ATT = C({"model": "example-model", "model_version": "1", "statement": "This model served the request.", "signed_by": "provider.example"})
r02 = C(decision(evidence=[ent(ITEM1), ent(ATT, ATTEST)]))
P("p02-model-attested",
  "V13-06 binding strength",
  "As p01. Under -02 this case and p01 give the same report, which is the gap.",
  "The same decision with a provider's signed statement about the model attached as evidence (test format: provider-attestation, which always verifies here).",
  r02, "released", P3,
  "Same state. The report adds: model binding 'attested' -- a provider's statement about the model is attached and verifies under its format. A policy could require at least 'attested' for kinds that need it.",
  items=(ITEM1, ATT), rests_on="Sections 2.2, 4.3 step 2, 7")

PROOF_ITEM = C({"model_digest": "00" * 32, "output_digest": H(r01), "proof": "test-only"})
r03 = C(decision(evidence=[ent(ITEM1), ent(PROOF_ITEM, PROOF)]))
P("p03-model-proof-after-reply",
  "V13-06 binding strength (with the FlashProve correction)",
  "When a proof of which model ran is produced only after the answer was given and relied on, should it count as 'proven' for that record?",
  "The same decision citing a proof of inference whose own upper time bound is later than the record's (test format: inference-proof, which always verifies here). Some serving set-ups send the answer before any proof exists.",
  r03, "held", HELD2,
  "Same as -02, with no new text: Section 4.3 step 2 already refuses to rely on an item whose upper time bound is later than the citing record's. 'Proven' is reported only when the proof's bound is not later than the record's.",
  items=(ITEM1, PROOF_ITEM), item_bounds={H(PROOF_ITEM): "2026-11-01T13:00:00.000000Z"},
  rests_on="Section 4.3 step 2 (upper time bound of a cited item)")

# p04 -- a cited record has a later version
v1 = C(rec(key="k-inner"))
v2 = C(rec(key="k-inner", version=2, supersedes=H(v1),
           body={"claim": {"text": "The measured value is at least the threshold."}, "measured": 3, "threshold": 5},
           check={"rule": AT_LEAST, "inputs": {"value": "measured", "min": "threshold"}, "result": "fail"}))
outer4 = C(rec(key="k-outer", evidence=[ent(v1, VR)]))
P("p04-cites-superseded-version",
  "V13-07 when a result stops counting; -02 Appendix B open question on supersedes",
  "When a checker holds a later version of a record that another record cites, what should it report about the citing record?",
  "An outer record cites version 1 of k-inner. The checker also holds version 2 of k-inner, which supersedes version 1 and reaches the opposite result. Both versions are released on their own.",
  outer4, "released", P3,
  "Same state: version 1 remains a true record of what was decided on its evidence, and no step may rely on the absence of a later version. The report adds that a later version of a cited record is held, naming it, so a reader sees the result has been reassessed. Reassessment of the outer record is a new record (Section 6).",
  items=(v1, v2, ITEM1), item_bounds={H(v1): "2026-11-01T11:00:00.000000Z", H(v2): "2026-11-01T11:30:00.000000Z"},
  rests_on="Sections 4.3 step 2, 6, Appendix B")

# p05 -- old evidence
inner5 = C(rec(key="k-old"))
outer5 = C(rec(key="k-outer5", evidence=[ent(inner5, VR)]))
P("p05-evidence-age",
  "V13-07 when a result stops counting (maximum evidence age as the reader's policy)",
  "Should a checker's policy be able to set a maximum age for cited evidence, measured between the record's upper time bound and each item's, never by the checker's clock?",
  "An outer record cites a record whose upper time bound is two years earlier than its own.",
  outer5, "released", P3,
  "With the base policy: same state. With a policy member such as max_evidence_age (not defined in -02, so a -02 checker reads past it and gives the same state as under the base policy), step 2 would be NOT RUN for an item older than the limit, and the state held. Two checkers holding the same inputs still give the same result, because no clock is read.",
  items=(inner5, ITEM1), item_bounds={H(inner5): "2024-11-01T11:00:00.000000Z"},
  rests_on="Sections 4.1 (no step reads the checker's clock), 4.5")

# p06 -- a commitment to personal data, checkable only by a party that holds the salt
SALT = b"test-only salt, held by the data controller"
ERASED = b"test-only personal data item"
COMMIT = C({"commitment": H(SALT + ERASED), "scheme": "sha256(salt||item)", "stores_covered": ["chat-log", "memory-summary", "vector-index"], "probe_recovered": False})
r06 = C(rec(kind="model-decision", check={"rule": "judgement", "result": "erasure-confirmed"},
            body={"claim": {"text": "The forget request was carried out in the stores covered."}},
            evidence=[ent(COMMIT, SALTED)]))
P("p06-salted-commitment",
  "V13-08 erasure receipt; V13-05 cross-border fingerprints",
  "Should a salted commitment be an evidence format in its own right, so a record can point at personal data without carrying it, and only a party holding the salt can check what it points at?",
  "A record of a completed forget request cites a commitment to the item, not the item. The checker's policy does not list the salted-commitment format.",
  r06, "held", HELD2,
  "Same state for a checker without the salt, by design: the core digest rule is unchanged and -02's 'no salted or hiding form of digest' stays true of the core. A checker that holds the salt and lists the format can verify the commitment and release the record. The salt, and anything a fingerprint of personal data counts as, stays with the controller.",
  items=(COMMIT,), rests_on="Sections 2.1 (no salted digest), 4.3 step 2, 4.5")

# p07 -- a refusal that cites nothing
r07 = C(decision(check={"rule": "judgement", "result": "deny"}, evidence=[],
                 body={"claim": {"text": "The agent's request to send the payment is allowed."}}))
P("p07-negative-judgement-no-cause",
  "V13-10 a refusal or held verdict carries its cause",
  "Should a negative judgement (a refusal) be required to cite at least one item it rests on, so a bare 'deny' cannot be released?",
  "A model decision refuses a request, by judgement, and cites no evidence at all.",
  r07, "released", P3,
  "Not released: a negative result reached by judgement with no evidence would fail a new requirement (step 2 FAIL, state refused), or a policy could list result values that need evidence. A mechanical rule's refusal already carries its cause, because the rule and its inputs are in the record.",
  items=(), rests_on="Sections 4.3 steps 1-3; -01 open point I-3 (empty evidence passes step 2)")

# p08 -- a verdict over a published authority history (IronTrellis), carrying the refusal's cause
IT_COMMIT = "a2c487f6cd3afee2e35c7f7f1b64c9d966bf8387"
IT_RAW = "https://raw.githubusercontent.com/zerohourzulu/irontrellis/" + IT_COMMIT + "/conformance/v2-g3/"
IT_SUITE_FMT = "https://github.com/zerohourzulu/irontrellis/tree/" + IT_COMMIT + "/conformance/v2-g3#vectors"
IT_HIST_FMT = "https://github.com/zerohourzulu/irontrellis/tree/" + IT_COMMIT + "/conformance/v2-g3#histories"
IT_RULE = "https://github.com/zerohourzulu/irontrellis/tree/" + IT_COMMIT + "/conformance#authorization"
SUITE_SHA = "6e97be5b26e39cae691c260787abc2f74790506348f6e62aaa25a3d5c5f8be34"   # vectors.json, 1,388,651 bytes
HIST_SHA = "307fdb7ceb170a7f14341a6f1ca8b54cbb7facc9e87a5e72d1e82bf4f8955777"    # histories/budget-v2.json, 39,414 bytes
IT_RESULT = {"budgetId": None, "code": "AMOUNT_EXCEEDED", "controllingAuthorityIds": None, "decision": "DENY",
             "failureCodes": ["AMOUNT_EXCEEDED"], "scopeAssurance": "REPLAY_VERIFIED"}
r08 = C(rec(key="irontrellis-v2-g3-authority-denial-precedes-budgets",
            evidence=[{"format": IT_SUITE_FMT, "sha256": SUITE_SHA}, {"format": IT_HIST_FMT, "sha256": HIST_SHA}],
            check={"rule": IT_RULE,
                   "inputs": {"case": {"evidence": 0, "pointer": "/57"}, "history": {"evidence": 1, "pointer": ""}},
                   "result": IT_RESULT},
            body={"claim": {"text": "Replaying the authority history refuses the request in conformance case authorization/v2/authority-denial-precedes-budgets, with cause AMOUNT_EXCEEDED."}}))
IT_POLICY = {"judgement_kinds": [], "formats": [IT_SUITE_FMT, IT_HIST_FMT], "citation_depth": 0}
cases.append({
    "name": "p08-irontrellis-refusal",
    "proposal": "V13-09 one evidence slot; V13-10 a refusal carries its cause. Offered to the IronTrellis author on the AUDIT list, 6 Nov 2026.",
    "open_question": "Does a verdict record carry an authority-history refusal, with its cause, so that any checker holding the history's replay re-derives it?",
    "description": "A check-run verdict whose rule is IronTrellis's own authorization replay, at a pinned commit. Its two inputs are bound to evidence: the conformance case (vectors.json, entry 57) and the 40-event history it names. The stated result is the case's published expected answer: DENY, cause AMOUNT_EXCEEDED. The evidence items are too large to embed, so each is cited by digest with the URL of its exact bytes.",
    "record_b64": B(r08), "record_sha256": H(r08),
    "evidence_items": [],
    "evidence_fetch": [{"url": IT_RAW + "vectors.json", "sha256": SUITE_SHA, "bytes": 1388651},
                       {"url": IT_RAW + "histories/budget-v2.json", "sha256": HIST_SHA, "bytes": 39414}],
    "upper_time_bound": UB, "policy": IT_POLICY, "policy_sha256": H(C(IT_POLICY)),
    "expected_under_02": {
        "state": "held", "steps": {"1": "PASS", "2": "PASS", "3": "NOT RUN"},
        "rests_on": "Sections 2.2 (inputs bound to evidence by JSON Pointer), 4.3 steps 2 and 3. For a checker that holds both items (fetched and matched by digest) and whose format rules accept them, but that does not hold the IronTrellis rule: step 3 NOT RUN, naming the rule. A checker that holds the rule re-runs it: released if the replay gives this result, refused if it does not."},
    "proposed": "No change to -02 is needed for this case: it is the evidence slot doing its job. It shows a refusal carrying its cause mechanically, because the rule and its inputs are in the record. The question for the IronTrellis author: is this the right rule name and input binding for a third party to re-run his replay?",
    "status": "PROPOSAL: not draft text. For discussion at IETF 127."})

for c in cases:
    with open(os.path.join(OUT, c["name"] + ".json"), "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2, ensure_ascii=False)
        f.write("\n")
print(len(cases), "cases")
