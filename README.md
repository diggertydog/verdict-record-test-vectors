# Test vectors for draft-wright-verdict-record-01

These vectors test the parsing rules (Sections 2.1–2.3) and the check (Section 4) of
draft-wright-verdict-record-01. They do not test signing or containers: Section 3
leaves those to the container, so each vector supplies the record's upper time bound
directly as a checker input.

## Vector file format

Each vector is one JSON file at the top of this repository, named `a01-…` to `f01-…`. Each is one JSON object:

- `name`, `section`, `description`: what the vector tests and where in the draft.
- `record_b64`: the exact bytes of the verdict record, base64. Exact bytes matter:
  several vectors are records that are not canonical.
- `record_sha256`: the SHA-256 of those bytes, in hex.
- `evidence_items`: the items the checker holds, each `{"b64": ..., "upper_time_bound"?: ...}`.
  An item's `upper_time_bound`, where present, is what the item's own verification
  gives (Section 4.3 step 2).
- `upper_time_bound`: the record's upper time bound, established outside the record.
- `policy`: the checker's policy (Section 4.5), as `{"judgement_kinds": [...],
  "formats": [...], "max_depth": n}`. The policy is valid when it has exactly those
  three members, the two lists hold strings, and `max_depth` is an integer of 0 or more.
- `policy_sha256`: the SHA-256 of the policy in the canonical form of Section 2.1.
- `expected.state`: `released`, `held`, `refused` or `no verdict`.
- `expected.steps`: each step's result, `PASS`, `FAIL` or `NOT RUN`. It is null where no
  step runs (bytes refused under Sections 2.1–2.3, or an invalid policy), or where two
  readings of the text give the same state but different step results (see I-2).
- `depends_on_interpretation`: present where the expected result rests on a reading of
  the draft that the text does not settle. The label names the open point below.

## Test-only evidence formats

The draft verifies each evidence item "by the rules of the format its entry names".
So that the vectors do not depend on any other format's rules, they use these:

- `urn:example:verdict-record:format:opaque`: every item verifies.
- `urn:example:verdict-record:format:never-verifies`: no item verifies.
- `verdict-record/1`: the item is a verdict record, checked by Section 4 as a record of
  its own. It verifies when its state is `released`.

## Test-only rule

`urn:example:verdict-record:rule:at-least`:
- `check.inputs` is an object with exactly the members `value` and `min`. Each maps to
  the name of a member of `body`.
- Both named members must be integers. Otherwise the rule's input is of the wrong type,
  which is a FAIL of step 3.
- The result is `"pass"` when body[value] >= body[min], else `"fail"`.

## Running the checkers

    python3 vrcheck.py [a-f][0-9][0-9]-*.json
    python3 blind-checker.py . .

`gen.py` regenerates the vectors in the current directory.

## How the expected answers were checked

- The expected answers were written by hand from the draft text, each with the section
  it rests on. A reference checker (`vrcheck.py`) was then written and run against them.
- A second checker was written by a separate agent that was given only the draft, this
  README (without this section or the open points) and the vectors with no expected
  answers. It is `blind-checker.py`, with the readings it had to choose in `blind-checker-readings.md` and its raw results in `blind-checker-results.json`.
- On the first comparison the two agreed on the state of all 37 vectors. They disagreed
  on step results in two places (b03 and c11). The text supported the blind checker's
  reading on b03, and it was adopted. c11 is now tested on its state only.
- Both checkers reproduce the draft's Appendix A digest (2a85c94e…).
- **Neither checker is a second implementation in the IETF sense.** Both were written
  on the author's side. A checker written by another party is still wanted.

## Open points the vectors expose (for -02)

Points marked * were found only by the blind checker.

- **I-1** No state is named for bytes that break Sections 2.1–2.3. Section 2.1 says a
  checker MUST "refuse" over-deep JSON, so the vectors expect `refused` with no step run.
  Section 4.4 defines refused only through a failed step. -02 could add a step 0.
- **I-2** Section 2.3: body.claim.ref MUST appear in evidence, but no step is named. A
  step 2 FAIL and a refusal before the steps both fit.
- **I-3** An empty evidence array passes step 2, so a record citing nothing can be released.
- **I-4** For rule `judgement`, step 3 has nothing to re-run. Both checkers read it as
  PASS, as Appendix A implies, even when step 1 FAILs.
- **I-5** Citation depth: the record checked is depth 0, so following one citation needs
  `max_depth` of 1 or more.
- **I-6** A cited verdict record "verifies" only when its own state is `released`.
- **I-7** The shape of `check.inputs` is not specified. The test rule defines its own.
- **I-8** Policy validity is not defined. The vectors define it as above.
- **I-9** What "verify" means for a plain media type such as `application/json` is not
  defined.
- **I-10** Nesting depth counts objects and arrays, starting at 1 for the record.
- **I-11** Which bytes of the policy are digested for the report. The vectors use the
  policy's canonical form.
- **I-12\*** The escape form for control characters is not given (`\n` or `\u000a`).
  No vector tests it yet.
- **I-13\*** Rules on members no step reads (v, key, version, supersedes, writer, actor,
  act_time, and body as an object) have no step that enforces them.
- **I-14\*** Section 2.2 does not say that check holds "exactly" rule, inputs and result.
- **I-15\*** A record whose container gives no upper time bound: Section 3 implies held
  with no step run. No vector tests it yet.
- **I-16\*** A non-integer number is a parse refusal under Section 2.1, not a step 3
  wrong-type FAIL. The text could say so.

## Licence

The vectors and the reference checker are offered under the Revised BSD Licence, the
terms the IETF uses for code components.
