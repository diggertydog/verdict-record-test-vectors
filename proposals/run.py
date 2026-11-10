"""Runs the proposal cases through the reference checker and compares each with expected_under_02.

Run from the repository root:  python3 proposals/run.py
A disagreement is printed as DIFFERS and is itself a finding, not something to fix by editing the expected value.
"""
import base64, glob, hashlib, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vrcheck

here = os.path.dirname(os.path.abspath(__file__))
out = {}
for path in sorted(glob.glob(os.path.join(here, "p[0-9][0-9]-*.json"))):
    v = json.load(open(path, encoding="utf-8"))
    if "evidence_fetch" in v:
        # The items are too large to embed: fetch each from its URL into P08_EVIDENCE (default proposals/p08-evidence)
        # and they are handed over by digest. Without them the case is not run.
        d = os.environ.get("P08_EVIDENCE", os.path.join(here, "p08-evidence"))
        held_items = []
        for f in v["evidence_fetch"]:
            p = os.path.join(d, f["url"].rsplit("/", 1)[1])
            if os.path.exists(p):
                b = open(p, "rb").read()
                if hashlib.sha256(b).hexdigest() == f["sha256"]:
                    held_items.append({"b64": base64.b64encode(b).decode()})
        if len(held_items) != len(v["evidence_fetch"]):
            out[v["name"]] = {"reference_checker": "NOT RUN: evidence_fetch items not present in " + d}
            print("NOT RUN", v["name"], "(fetch evidence_fetch items into %s)" % d)
            continue
        v = dict(v, evidence_items=v.get("evidence_items", []) + held_items)
    got = vrcheck.run_vector(v)
    exp = v["expected_under_02"]
    same = got["state"] == exp["state"] and got["steps"] == exp["steps"]
    got.pop("held", None)
    out[v["name"]] = {"reference_checker": got, "agrees_with_expected_under_02": same}
    print(("AGREES " if same else "DIFFERS"), v["name"], got["state"], got["steps"], got["reasons"])
with open(os.path.join(here, "results-reference-checker.json"), "w", encoding="utf-8") as f:
    json.dump(out, f, indent=2, ensure_ascii=False)
    f.write("\n")
