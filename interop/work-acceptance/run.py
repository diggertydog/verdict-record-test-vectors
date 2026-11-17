"""Runs the reference checker on the work-acceptance case (babyblueviper1/preaction-governance-conformance,
examples/verdict-record-work-acceptance, at CASE_COMMIT) and sets each result beside the result the case states.

This is a presenter, not a change to the checker. Per case it hands vrcheck.py: the verdict record's exact bytes, as
published; the cited evidence item (a signed work-acceptance record, or the case's tampered copy of it); the case's
policy (policy.json) and upper time bound (cases.json); the trust anchors {"invinoveritas-checker-keys": the case's key
document}; and, as held inputs, held/test_suite.py and held/invinoveritas_work_acceptance.py (the format and rule of
the case's README, sections "Format" and "Rule"). What the case states is read from its README table only.

Usage:
  git clone https://github.com/babyblueviper1/preaction-governance-conformance wa
  git -C wa checkout 076e40579aa6fa41899d552360ab771384e57a1e
  WA_CASE=wa python3 interop/work-acceptance/run.py      # needs the Python package cryptography
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOP)
import vrcheck  # noqa: E402

CASE_COMMIT = "076e40579aa6fa41899d552360ab771384e57a1e"
STATED = {"p1-pass": "released", "n1-stated-fail": "refused", "n2-tampered-item": "held", "n3-key-not-held": "held"}


def main():
    root = os.environ.get("WA_CASE") or sys.exit("set WA_CASE to a checkout of babyblueviper1/preaction-governance-conformance")
    d = os.path.join(root, "examples", "verdict-record-work-acceptance")
    cases = json.load(open(os.path.join(d, "cases.json")))
    policy = json.load(open(os.path.join(d, cases["policy"])))
    held = vrcheck.load_held([vrcheck.TEST_SUITE, os.path.join(TOP, "held", "invinoveritas_work_acceptance.py")])
    rows, ok = [], True
    for c in cases["cases"]:
        rb = open(os.path.join(d, c["verdict_record"]), "rb").read()
        ib = open(os.path.join(d, c["evidence_item"]), "rb").read()
        anchors = {"invinoveritas-checker-keys": json.load(open(os.path.join(d, c["trust_anchors"])))}
        rep = vrcheck.run(rb, policy, cases["upper_time_bound"], {vrcheck.sha256hex(ib): {"bytes": ib}}, held, anchors)
        row = {"case": c["case"], "record_sha256": vrcheck.sha256hex(rb), "state": rep.get("state"),
               "steps": rep.get("steps"), "stated": STATED.get(c["case"])}
        row["agrees"] = row["state"] == row["stated"]
        ok &= row["agrees"]
        rows.append(row)
        print("%-18s %-9s stated %-9s %s" % (c["case"], row["state"], row["stated"], json.dumps(row["steps"])))
    json.dump({"case_commit": CASE_COMMIT, "results": rows}, open(os.path.join(HERE, "results.json"), "w"), indent=1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
