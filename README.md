# Test vectors and a reference checker for draft-wright-verdict-record-03

These vectors test the parsing rules (Sections 2.1–2.3) and the check (Section 4) of
draft-wright-verdict-record-03. The reference checker, `vrcheck.py`, implements -03. Each duty -02 gave a checker
carries an id and the line of the published -02 text it comes from, and `DUTIES.md` lists every duty with the vectors
that show it; what -03 changed is marked "-03" at the line of `vrcheck.py` that implements it.

**An independent run.** Lars Kersten Kroehl (MolTrust) wrote a checker of -02 from the -02 text and lines 1-82 of this
README alone, committed its result on all 71 vectors before reading the reference checker, and published the run with
its inputs pinned: https://github.com/MoltyCel/reproduction-runs/tree/run-20261111-verdict-record-02 (directory
`verdict-record-02-d302e24d`, against this repository at d302e24d). It agreed with the reference checker on the state
of 69 of 71 vectors and on all three step results of 68. The three differences (c11, g15, g16), and the Appendix A.2
case he raised by mail, are what -03 closes; see "What -03 settled" below. His run does not cover signing,
containers, `proposals/` or `interop/`. The vectors do not test signing or containers: Section 3 leaves those to the container, so each vector
supplies the record's upper time bound directly as a checker input.

The vectors a01–f01 were written for -01 (f01 now holds the Appendix A.1 example of -03). The vectors a15–a18 and
g31–g46 were added for -03, one for each behaviour -02 left to the checker that -03 now states. The vectors g01–g30
and h01–h04 were added for -02: inputs bound to evidence, the evidence-only policy, the
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
- `policy`: the checker's policy, with the member names of -03 Section 4.5: `{"judgement_kinds": [...], "formats":
  [...], "citation_depth": n}`, with `"inputs_from_evidence_only": true` where the policy reads inputs from evidence
  only. (The -02 vectors named the depth `max_depth`; under -03 that is a member the document does not define: g17,
  g31.) A member -03 does not define is not applied, and the report names it (g15).
- `policy_sha256`: the SHA-256 of the policy in the canonical form of Section 2.1 (-02 lines 460-461).
- `hold` (vectors from -02 on, optional): the modules under `held/` the checker must hold for this vector, beyond the
  test suite (`held/test_suite.py`).
- `expected.state`: `released`, `held`, `refused` or `no verdict`.
- `expected.steps`: each step's result, `PASS`, `FAIL` or `NOT RUN`. It is null where no step runs (bytes refused
  under Sections 2.1–2.3, or an invalid policy), or where two readings of the text give the same state but different
  step results (see I-2). Vectors from -02 on say `expected.no_step_runs: true` where no step may run.
- `expected.named` (from -03 on, every vector): what the check names: `FAIL at step N` or `NOT RUN at step N`
  (-03 Section 4.1: the first step that FAILed, else the first that could not run), `PASS`, `Section 2.N` for a record
  refused before any step (-03 Section 2.1), or null for no verdict.
- `expected.policy_members_not_used` (optional): the policy members the report must name as not used (-03 4.5).
- `decided_by` (from -03 on): the sentence of -03 that decides the expected answer, verbatim, on every vector whose
  answer -03 added or changed, and on every vector whose policy uses the -03 member names. `run_all.py --draft` refuses
  a vector whose sentence is not in the draft.
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

Each test-only rule states, as -03 Section 4.3 requires, how its inputs are compared and what an absent input means:
an input the rule names that `check.inputs` does not give is a set of inputs other than the one stated (a FAIL of
step 3), never a default.

`urn:example:verdict-record:rule:at-least`:
- `check.inputs` is an object with exactly the members `value` and `min`. Under -01 each named a member of `body`;
  under -02 each is resolved as Section 2.2 says (a member of `body`, or an evidence binding). The -01 vectors use body
  members only, so their answers are unchanged.
- Both inputs must be integers. Otherwise the rule's input is of the wrong type, which is a FAIL of step 3.
- The result is `"pass"` when value >= min, compared as integers, else `"fail"`.

`urn:example:verdict-record:rule:equals` (added for -02): exactly the inputs `a` and `b`, any JSON values; `"equal"`
when they are equal as JSON values as -03 Section 4.3 defines it (numbers by mathematical value, so 1.0 equals 1;
arrays in order; objects by member name), else `"different"`. It lets g02 bind an input to an item's digest.

## Running

    python3 run_all.py                  # every vector; exit 0 when all agree and every report meets D39 and D40
    python3 run_all.py --draft draft-wright-verdict-record-03.xml   # also: every decided_by sentence is in the draft
    python3 vrcheck.py g01-*.json       # one vector's report
    python3 gen.py; python3 gen02.py; python3 gen03.py    # regenerate (gen03 adds -03 vectors and expected.named)
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
- -02's Appendix A.1 cited, as its second item, the digest of a placeholder string rather than of a receipt (the
  record over it was 2a85c94e…). -03 cites the receipt of vector P1 of draft-gruszka-signed-evaluation-receipts-04 and
  prints its bytes; f01 holds the new record, read from `appendix-objects.json`, which the draft's own generator
  writes. The -02 generator refuses to write unless it reproduces the Appendix A.2 digests (62017940… and both hops).
- For -03, MolTrust's checker and the reference checker were also run side by side over 2,823 records mutated from
  the vectors. Every case where they still answer differently falls in a behaviour -03 now states, each pinned by a
  vector (a18, g15, g31, g33, g34, g37-g42, g44-g46); 331 of those cases are mutations of those vectors themselves and
  were not classified one by one. MolTrust's -02 checker, run unmodified on the 91 -03 vectors, gives no verdict on 90,
  because it reads `citation_depth` as a member it does not know; with only that policy member renamed back by the
  presenter, it agrees on the state of 81 of 91 and on the step or section named of 77, and what differs is those behaviours.
- Both checkers in this repository were written on the author's side. A checker of -02 written by another party,
  Laurent Lemonnier's `verdict.py` in `dps-scitt-decision-layer` (`interop/verdict-record`), was written from the -02
  text alone. No code of it was read in writing this checker.

## Open points

### From -01, and where -02 leaves them

Points marked * were found only by the blind checker.

- **I-1** Resolved by -02 lines 216-219: bytes that break Sections 2.1–2.2 are refused before any step runs.
- **I-2** Settled by -03 Section 2.3: a ref that does not appear in evidence is refused before any step, named by
  Section 2.3 (c11, g36). The -02 vectors read it as a step 2 FAIL; MolTrust's checker refused it before any step, as
  -03 now says.
- **I-3** Stated by -03 Section 4.3: an empty evidence array passes step 2 (c12).
- **I-4** Stated by -03 Section 4.3: for `judgement`, step 3 re-runs nothing and PASSes.
- **I-5** Resolved by lines 410-413 (depth 0 is the record checked).
- **I-6** Resolved by lines 406-408 (a cited record is relied on only when released).
- **I-7** Resolved by lines 285-298 (the shape of check.inputs).
- **I-8** Resolved: -03 Section 4.5 names the members.
- **I-9** Still open (Appendix B): what "verify" means for a plain media type, or a format whose signature is absent.
- **I-10** Resolved by lines 207-209.
- **I-11** Resolved by lines 460-461 (the policy's canonical form).
- **I-12\*** Settled by -03 Section 2.1: `\b \t \n \f \r` where one applies, else `\u` and four lowercase hex digits
  (a15, a16).
- **I-13\*** Resolved by lines 216-219: a record that breaks Section 2.2 is refused before any step (g19–g26).
- **I-14\*** Resolved by line 271 ("exactly the members"); g27.
- **I-15\*** Resolved by lines 329-330 (held, with the reason). The one chain case exercises it.
- **I-16\*** Resolved by lines 216-219: a non-integer number breaks Section 2.1 and is refused before any step.

### What -03 settled

Each point below was left to the checker by -02. -03 states each one, in the section named, and a vector pins it.
Where -03 decided against the reading an independent checker of -02 took, that is said.

- O-1, O-2: -03 Section 4.5 names the members (`citation_depth`, as agreed with Laurent Lemonnier on 10 Nov 2026) and
  says an undefined member is not applied and is named in the report (g15, g16, g17, g31). MolTrust's -02 checker read
  an unknown member as making the policy invalid; -03 decided the other way.
- O-3: -03 Section 4.3, step 2 names every entry it cannot rely on (g18).
- O-4: -03 Section 4.3, a format the policy lists but the checker holds no rules for is not relied on.
- O-5: -03 Section 4.3, inputs are resolved whether or not the rule is held (g39). MolTrust's checker did not resolve
  them when it did not hold the rule.
- O-7: -03 Section 4.3, a rule specification MUST give a result for every set of inputs of the types it states.
- O-12: -03 Section 4.3, an item read by pointer is parsed by the strict-JSON and nesting rules only.
- O-13: -03 Section 2.2, any string is read as a kind (g32); the reference checker had refused an empty kind.
- O-14: -03 Section 2.2, body.claim MUST be present (g35); the reference checker had read a body without one.
- Found by the side-by-side run over mutated records: the step a check names when two FAIL (the first; g41), a FAIL
  outranking a NOT RUN within step 3 (g40), inputs that are not an object when the rule is not held (g44), JSON value equality (g42, g43), actor values as strings (g33), supersedes
  present for a later version (g34), non-empty format and rule (g37, g38), the section that names a refusal when a
  record breaks more than one (a18), and that the form of hex, like that of a time, is a rule of Section 2.1 (g45, g46).

Still open under -03 (its Appendix B): I-9 (what "verify" means for an unsigned item or a plain media type); O-6
(steps under a container that does not show the record); how an item's own upper time bound is compared when it is
not in the form of Section 2.1, or when the checker has no bound for the citing record.

`blind-checker.py` is a checker of -01 and reads the -01 policy names; it gives no verdict on the -03 vectors and is
kept as it was written.

### Readings -02 does not settle (as written for -02; see above for what -03 settled)

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
