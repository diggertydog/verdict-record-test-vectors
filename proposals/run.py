"""Runs the proposal cases through the reference checker and compares each with expected_under_02.

Run from the repository root:  python3 proposals/run.py
A disagreement is printed as DIFFERS and is itself a finding, not something to fix by editing the expected value.
"""
import glob, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vrcheck

here = os.path.dirname(os.path.abspath(__file__))
out = {}
for path in sorted(glob.glob(os.path.join(here, "p[0-9][0-9]-*.json"))):
    v = json.load(open(path, encoding="utf-8"))
    if "evidence_fetch" in v:
        # Inputs bound to evidence by JSON Pointer are -02 text; this reference checker predates -02.
        out[v["name"]] = {"reference_checker": "NOT RUN: the reference checker predates -02 evidence-bound inputs"}
        print("NOT RUN", v["name"], "(needs a -02 checker that holds the IronTrellis rule)")
        continue
    got = vrcheck.run_vector(v)
    exp = v["expected_under_02"]
    same = got["state"] == exp["state"] and got["steps"] == exp["steps"]
    out[v["name"]] = {"reference_checker": got, "agrees_with_expected_under_02": same}
    print(("AGREES " if same else "DIFFERS"), v["name"], got["state"], got["steps"], got["reasons"])
with open(os.path.join(here, "results-reference-checker.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write("\n")
