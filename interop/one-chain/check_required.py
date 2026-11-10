"""Shows that the held rule executed-as-approved:v1 requires authorisation_recheck and rationale_provenance.

No record of the one chain case has either dimension at anything but verified, so the case alone cannot show the
requirement. This runs the held rule on the case's own positive inputs (A1, A2, the decision record, the attempt's
digest), with the reference check's answer for one of the two dimensions replaced by not_checked or failed. The held
rule must give not_as_approved each time; a copy of the rule that ignores the two must give executed_as_approved,
which shows the check can tell the two apart.

Usage:
  ONE_CHAIN_REPO=<checkout at 9e1c7a0b> DPS_STANDARD=<checkout at 007f8c9> python3 interop/one-chain/check_required.py
Exit 0 when every line holds.
"""
import importlib.util
import json
import os
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("held_dps", HERE.parent.parent / "held" / "dps_007f8c9.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
R, REF = m.ExecutedAsApproved, m.REF

d = pathlib.Path(os.environ["ONE_CHAIN_REPO"]) / "interop" / "one-chain" / "out" / "positive"
L = lambda n: json.loads((d / n).read_text(encoding="utf-8"))
a1, a2, rec = L("action-binding-attachment-a1.json"), L("action-binding-attachment-a2.json"), L("decision-record.json")
att = [s for s in a2["stages"] if s.get("kind") == "attempt"][0]["spec_digest"]
vals = {"approval": a1, "attachment": a2, "record": rec, "approved_spec_digest": att, "attempted_spec_digest": att}

real = REF.check_attachment
ok = R.rerun(vals, {}) == "executed_as_approved"
print("positive, as published: %s" % R.rerun(vals, {}))
for dim in R.REQUIRED:
    for verdict in ("not_checked", "failed"):
        def replaced(a, r, _d=dim, _v=verdict):
            got = dict(real(a, r))
            got[_d] = (_v, ["replaced by check_required.py"])
            return got
        REF.check_attachment = replaced
        held = R.rerun(vals, {})
        req, dims = R.REQUIRED, REF.DIMENSIONS
        R.REQUIRED, REF.DIMENSIONS = (), tuple(x for x in dims if x not in req)
        ignoring = R.rerun(vals, {})
        R.REQUIRED, REF.DIMENSIONS = req, dims
        line_ok = held == "not_as_approved" and ignoring == "executed_as_approved"
        ok = ok and line_ok
        print("%-22s %-11s held rule: %-20s rule ignoring the two: %-20s %s"
              % (dim, verdict, held, ignoring, "ok" if line_ok else "WRONG"))
REF.check_attachment = real
sys.exit(0 if ok else 1)
