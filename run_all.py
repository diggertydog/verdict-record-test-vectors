"""Runs every vector (a01-f01 for -01 text that -02 keeps, g01-h04 added for -02) through the reference checker and
compares each with its expected answer. Also checks, over every report, the report duties of -02 Section 4.4:
D39 (lines 453-457: no word that speaks for the whole record; a summary line naming the state and every step) and
D40 (lines 459-463: the upper time bound and the policy's digest over its canonical form are stated).

Usage: python3 run_all.py            exit 0 when every vector agrees and every report meets D39 and D40.
A disagreement is printed as DIFFERS and is a finding, not something to fix by editing the expected answer.
"""
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vrcheck  # noqa: E402

WORD = re.compile(r"\b(%s)\b" % "|".join(vrcheck.FORBIDDEN_WORDS), re.I)


def report_problems(v, got):
    out = []
    if got.get("policy_sha256") != v["policy_sha256"]:
        out.append("D40: policy digest %s, vector %s" % (got.get("policy_sha256"), v["policy_sha256"]))
    if got.get("upper_time_bound") != v["upper_time_bound"]:
        out.append("D40: upper time bound not stated")
    steps = got.get("steps")
    want = vrcheck.summary_line(got)
    if got.get("summary") != want or (steps and not all(("step %s %s" % (k, steps[k])) in got["summary"] for k in "123")):
        out.append("D39: summary line")
    # D39 is about words that speak for the whole record: the state, the steps, the summary and every member name.
    def names(x):
        if isinstance(x, dict):
            for k, val in x.items():
                yield k
                yield from names(val)
        elif isinstance(x, list):
            for val in x:
                yield from names(val)
    spoken = [got.get("state") or "", got.get("summary") or ""] + list(names({k: got[k] for k in got if k != "held"}))
    bad = [w for w in spoken if WORD.search(str(w))]
    if bad:
        out.append("D39: %s" % bad)
    return out


def main():
    paths = sorted(glob.glob(os.path.join(HERE, "[a-h][0-9][0-9]-*.json")))
    agree = 0
    for p in paths:
        v = json.load(open(p, encoding="utf-8"))
        got = vrcheck.run_vector(v)
        e = v["expected"]
        same = got["state"] == e["state"] and (e["steps"] is None or got["steps"] == e["steps"])
        if "body_inputs_read" in e:
            same = same and got.get("body_inputs_read", []) == e["body_inputs_read"]
        if e.get("no_step_runs"):
            same = same and got.get("steps") is None
        if "not_relied_on" in e:
            same = same and len(got.get("not_relied_on", [])) == e["not_relied_on"]
        probs = report_problems(v, got)
        agree += same and not probs
        if not same or probs:
            print("DIFFERS", os.path.basename(p), got["state"], got.get("steps"), got.get("reasons"), probs)
    print("vectors run %d, agreeing %d" % (len(paths), agree))
    return 0 if agree == len(paths) else 1


if __name__ == "__main__":
    sys.exit(main())
