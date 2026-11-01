# Readings — independent checker for draft-wright-verdict-record-01

Each reading is a place where the draft text did not settle the outcome. I chose the reading I think the text supports best. A vector's `readings` list in results.json names the readings its result rests on.

**R1. A record that fails Sections 2.1–2.3 is refused, and no step runs.**
Section 4.4 defines refused only as "when a step FAILs", and parsing is not one of steps 1–3. But Section 2.1 says "A checker MUST refuse JSON nested deeper than 32 levels" and "Re-serializing the parsed record MUST give the same bytes". Section 2.2 says "A record without evidence or check can be parsed, but fails step 1 or step 2", which implies other records cannot be parsed. I report state `refused` with `steps: null`. The other way to read it, step 1 FAIL, was rejected because the steps assume a parsed record.

**R2. Depth counts the outermost object as level 1, and 32 levels are allowed.**
Section 2.1 says "nested deeper than 32 levels" but does not say where counting starts. Every object or array adds one level, starting at 1 for the top-level object. Depth 32 is accepted (a11) and depth 33 is refused (a12).

**R3. A non-integer number is a parse failure, not a step 3 type FAIL.**
Section 2.1 says "numbers are integers" in canonical form, and an integer has "no fraction and no exponent". Step 3 says "A rule input of the wrong JSON type is a FAIL of this step". The README's rule says inputs that are not integers are "of the wrong type". 7.5 is not a number the canonical form allows anywhere, so the record is refused at parse (a06). Step 3 type FAIL is reserved for well-formed values of another JSON type, such as a string (d02).

**R4. How control characters are escaped.**
Section 2.1 says strings "escape only the quotation mark, the reverse solidus and control characters" but does not give the escape form. I take control characters to mean U+0000–U+001F, as in JSON (not U+007F–U+009F). The canonical forms are `\b \t \n \f \r`, and `\u00xx` in lowercase hex for the rest, as in RFC 8785. `\/` is not canonical. No vector exercises this.

**R5. Rules on members that no step reads are enforced at parse.**
Section 2.1 says "A member of the wrong JSON type is refused at the step that reads it", but steps 1–3 never read v, kind (outside judgement), key, version, supersedes, writer, actor or act_time. These are refused at parse (R1):
- a member not in the Section 2.2 list (a13, "No other member is allowed");
- a missing member from v, kind, key, version, writer, body (a14);
- v other than "verdict-record/1";
- a malformed key, version, writer, supersedes (null for version 1, a digest for later versions), act_time or actor;
- a body that is not an object.

A missing check or evidence is left to steps 1 and 2, as Section 2.2 says. Any kind string is accepted, including kinds this document does not define.

**R6. The body.claim rules of Section 2.3 are enforced at parse.**
"When ref is used, the same entry MUST also appear in evidence" is not assigned to any step, so it is treated like R5: refused, no steps (c11). The other reading, step 2 FAIL, gives the same state (refused) but different step results.

**R7. check may hold only rule, inputs and result.**
Section 2.2 lists "the members rule …, inputs … and result" without saying "exactly". Any other member makes step 1 FAIL, by analogy with "exactly two members" for evidence entries. No vector exercises this.

**R8. A malformed evidence entry is a step 2 FAIL, not NOT RUN.**
Step 2: "The member evidence MUST be an array of entries as in Section 2.2". An entry with an extra member (c02), or a sha256 that is not lowercase hex (c03, Section 2.1 "Hex is lowercase"), breaks that condition, so the result is FAIL. NOT RUN is kept for items the checker does not hold or that do not verify. An uppercase digest is treated as malformed, not as "no held item matches".

**R9. An empty evidence array passes step 2.**
Step 2 asks for "an array of entries", and the per-entry conditions hold for every entry when there are none. Section 2.2 makes only a record *without* evidence fail. So `"evidence":[]` gives PASS (c12, released). Section 5 confirms that completeness is not claimed.

**R10. How nested verdict records are checked.**
Step 2 says "The checker's policy sets how deep such citations are followed; beyond that depth, step 2 is NOT RUN", without saying how depth is counted. The record being checked is at depth 0, and an item it cites is at depth 1. A citation at depth d is followed only if d ≤ max_depth, so max_depth 0 follows none (c08).
- The nested record is checked by Section 4 with the same policy and the same pool of held items.
- Its upper time bound is the item's `upper_time_bound` from the vector file.
- Following the README, the item verifies only when its state is released. Otherwise outer step 2 is NOT RUN, not FAIL, because "An item that does not verify … is not relied on: step 2 is then NOT RUN" (c10).

**R11. Upper time bounds are compared as times.**
"MUST NOT be later than": an equal bound is allowed. Both bounds have the fixed format of Section 2.1, so they are compared as strings. The bound check applies to any item whose verification gives a bound, not only verdict records (c09 → NOT RUN).

**R12. A cited verdict record with no upper time bound does not verify.**
Section 3 needs an upper time bound for every record, and "If the container does not show the record, the state is held". So the nested record cannot be released, and outer step 2 is NOT RUN. No vector exercises this.

**R13. A format the policy lists but the checker cannot verify.**
Step 2 says "verified by the rules of the format its entry names". If the checker holds no rules for the format, the item does not verify and step 2 is NOT RUN. No vector exercises this.

**R14. Step 3 runs even when step 1 FAILed, and needs its own inputs.**
Section 4.1: "When a step cannot run, the check goes on with its other steps." If check, check.rule or check.result is missing, step 3 lacks an input, so it is NOT RUN, not FAIL (b01, b02). The state is refused either way, because step 1 FAILs.

**R15. With the rule judgement, step 3 PASSes with nothing to re-run.**
Step 3 begins "If the rule is not judgement, …" and says nothing for judgement. Section 4.4 releases only when "steps 1 to 3 PASS". Appendix A presents a judgement record as checkable to a state ("verifies each by its own format, and reports the state"), so step 3 PASSes trivially (b04, f01). If step 1 FAILed because judgement is not allowed for the kind, step 3 is still a trivial PASS (b03). The state is refused either way.

**R16. Inputs the test rule cannot read are a step 3 FAIL.**
If `check.inputs` is missing or is not exactly {value, min} with string values, or if a named member is absent from body, that is a step 3 FAIL, not NOT RUN. The body is fixed in the record's bytes, so this is not "a statement that the issuer or the presenter could withhold" (Section 4.2). The README treats any non-integer as "the wrong type". No vector exercises this.

**R17. The record's own upper time bound must be present and well-formed.**
If it is missing or malformed, the state is held and no step runs (Section 3, "If the container does not show the record, the state is held"). Policy validity is checked first, because an invalid policy gives "no verdict" whatever else holds. No vector exercises the missing bound. e01 exercises the invalid policy.

## Notes, not readings
- Comparing check.result with the re-run is type-aware (`"pass"` ≠ `true`).
- My canonicaliser reproduces the draft's Appendix A digest (2a85c94e…41c45, vector f01) and every vector's `policy_sha256`.
