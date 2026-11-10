# What draft-wright-verdict-record-02 asks of a checker, and what shows the reference checker does it

Lines are those of the published text, https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt
(md5 e02052750dc143f4aaea2d56abcfc5dc). "Before" is `vrcheck.py` at commit 97b63b2 (written for -01); "after" is
`vrcheck.py` on this branch. A duty id appears as a comment on the line of `vrcheck.py` that implements it, and in the
`duties` member of each vector added for -02. "Shown by" names the vectors, the proposal case or the interop case
whose expected answer depends on the duty. Where -02 does not settle the answer, the reading taken is named (O-n,
I-n: README, "Open points").

| id | -02 lines | duty | before | after | shown by |
|---|---|---|---|---|---|
| D01 | 196-202 | canonical form; re-serializing gives the same bytes | met | met | a02, a03, a08, a09 |
| D02 | 204-206 | strict JSON: UTF-8, no byte-order mark, no member twice, no lone surrogate | met | met | a04, a05, a10 |
| D03 | 206-209 | refuse nesting deeper than 32; record is level 1, each object or array adds one | met | met | a11, a12 |
| D04 | 201, 211-213 | numbers are integers within ±(2^53 - 1) | met | met | a06, a07 |
| D05 | 213-214 | a time is YYYY-MM-DDTHH:MM:SS.ffffffZ | not met | met | g19 |
| D06 | 214-215 | hex is lowercase, two characters per byte (evidence sha256, supersedes) | partly (evidence only) | met | c03, g21, g22, g23 |
| D07 | 215-216 | a member of the wrong JSON type is refused at the step that reads it | met | met | c02, d02, g13 |
| D08 | 216-219 | bytes breaking 2.1, or a record breaking 2.2 other than in evidence and check, are refused before any step, naming the rule | partly (top-level member names only) | met | a02-a14, g19-g22, g24-g26, g28-g30 |
| D09 | 229-231 | the digest is SHA-256 of the exact bytes, in hex | met | met | f01 (A.1 digest), h01 (A.2 digests) |
| D10 | 235-238 | exactly the listed members; v, kind, key, version, writer, body present | met | met | a13, a14 |
| D11 | 240-264, 304-306 | each member's value: v, kind, key, version, supersedes, writer, actor, act_time, body | not met | met | g20-g26, g29 |
| D12 | 266-269 | an evidence entry has exactly sha256 and format | met | met | c02, c03 |
| D13 | 271-273 | check has exactly rule, inputs (optional) and result | met, no vector (I-14) | met | g27 |
| D14 | 285-293 | each input is a member name of body, or {evidence, pointer?} and no other member | not met | met | g01, g08, h01 |
| D15 | 294-295 | a binding with no pointer is the digest of the item held | not met | met | g02, h01 |
| D16 | 295-298 | a binding with pointer is the value at that JSON Pointer in the item, parsed as strict JSON | not met | met | g01, g10, g11, h01, one chain case |
| D17 | 310-314 | body.claim is exactly one of text or ref; a ref also appears in evidence | partly (ref only) | met | c11, g28, g30 |
| D18 | 318-330 | the checker needs a key bound to writer and an upper time bound; a container that does not show the record makes the state held | not met (vectors supply the bound; no container rule) | met through a held container rule | one chain case (23 published containers); vectors leave Section 3 to the container |
| D19 | 354-356 | a later FAIL makes the check FAIL; otherwise NOT RUN at the first step that could not run; the result names the step | met | met | d04, g12 |
| D20 | 358-360 | two checkers with the same inputs give the same result; no step reads the clock | met | met | no clock is read; run_all.py twice gives the same output |
| D21 | 364-370 | every input from outside the issuer's reach; the checker's own inputs never taken from the record | met | met | policy, rules, formats and anchors are presenter inputs (held/) |
| D22 | 379-382 | under the default policy, step 3 may rely on a value in body that check.inputs names | met | met | a01, g03 |
| D23 | 386-388 | step 1: check present, names a rule, gives a result; judgement only for kinds the policy lists | met | met | b01-b04 |
| D24 | 397-400 | step 2: hold an item with the entry's digest, else NOT RUN naming the entry | met (first entry only) | met (every entry named, O-3) | c04, g06, g18, h04 |
| D25 | 402-404 | an item whose format's rules are not met, or whose format the policy does not list, is not relied on | met (test formats only) | met (held format rules) | c05, c06, g07, h02, one chain case |
| D26 | 406-408, 535-538 | a cited verdict record is checked as a record and relied on only while released | met | met | c07, c10 |
| D27 | 408-410 | an item's upper time bound is not later than the record's | met | met | c09, p03 |
| D28 | 410-413 | citation depth: the record is depth 0; beyond the policy's depth, NOT RUN | met | met | c08, g16 |
| D29 | 415-417 | step 3: hold the rule's specification, resolve each input, re-run | partly (one test rule, body inputs only) | met | d03, g01, h01, one chain case |
| D30 | 417-419 | an input bound to an item not held, or not relied on by step 2, makes step 3 NOT RUN | not met | met | g06, g07, h02, h04 |
| D31 | 419-423 | an input that cannot be resolved, or is of the wrong JSON type, is a FAIL of step 3 | partly (body inputs only) | met | d02, g08-g11, g13 |
| D32 | 423-424 | one input NOT RUN and another FAIL: the step FAILs | not met | met | g12 |
| D33 | 425-427, 476-482 | under an evidence-only policy, an input read from body makes step 3 NOT RUN | not met | met | g04, g05, h01 |
| D34 | 427 | the re-run result must equal check.result, else step 3 FAILs | met | met | d01, d05, h03 |
| D35 | 415, 429 | judgement: no rule is re-run (I-4: step 3 PASS) | met | met | b04, f01 |
| D36 | 433-436 | the state: released, held, refused, or no verdict | met | met | all |
| D37 | 436-438 | the report gives each step's result and, for each FAIL or NOT RUN, the step and the input needed | partly (first reason only) | met | g06, g12, g18 |
| D38 | 438-439 | under the default policy the report names each rule input read from body | not met | met | g03, g01 (none) |
| D39 | 453-457 | no word that speaks for the whole record; a summary line names the state and every step | met (no summary line) | met | run_all.py, over every report |
| D40 | 459-463 | the report states the upper time bound and the digests of the policy (canonical form) and of each set of trust anchors | partly (policy digest only) | met | run_all.py, over every report; one chain case (two anchor sets) |
| D41 | 467-471 | the policy lists judgement kinds, formats, a depth of 0 or more, and may state evidence-only | partly (no evidence-only; one member name) | met (O-1) | g04, g05, g16 |
| D42 | 472-474 | a policy lacking one of the three, or stating one in another form, is invalid: no verdict | met | met (O-2) | e01, g14, g15, g17 |
| D43 | 1185-1194 | Appendix A.2's four predicted outcomes (Appendix C: "Added a second example") | not met (no vectors; -02 says they are being added) | met | h01-h04 |

Not checker duties, and so not in the table: Section 1.2 and Appendix C "rule names should identify a version" (an
issuer's SHOULD), Section 2.2 "an issuer SHOULD bind an input to evidence" (line 300), Section 5 (what a check shows),
and Section 6's statements about issuers. Section 6's duties for a checker are D26 and the absence of any step that
reads supersedes (g23).

Count: 43 duties. Before: 24 met, 8 partly, 11 not met. After: 43 met, 5 of them resting on a reading the text does
not settle (D24 O-3, D41 O-1, D42 O-2, D11 O-13, D17 O-14), stated in the README's open points.
