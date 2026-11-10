# Test vectors and a reference checker for draft-wright-verdict-record-02

These vectors test the parsing rules (Sections 2.1–2.3) and the check (Section 4) of
draft-wright-verdict-record-02. The reference checker, `vrcheck.py`, implements -02: each duty -02 gives a checker
carries an id and the line of the published text it comes from, and `DUTIES.md` lists every duty with the vectors that
show it. The vectors do not test signing or containers: Section 3 leaves those to the container, so each vector
supplies the record's upper time bound directly as a checker input.

The vectors a01–f01 were written for -01. -02 keeps every rule they test, and each still gives the same expected
answer. The vectors g01–g30 and h01–h04 were added for -02: inputs bound to evidence, the evidence-only policy, the
member rules that -02 refuses before any step, the report, and the four outcomes -02 Appendix A.2 predicts.

`blind-checker.py` was written for -01 by a party that saw only the -01 draft text. It reads a01–f01 only, and it
implements -01. Its value is that it was written from the text alone.

## Vector file format

Each vector is one JSON file at the top of this repository. Each is one JSON object:

- `name`, `section`, `description`: what the vector tests and where in the draft. Vectors added for -02 give the
  lines of the published -02 text, and `duties`, the ids of `DUTIES.md`.
- `record_b64`: the exact bytes of the verdict record, base64. Exact bytes matter: several vectors are records that
  are not canonical.
- `record_sha256`: the SHA-256 of those bytes, in hex.
- `evidence_items`: the items the checker holds, each `{"b64": ..., "upper_time_bound"?: ...}`. An item's
  `upper_time_bound`, where present, is what the item's own verification gives (Section 4.3 step 2).
- `upper_time_bound`: the record's upper time bound, established outside the record.
- `policy`: the checker's policy (Section 4.5). -02 says what a policy states but not the names of its members
  (open point O-1). The vectors write it as `{"judgement_kinds": [...], "formats": [...], "max_depth": n}`, with
  `"inputs_from_evidence_only": true` where the policy reads inputs from evidence only. The reference checker also
  reads the depth as `citation_depth`, the name a second checker of -02 chose (g16).
- `policy_sha256`: the SHA-256 of the policy in the canonical form of Section 2.1 (-02 lines 460-461).
- `hold` (vectors from -02 on, optional): the modules under `held/` the checker must hold for this vector, beyond the
  test suite (`held/test_suite.py`).
- `expected.state`: `released`, `held`, `refused` or `no verdict`.
- `expected.steps`: each step's result, `PASS`, `FAIL` or `NOT RUN`. It is null where no step runs (bytes refused
  under Sections 2.1–2.3, or an invalid policy), or where two readings of the text give the same state but different
  step results (see I-2). Vectors from -02 on say `expected.no_step_runs: true` where no step may run.
- `expected.body_inputs_read`, `expected.not_relied_on` (optional): the inputs the report must name as read from
  body (-02 lines 438-439), and how many evidence entries step 2 must name as not relied on.
- `depends_on_interpretation`: present where the expected result rests on a reading of the draft that the text does
  not settle. The label names the open point below.

## What the checker holds: `held/`

A checker holds rule specifications, format rules and trust anchors as its own inputs (-02 lines 367-369). The
reference checker holds none of them in its code. Each is a module under `held/` that names its published source:

- `test_suite.py`: the test-only rules and formats below.
- `appendix_a2_rule.py`, `appendix_a2_hops_parse_only.py`, `appendix_a2_hops_signature_required.py`: the rule of -02
  Appendix A.2 (lines 1075-1087) and two test-only readings of the hop format, for h01–h04.
- `dps_007f8c9.py`: the format rules of two Decision Provenance Standard formats and the rule `executed-as-approved:v1`,
  as the one chain interop case pins them (below). It loads the Standard's own published reference check at commit
  007f8c9 and needs a checkout of that commit (`DPS_STANDARD`) and the Standard's dependencies (`jsonschema`,
  `referencing`, `cryptography`, `asn1crypto`).
- `container_detached_ed25519.py`: the stand-in container that interop case uses (Section 3). Labelled a stopgap in
  its own text.

Every report lists what was held and from where (`held`), so a rule's author can see which reading of the rule ran.

## Test-only evidence formats

The draft verifies each evidence item "by the rules of the format its entry names". So that the vectors do not depend
on any other format's rules, they use these:

- `urn:example:verdict-record:format:opaque`: every item meets the format's rules.
- `urn:example:verdict-record:format:never-verifies`: no item meets them.
- `verdict-record/1`: the item is a verdict record, checked by Section 4 as a record of its own. It is relied on when
  its state is `released`.

## Test-only rules

`urn:example:verdict-record:rule:at-least`:
- `check.inputs` is an object with exactly the members `value` and `min`. Under -01 each named a member of `body`;
  under -02 each is resolved as Section 2.2 says (a member of `body`, or an evidence binding). The -01 vectors use body
  members only, so their answers are unchanged.
- Both inputs must be integers. Otherwise the rule's input is of the wrong type, which is a FAIL of step 3.
- The result is `"pass"` when value >= min, else `"fail"`.

`urn:example:verdict-record:rule:equals` (added for -02): exactly the inputs `a` and `b`, any JSON values; `"equal"`
when they are equal as JSON values, else `"different"`. It lets g02 bind an input to an item's digest.

## Running

    python3 run_all.py                  # every vector; exit 0 when all agree and every report meets D39 and D40
    python3 vrcheck.py g01-*.json       # one vector's report
    python3 gen.py; python3 gen02.py    # regenerate the vectors (-01 set, -02 set)
    python3 proposals/run.py            # the proposal cases (proposals/README.md)
    python3 blind-checker.py . .        # the -01 blind checker, a01-f01 only

The one chain interop case (below):

    git clone https://github.com/decision-provenance-standard/standard dps && git -C dps checkout 007f8c99ec910564bac1c508b76c8ce8391fa11e
    git clone https://github.com/Laurent-Lemonnier/dps-scitt-decision-layer one-chain-repo
    ONE_CHAIN_REPO=one-chain-repo DPS_STANDARD=dps python3 interop/one-chain/run.py
    ONE_CHAIN_REPO=one-chain-repo DPS_STANDARD=dps python3 interop/one-chain/check_required.py

## The one chain interop case

Laurent Lemonnier's case 18 (`dps-scitt-decision-layer`, `interop/one-chain`) joins his decision record to a verdict
record of -02, with 23 directories (the valid chain, the stated negative chain and 21 failing cases), each holding two
verdict records. `interop/one-chain/run.py` hands this checker each record with the case's own policy (verbatim, the
bytes whose digest the case's reports name), the case's own trust anchors and published containers, and the rule and
format rules the case pins, held as `held/dps_007f8c9.py` from their published sources. It writes
`interop/one-chain/results.json`: per record, our state and steps beside the case's stated ones. Nothing the case
states is given to the checker.

The rule `executed-as-approved:v1` requires the reference check to report all eight of its dimensions verified,
`authorisation_recheck` and `rationale_provenance` among them. The held module names those two as required, as the
Standard's steward reads the rule (decision-provenance-standard/standard, issue #106, on the paragraph merged as pull
request #108), and refuses to load if the pinned reference check stops reporting either. No record of the case has
either dimension at anything but verified, so `interop/one-chain/check_required.py` shows the requirement on the
case's positive inputs with each dimension's answer replaced: the held rule gives `not_as_approved` each time.

## How the expected answers were checked

- The expected answers were written by hand from the draft text, each with the section (from -02 on, the lines) it
  rests on. A reference checker (`vrcheck.py`) was then written and run against them.
- For -01, a second checker was written by a separate agent that was given only the draft, this README (without this
  section or the open points) and the vectors with no expected answers. It is `blind-checker.py`, with the readings it
  had to choose in `blind-checker-readings.md` and its raw results in `blind-checker-results.json`. On the first
  comparison the two agreed on the state of all 37 vectors; they disagreed on step results in two places (b03 and
  c11). The text supported the blind checker's reading on b03, and it was adopted. c11 is tested on its state only.
- For -02, the published -01 checker was run on the -02 vectors: it gives the expected answer on 10 of 34. Two
  are policy cases where -01 and -02 agree (g14, g17). Six FAIL at step 3 under -01 only because it cannot read
  an evidence binding at all (g08–g13); g01, g05 and g15 separate the two. Two are caught only by the report fields
  (g03, g18).
- Both checkers reproduce the draft's Appendix A.1 digest (2a85c94e…); the -02 generator refuses to write unless it
  reproduces the Appendix A.2 digests (62017940… and both hops).
- Both checkers in this repository were written on the author's side. A checker of -02 written by another party,
  Laurent Lemonnier's `verdict.py` in `dps-scitt-decision-layer` (`interop/verdict-record`), was written from the -02
  text alone. No code of it was read in writing this checker.

## Open points

### From -01, and where -02 leaves them

Points marked * were found only by the blind checker.

- **I-1** Resolved by -02 lines 216-219: bytes that break Sections 2.1–2.2 are refused before any step runs.
- **I-2** Still open: body.claim.ref MUST appear in evidence (lines 313-314), but no step is named. The vectors read it
  as a step 2 FAIL.
- **I-3** Still open: an empty evidence array passes step 2, so a record citing nothing can be released.
- **I-4** Still a reading: for rule `judgement`, step 3 has nothing to re-run; both checkers read it as PASS.
- **I-5** Resolved by lines 410-413 (depth 0 is the record checked).
- **I-6** Resolved by lines 406-408 (a cited record is relied on only when released).
- **I-7** Resolved by lines 285-298 (the shape of check.inputs).
- **I-8** Resolved in part by lines 472-474 (when a policy is invalid); its member names are still open (O-1).
- **I-9** Still open (Appendix B): what "verify" means for a plain media type, or a format whose signature is absent.
- **I-10** Resolved by lines 207-209.
- **I-11** Resolved by lines 460-461 (the policy's canonical form).
- **I-12\*** Still open: the escape form for control characters (`\n` or `\u000a`).
- **I-13\*** Resolved by lines 216-219: a record that breaks Section 2.2 is refused before any step (g19–g26).
- **I-14\*** Resolved by line 271 ("exactly the members"); g27.
- **I-15\*** Resolved by lines 329-330 (held, with the reason). The one chain case exercises it.
- **I-16\*** Resolved by lines 216-219: a non-integer number breaks Section 2.1 and is refused before any step.

### Readings -02 does not settle

Each is a reading this checker takes where the -02 text does not decide. The quoted sentence states the reading;
it is not draft text.

- **O-1 The policy's member names.** -02 lines 467-471 say what a policy states, not its members' names, so two
  checkers of -02 can each reject the other's policy (this repository's `max_depth`; a second checker's
  `citation_depth`). The reading: "A policy is a JSON object with the members `judgement_kinds` (an array of
  strings), `formats` (an array of strings), `citation_depth` (an integer of 0 or more) and, optionally,
  `inputs_from_evidence_only` (a boolean, false when absent)." This checker reads either depth name (a stopgap,
  labelled in `vrcheck.py` with the condition on which it retires).
- **O-2 A member a checker does not know.** Lines 472-474 make a policy invalid only when it lacks one of the first
  three members or states one in another form. The reading: "A member the checker does not know is read past, and
  the policy runs without it." (g15.) The second checker reads it the same way. What the reading costs: a limit
  stated under a name the checker does not know is not applied. The report's policy digest covers the policy as
  given, unknown members included.
- **O-3 Which entries step 2 names.** Line 400 says step 2 is NOT RUN "naming the entry". The reading: "Step 2 names
  every entry it does not rely on, with the reason for each." Step 3 needs the whole set (lines 417-419) (g18).
- **O-4 A format the policy lists but the checker holds no rules for.** The reading, for step 2: "An item whose format
  the checker cannot verify is not relied on, as if the policy did not list it." (proposal case p08.)
- **O-5 A binding that cannot be resolved, when the rule is not held.** The reading, for step 3: "Inputs are resolved
  before the rule is re-run; an input that cannot be resolved makes step 3 FAIL whether or not the checker holds the
  rule."
- **O-6 Steps under a container that does not show the record.** The reading, for Section 3: "The steps still run and
  are reported; the state is held."
- **O-7 A rule the checker holds but cannot run on the resolved inputs.** The reading: step 3 is NOT RUN, naming the
  rule.
- **O-12 Numbers in an item read by pointer.** Line 297 parses the item "as strict JSON by the rules of Section 2.1";
  this checker applies the strict-JSON rules (UTF-8, no byte-order mark, no member twice, no lone surrogate, depth)
  and not the record's integer rule. The text does not say which.
- **O-13 Values of v and kind.** -02 defines one v and two kinds, plus private `x-` kinds. This checker refuses any
  other v (g26) and reads any non-empty kind. The reading: "A record whose v is not "verdict-record/1" is refused before
  any step; a kind that is neither defined here nor private is read, and only step 1 depends on it."
- **O-14 The claim's shape.** The reading, for Section 2.3: "body.claim is required; a claim with both text and ref, or
  with neither, is refused before any step." (g28, g30; this checker reads a body without claim, since -02 does not
  say it is required.)

## Licence

The vectors and the reference checker are offered under the Revised BSD Licence, the terms the IETF uses for code
components.
