"""Held by the checker: the format rules of two Decision Provenance Standard formats, and the rule
executed-as-approved:v1, as one interop case pins them. Nothing here is part of draft-wright-verdict-record-02.

Sources, each read at a pinned commit; no code of any other checker of verdict records was read or copied:

- The rule: Laurent Lemonnier, dps-scitt-decision-layer, interop/verdict-record/README.md, section
  "The rule (executed-as-approved:v1)", lines 31-41, at commit 9e1c7a0b047129d71c5694995e0014eecdf2289c.
- Which checks of the two formats are format rules (step 2) and which belong to the rule (step 3): the same README,
  section "The format rules", lines 43-50, and its ambiguity log entry 5 (lines 151-158), same commit.
- What each check is: the Decision Provenance Standard at commit 007f8c99ec910564bac1c508b76c8ce8391fa11e, the
  commit the format URIs name. Its action binding extension (extensions/action-binding/README.md) publishes its
  reference check as extensions/action-binding/tests/run_checks.py (README lines 106, 117); this module loads that
  file from a checkout of the Standard at that commit (environment variable DPS_STANDARD) and calls it, as the rule's
  text says ("the Standard's action binding reference check"). The record seal is computed as that README line 124
  states: SHA-256 of the record with the seal_hash value replaced by 64 zeros.

Readings this module had to take where its sources are silent are marked R-n; the report lists them for the rule's
author (README, "Readings of executed-as-approved:v1").

STOPGAP, labelled: the rule is held by name for a URI that points at a branch (tree/main), not a commit. This module
binds that name to the text at 9e1c7a0b. Retires when the rule's author names a pinned text for the rule (or a
registry does, -02 Appendix B), at which point SOURCE names that text instead.
"""
import base64
import importlib.util
import json
import os
import pathlib
import subprocess

STANDARD_COMMIT = "007f8c99ec910564bac1c508b76c8ce8391fa11e"
STANDARD_TREE = "https://github.com/decision-provenance-standard/standard/tree/" + STANDARD_COMMIT
CASE_COMMIT = "9e1c7a0b047129d71c5694995e0014eecdf2289c"
CASE_README = ("https://github.com/Laurent-Lemonnier/dps-scitt-decision-layer/blob/" + CASE_COMMIT
               + "/interop/verdict-record/README.md")

SOURCE = {"rule": CASE_README + "#L31-L41",
          "format_split": CASE_README + "#L43-L50 and #L151-L158 (ambiguity 5)",
          "format_specifications": STANDARD_TREE,
          "reference_check": STANDARD_TREE + "/extensions/action-binding/tests/run_checks.py",
          "record_seal": "https://github.com/decision-provenance-standard/standard/blob/" + STANDARD_COMMIT
                         + "/extensions/action-binding/README.md#L124",
          "stopgap": "rule name points at tree/main; held as the text at " + CASE_COMMIT}


def _standard_root():
    root = os.environ.get("DPS_STANDARD")
    if not root:
        raise RuntimeError("set DPS_STANDARD to a checkout of the Standard at " + STANDARD_COMMIT)
    head = subprocess.run(["git", "-C", root, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != STANDARD_COMMIT:
        raise RuntimeError("DPS_STANDARD is at %r, not at %s" % (head, STANDARD_COMMIT))
    return pathlib.Path(root)


ROOT = _standard_root()
_spec = importlib.util.spec_from_file_location(
    "dps_action_binding_reference_check", ROOT / "extensions" / "action-binding" / "tests" / "run_checks.py")
REF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(REF)

from jsonschema import Draft202012Validator          # noqa: E402  (the Standard's own dependency)
from referencing import Registry, Resource           # noqa: E402
from referencing.jsonschema import DRAFT202012       # noqa: E402


def _schema(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _validator(path):
    """A validator for one of the Standard's schemas, with every schema of the Standard registered under its $id
    and under the URI a relative $ref resolves to.
    R-5: the decision-record schema ($id .../schemas/v5.0/decision-record.schema.json, file standard/v5.0/schemas/)
    refers to "../mode-drift/layer-4-attestation.schema.json", a path relative to its file, while that file's $id is
    .../schemas/v5.0/layer-4-attestation.schema.json. The $ref is resolved as a file path: the directory of the $id
    (.../schemas/v5.0/) stands for standard/v5.0/schemas/, so .../schemas/ stands for standard/v5.0/."""
    resources = []
    v5 = ROOT / "standard" / "v5.0"
    for p in (ROOT / "standard").rglob("*.schema.json"):
        s = _schema(p)
        r = Resource.from_contents(s, default_specification=DRAFT202012)
        if p.is_relative_to(v5):
            resources.append(("https://decisionprovenancestandard.org/schemas/" + p.relative_to(v5).as_posix(), r))
        if isinstance(s, dict) and "$id" in s:
            resources.append((s["$id"], r))
    return Draft202012Validator(_schema(path), registry=Registry().with_resources(resources))


ATTACHMENT_SCHEMA = _validator(ROOT / "extensions" / "action-binding" / "schemas" / "execution-evidence.schema.json")
RECORD_SCHEMA = _validator(ROOT / "standard" / "v5.0" / "schemas" / "decision-record.schema.json")


def _strict(b):
    return REF.strict_json(b)        # the Standard's reading: a member named twice at any depth is not read


class AttachmentFormat:
    """{STANDARD_TREE}/extensions/action-binding. Format rules, as the case's README lines 46-50 divide them:
    strict JSON; valid under the extension's schema; every specification digest recomputes from the bytes carried;
    the issuer's seal verifies under the DPS trust policy the checker holds (trust anchor set dps_trust_policy).
    R-1: a DPS item gives no upper time bound of its own (the seal's sealed_at is the issuer's statement), as the
    case's ambiguity log entry 6 reads it."""
    NAME = STANDARD_TREE + "/extensions/action-binding"

    @staticmethod
    def check_item(b, ctx):
        try:
            att = _strict(b)
        except ValueError as e:
            return False, "not strict JSON: %s" % e, None
        errs = list(ATTACHMENT_SCHEMA.iter_errors(att))
        if errs:
            return False, "not valid under the extension's schema: %s" % errs[0].message[:120], None
        got = REF.check_attachment(att, None)
        if got["specification_digests"][0] != "verified":
            return False, "a specification digest does not recompute", None
        policy = ctx["anchors"].get("dps_trust_policy")
        if policy is None:
            return False, "the checker holds no DPS trust policy", None
        sig = REF.check_issuer_signature(att, policy, REF.sig.check_policy(policy), [])
        if sig.get("status") != "verified":
            return False, "the issuer's seal: %s" % sig.get("status"), None
        return True, None, None


class RecordFormat:
    """{STANDARD_TREE}/standard/v5.0. Format rules, as the case's README lines 46-48 divide them: strict JSON;
    valid under the decision-record schema; seal_hash recomputes (extensions/action-binding/README.md line 124: the
    SHA-256 of the record with the seal_hash value replaced by 64 zeros; the value must occur once)."""
    NAME = STANDARD_TREE + "/standard/v5.0"

    @staticmethod
    def check_item(b, ctx):
        try:
            rec = _strict(b)
        except ValueError as e:
            return False, "not strict JSON: %s" % e, None
        errs = list(RECORD_SCHEMA.iter_errors(rec))
        if errs:
            return False, "not valid under the decision-record schema: %s" % errs[0].message[:120], None
        seal = rec.get("seal_hash") if isinstance(rec, dict) else None
        if not isinstance(seal, str):
            return False, "no seal_hash", None
        text = b.decode("utf-8")
        stored = '"seal_hash":"' + seal + '"'
        if text.count(stored) != 1:
            return False, "the record does not carry its seal_hash exactly once in the compact form", None
        if REF.sha256(text.replace(stored, REF.ZEROED).encode("utf-8")) != seal:
            return False, "seal_hash does not recompute", None
        return True, None, None


class ExecutedAsApproved:
    """executed-as-approved:v1, from the case's README lines 31-41 (commit 9e1c7a0b).

    Inputs: approval (A1, whole), attachment (A2, whole), record (the decision record, whole), approved_spec_digest,
    attempted_spec_digest. Result "executed_as_approved" when all four hold, else "not_as_approved":
      (a) the Standard's action binding reference check over attachment and record reports all eight dimensions
          verified;
      (b) A1's stages are the first stages of A2, unchanged, for the same decision_id;
      (c) A2 has exactly one attempt, whose digest equals the approved one and equals both digest inputs;
      (d) the result stage observes succeeded.
    R-2: "the approved one" in (c) is the approved_spec_digest of A1's one outcome stage whose outcome is approved;
         with no such stage, or more than one, (c) does not hold.
    R-3: "the result stage" in (d) is A2's one stage of kind result; with none, or more than one, (d) does not hold.
    R-4: an input of the wrong JSON type (an object input that is not an object, a digest that is not a string) is a
         wrong type in the sense of -02 line 422 (a FAIL of step 3), since the README states the inputs' meaning but
         not their types.
    REQUIRED: authorisation_recheck and rationale_provenance are required verified, by name. (a) already requires
         every dimension of the reference check, and these two are among them; they are named here because the
         Standard's steward states that this rule requires both (decision-provenance-standard/standard issue #106,
         comment of 10 Nov 2026, on the paragraph merged as pull request #108, which says which dimensions a checker
         requires "is its own choice"). The module refuses to load if the pinned reference check stops reporting
         either, so the requirement cannot lapse by a change to the Standard's list."""
    NAME = "https://github.com/Laurent-Lemonnier/dps-scitt-decision-layer/tree/main/interop/verdict-record#executed-as-approved-v1"
    INPUTS = ["approval", "approved_spec_digest", "attachment", "attempted_spec_digest", "record"]
    REQUIRED = ("authorisation_recheck", "rationale_provenance")

    @classmethod
    def input_problems(cls, values, names):
        if names != cls.INPUTS:
            return ["the rule's inputs are exactly " + ", ".join(cls.INPUTS)]
        out = []
        for n in ("approval", "attachment", "record"):
            if n in values and not isinstance(values[n], dict):
                out.append("input %s is not a JSON object" % n)
        for n in ("approved_spec_digest", "attempted_spec_digest"):
            if n in values and not isinstance(values[n], str):
                out.append("input %s is not a string" % n)
        return out

    @staticmethod
    def rerun(values, ctx):
        a1, a2, rec = values["approval"], values["attachment"], values["record"]
        record_raw = json.dumps(rec, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        got = REF.check_attachment(a2, record_raw)                                         # (a)
        required = all(got[d][0] == "verified" for d in ExecutedAsApproved.REQUIRED)
        a = required and all(got[d][0] == "verified" for d in REF.DIMENSIONS)
        s1, s2 = a1.get("stages"), a2.get("stages")                                         # (b)
        b = (isinstance(s1, list) and isinstance(s2, list) and len(s1) <= len(s2) and s2[:len(s1)] == s1
             and a1.get("decision_id") == a2.get("decision_id"))
        approved = [s for s in (s1 or []) if s.get("kind") == "outcome" and s.get("outcome") == "approved"]
        attempts = [s for s in (s2 or []) if s.get("kind") == "attempt"]                  # (c)
        c = (len(approved) == 1 and len(attempts) == 1
             and attempts[0].get("spec_digest") == approved[0].get("approved_spec_digest")
             == values["approved_spec_digest"] == values["attempted_spec_digest"])
        results = [s for s in (s2 or []) if s.get("kind") == "result"]                    # (d)
        d = len(results) == 1 and results[0].get("observed") == "succeeded"
        ctx.setdefault("rule_detail", {})[ExecutedAsApproved.NAME] = {
            "eight_dimensions": {k: got[k][0] for k in REF.DIMENSIONS}, "required": required,
            "a": a, "b": b, "c": c, "d": d}
        return "executed_as_approved" if (a and b and c and d) else "not_as_approved"


_lapsed = [d for d in ExecutedAsApproved.REQUIRED if d not in REF.DIMENSIONS]
if _lapsed:
    raise ImportError("the pinned reference check no longer reports %s, which executed-as-approved:v1 requires"
                      % ", ".join(_lapsed))

RULES = (ExecutedAsApproved,)
FORMATS = (AttachmentFormat, RecordFormat)
