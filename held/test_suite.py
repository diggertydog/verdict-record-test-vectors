"""Held by the checker: the test-only rule and evidence formats these vectors define.

Source: README.md of this repository, sections "Test-only evidence formats" and "Test-only rule", and
proposals/README.md for the three proposal formats. These are not part of draft-wright-verdict-record-02; a checker
holds them only to run these vectors (-02 lines 367-369: the rule specifications a checker holds are its own input).
"""

SOURCE = {"url": "https://github.com/diggertydog/verdict-record-test-vectors/blob/checker-to-02/README.md",
          "sections": ["Test-only evidence formats", "Test-only rule"],
          "also": "proposals/README.md (provider-attestation, inference-proof)"}


class AtLeast:
    """urn:example:verdict-record:rule:at-least. check.inputs has exactly the members value and min, each resolved
    as Section 2.2 of -02 says (a member of body, or an evidence binding). Both must be integers, otherwise the input
    is of the wrong type, a FAIL of step 3. The result is "pass" when value >= min, else "fail"."""
    NAME = "urn:example:verdict-record:rule:at-least"

    @staticmethod
    def input_problems(values, names):
        if names != ["min", "value"]:
            return ["the rule's inputs are exactly value and min"]
        return ["input %s is not an integer" % n for n in names
                if n in values and not (isinstance(values[n], int) and not isinstance(values[n], bool))]

    @staticmethod
    def rerun(values, ctx):
        return "pass" if values["value"] >= values["min"] else "fail"


class Equals:
    """urn:example:verdict-record:rule:equals (added for -02). check.inputs has exactly the members a and b, each
    resolved as Section 2.2 of -02 says; any JSON value. The result is "equal" when the two values are equal as JSON
    values, else "different". It lets a vector bind an input to an item's digest (no pointer), which is a string."""
    NAME = "urn:example:verdict-record:rule:equals"

    @staticmethod
    def input_problems(values, names):
        return [] if names == ["a", "b"] else ["the rule's inputs are exactly a and b"]

    @staticmethod
    def rerun(values, ctx):
        # "equal as JSON values", as -03 Section 4.3 defines equality (numbers by mathematical value).
        import decimal

        def num(x):
            return isinstance(x, (int, float, decimal.Decimal)) and not isinstance(x, bool)

        def eq(a, b):
            if num(a) and num(b):
                return decimal.Decimal(str(a)) == decimal.Decimal(str(b))
            if isinstance(a, bool) or isinstance(b, bool) or a is None or b is None:
                return a is b
            if isinstance(a, str) and isinstance(b, str):
                return a == b
            if isinstance(a, list) and isinstance(b, list):
                return len(a) == len(b) and all(eq(x, y) for x, y in zip(a, b))
            if isinstance(a, dict) and isinstance(b, dict):
                return set(a) == set(b) and all(eq(a[k], b[k]) for k in a)
            return False
        return "equal" if eq(values["a"], values["b"]) else "different"


class TestFormat:
    def __init__(self, name, met, note):
        self.NAME, self._met, self._note = name, met, note

    def check_item(self, b, ctx):
        return (self._met, None if self._met else self._note, None)


RULES = (AtLeast, Equals)
FORMATS = (
    TestFormat("urn:example:verdict-record:format:opaque", True, ""),
    TestFormat("urn:example:verdict-record:format:never-verifies", False, "this test format's rules are never met"),
    TestFormat("urn:example:verdict-record:format:provider-attestation", True, ""),
    TestFormat("urn:example:verdict-record:format:inference-proof", True, ""),
)
