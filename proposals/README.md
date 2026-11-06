# Proposal cases for IETF 127: open questions as runnable cases

**These are proposals for discussion, not draft text.** Each case is a verdict record that a checker of
draft-wright-verdict-record-02 can run today. Each states, by hand and with the section it rests on, what -02
gives now (`expected_under_02`), and what a proposal would change (`proposed`, in prose). The point is to argue
about behaviour rather than wording: run a case, see what your checker says, and say what it should say.

The cases use the record shape, test formats and test rule of the main vectors (see the top-level README), plus
three test-only formats:

- `urn:example:verdict-record:format:provider-attestation`: a provider's statement about which model served a
  request. Every item verifies, as with `opaque`.
- `urn:example:verdict-record:format:inference-proof`: a proof of which model ran. Every item verifies; the case
  gives the item its own upper time bound.
- `urn:example:verdict-record:format:salted-commitment`: a commitment `sha256(salt || item)` to data the record
  must not carry. Only a checker holding the salt could verify it; no checker in these cases does.

| Case | Question | -02 today |
|---|---|---|
| p01-model-declared | Should a checker report how strongly a record shows which model produced it, derived from what is attached? | released |
| p02-model-attested | The same with a provider's statement attached. Under -02 it reads exactly like p01: that is the gap. | released |
| p03-model-proof-after-reply | Does a proof made after the answer was relied on count? -02 already says no, through the upper-time-bound rule. | held |
| p04-cites-superseded-version | A cited record has a later version that reaches the opposite result. What should the report say? | released |
| p05-evidence-age | Should a policy be able to set a maximum evidence age, measured between upper time bounds and never by a clock? | released |
| p06-salted-commitment | Should a salted commitment be an evidence format, so a record can point at personal data without carrying it? | held |
| p07-negative-judgement-no-cause | Should a refusal reached by judgement have to cite at least one item it rests on? | released |
| p08-irontrellis-refusal | A verdict over a published IronTrellis authority history, whose rule is IronTrellis's own replay and whose result is a refusal with its cause. Is this the right binding for a third party to re-run it? | held without the IronTrellis rule; released or refused with it |

p08 cites two files of the IronTrellis repository at a pinned commit, too large to embed: `evidence_fetch` gives
the URL and SHA-256 of each. Its rule inputs are bound to evidence by JSON Pointer, which is -02 text, so the
reference checker here (written for -01) does not run it.

## Running

    python3 proposals/gen.py      # regenerates the cases
    python3 proposals/run.py      # runs the reference checker and compares with expected_under_02

`results-reference-checker.json` holds the reference checker's results: it agrees with `expected_under_02` on all
seven. The reference checker was written on the author's side, so that agreement is not independent. **Results
from checkers written by other parties are wanted**, and a disagreement is the most useful result: it shows where
the text does not settle the answer.

## Where the proposals come from

Each case names its entry in the proposed-changes log for the next version of the standard behind this draft
(V13-05 to V13-10). The log is a working document; nothing in it is decided until the author says so.
