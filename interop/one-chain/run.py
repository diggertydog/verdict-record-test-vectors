"""Runs the reference checker on Laurent Lemonnier's one chain case (case 18 of dps-scitt-decision-layer,
interop/one-chain) and sets each result beside the result the case states.

This is a presenter, not a change to the checker. It hands vrcheck.py, for each verdict record of the case:
  - the record's exact bytes, as published;
  - every file of the record's case directory, as evidence items by their digest (step 2 takes the ones cited);
  - the case's checker policy, verbatim: interop/verdict-record/out/checker-policy.json, whose digest the case's
    reports name (policy_sha256);
  - the upper time bound the case's own report states as its checker input (summary.json, upper_time_bound);
  - two sets of trust anchors, both the case's own published bytes: the DPS trust policy of the directory
    (trust-policy.json) and the writers' keys (interop/verdict-record/out/checker-trust-anchors.json, member writers);
  - the record's container, where the case publishes one (verdict-record.container.json);
  - and, as held inputs, the modules held/dps_007f8c9.py and held/container_detached_ed25519.py.

What the case states is read from its own reports (summary.json, link3_verdict and link3_other_verdict) and from
its README's table of failing cases; nothing the case states is fed to the checker.

Usage:
  ONE_CHAIN_REPO=<checkout of Laurent-Lemonnier/dps-scitt-decision-layer> \
  DPS_STANDARD=<checkout of decision-provenance-standard/standard at 007f8c9> \
  python3 interop/one-chain/run.py [--out results.json] [--table table.md]
"""
import glob
import hashlib
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOP = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOP)
import vrcheck  # noqa: E402

CASE_COMMIT_READ = "9e1c7a0b047129d71c5694995e0014eecdf2289c"
RECORDS = (("verdict-record.json", "link3_verdict"), ("verdict-record-other-result.json", "link3_other_verdict"))


def sha(b):
    return hashlib.sha256(b).hexdigest()


def stated_steps(s):
    return {k: v.get("result") for k, v in (s.get("steps") or {}).items()} if s.get("steps") else None


def main():
    repo = os.environ["ONE_CHAIN_REPO"]
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    case = os.path.join(repo, "interop", "one-chain", "out")
    c16 = os.path.join(repo, "interop", "verdict-record", "out")
    policy_bytes = open(os.path.join(c16, "checker-policy.json"), "rb").read()
    policy = json.loads(policy_bytes)
    writers = json.load(open(os.path.join(c16, "checker-trust-anchors.json")))["writers"]
    held = vrcheck.load_held([vrcheck.TEST_SUITE, os.path.join(TOP, "held", "dps_007f8c9.py"),
                              os.path.join(TOP, "held", "container_detached_ed25519.py")])
    dirs = [os.path.join(case, "positive"), os.path.join(case, "stated-negative")] + sorted(
        glob.glob(os.path.join(case, "negatives", "N*")), key=lambda p: int(os.path.basename(p)[1:].split("-")[0]))
    rows = []
    for d in dirs:
        name = os.path.relpath(d, case)
        files = [p for p in glob.glob(os.path.join(d, "**", "*"), recursive=True) if os.path.isfile(p)]
        items = {}
        for p in files:
            b = open(p, "rb").read()
            items[sha(b)] = {"bytes": b, "upper_time_bound": None, "file": os.path.relpath(p, d)}
        summary = json.load(open(os.path.join(d, "summary.json")))
        anchors = {"dps_trust_policy": json.load(open(os.path.join(d, "trust-policy.json"))), "writers": writers}
        cont_path = os.path.join(d, "verdict-record.container.json")
        container = json.load(open(cont_path)) if os.path.exists(cont_path) else None
        for fname, key in RECORDS:
            rb = open(os.path.join(d, fname), "rb").read()
            st = summary.get(key) or {}
            # The container the case publishes is for one record only; it is handed in with the record it names.
            cont = container if (container and container.get("record_sha256") == sha(rb)) else None
            got = vrcheck.run(rb, policy, st.get("upper_time_bound"), items, held, anchors,
                              container=cont, container_presented=cont is not None)
            rows.append({
                "dir": name, "record": fname, "record_sha256": sha(rb),
                "stated": {"record_sha256": st.get("record_sha256"), "state": st.get("state"),
                           "steps": stated_steps(st), "re_run_result": (st.get("steps") or {}).get("3", {}).get("re_run_result"),
                           "why": {k: v.get("why") for k, v in (st.get("steps") or {}).items() if v.get("why")},
                           "items": (st.get("steps") or {}).get("2", {}).get("items"),
                           "container": st.get("container")},
                "ours": {k: got.get(k) for k in ("state", "state_from_steps", "steps", "reasons", "re_run_result",
                                                  "container", "rule_detail", "summary", "not_relied_on")},
                "container_published": cont is not None,
            })
    # SUPPLEMENTARY, not counted in the comparison: N13's what.txt says the checker "holds no item with the cited
    # digest" (A2 altered after the verdict cited it), but the directory publishes the A2 bytes the verdict cites.
    # Here the item at evidence[1] is withheld, which is the condition what.txt states; nothing is constructed.
    supplementary = []
    n13 = [d for d in dirs if os.path.basename(d).startswith("N13-")]
    for d in n13:
        summary = json.load(open(os.path.join(d, "summary.json")))
        anchors = {"dps_trust_policy": json.load(open(os.path.join(d, "trust-policy.json"))), "writers": writers}
        for fname, key in RECORDS:
            rb = open(os.path.join(d, fname), "rb").read()
            cited = json.loads(rb)["evidence"][1]["sha256"]
            items = {}
            for p in glob.glob(os.path.join(d, "**", "*"), recursive=True):
                if os.path.isfile(p):
                    b = open(p, "rb").read()
                    if sha(b) != cited:
                        items[sha(b)] = {"bytes": b, "upper_time_bound": None}
            st = summary.get(key) or {}
            got = vrcheck.run(rb, policy, st.get("upper_time_bound"), items, held, anchors)
            supplementary.append({"dir": os.path.relpath(d, case), "record": fname,
                                  "condition": "item at evidence[1] (%s) withheld, as what.txt states" % cited[:12],
                                  "stated": {"state": st.get("state"), "steps": stated_steps(st)},
                                  "ours": {k: got.get(k) for k in ("state", "steps", "reasons", "summary")}})
    out = {"case_commit_read": head, "case_commit_brief": CASE_COMMIT_READ, "supplementary": supplementary,
           "policy_sha256": sha(policy_bytes), "report_policy_sha256": vrcheck.sha256hex(vrcheck.canonical(policy)),
           "held": held.sources, "rows": rows}
    args = sys.argv[1:]
    path = args[args.index("--out") + 1] if "--out" in args else os.path.join(HERE, "results.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    classes = json.load(open(os.path.join(HERE, "classes.json")))
    lines = ["# One chain case: our state and steps beside the case's", "",
             "Case commit read: `%s`. Policy: the case's own, verbatim (sha256 `%s`). Written by run.py." % (head, sha(policy_bytes)),
             "", "| directory | record | stated | ours | container | agree | class |", "|---|---|---|---|---|---|---|"]
    fmt = lambda x: "%s %s" % (x["state"], "/".join(x["steps"][k] for k in "123") if x.get("steps") else "-")
    for r in rows:
        s, o = r["stated"], r["ours"]
        same = s["state"] == o["state"] and s["steps"] == o["steps"]
        c = classes.get(r["dir"] + "/" + r["record"], {})
        cont = o.get("container") if r["container_published"] else "not published"
        lines.append("| %s | %s | %s | %s | %s | %s | %s |" % (r["dir"].replace("negatives/", ""), r["record"], fmt(s), fmt(o),
                     cont, "yes" if same else "no", "" if same else c.get("class", "UNCLASSED")))
    # The table is written beside results.json, so a run with --out elsewhere never touches the published table.
    with open(os.path.join(os.path.dirname(os.path.abspath(path)), "table.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    for r in rows:
        s, o = r["stated"], r["ours"]
        same = s["state"] == o["state"] and s["steps"] == o["steps"]
        print("%-8s %-58s %-34s stated %-9s %-28s ours %-9s %s" % (
            "AGREES" if same else "DIFFERS", r["dir"][:58], r["record"], s["state"], s["steps"], o["state"], o["steps"]))


if __name__ == "__main__":
    main()
