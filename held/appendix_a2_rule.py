"""Held by the checker: the example rule of draft-wright-verdict-record-02 Appendix A.2.

Source: draft-wright-verdict-record-02, Appendix A.2, lines 1075-1087 of the published text
(https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt, md5 e02052750dc143f4aaea2d56abcfc5dc).
The draft names the rule "for this example"; Appendix B asks where rule names are registered.
"""

SOURCE = {"url": "https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt", "lines": "1075-1087"}


class HopContinuityAttenuation:
    """Exactly four inputs: parent_hash and parent_digest (strings), parent_scopes and child_scopes (arrays of
    strings). "attenuated_and_linked" when parent_hash equals parent_digest and every member of child_scopes is a
    member of parent_scopes, "not_attenuated_or_not_linked" otherwise (-02 lines 1077-1082)."""
    NAME = "urn:example:verdict-record:rule:hop-continuity-attenuation:v1"
    INPUTS = ["child_scopes", "parent_digest", "parent_hash", "parent_scopes"]

    @classmethod
    def input_problems(cls, values, names):
        if names != cls.INPUTS:
            return ["the rule's inputs are exactly " + ", ".join(cls.INPUTS)]
        out = []
        for n in ("parent_hash", "parent_digest"):
            if n in values and not isinstance(values[n], str):
                out.append("input %s is not a string" % n)
        for n in ("parent_scopes", "child_scopes"):
            if n in values and not (isinstance(values[n], list) and all(isinstance(x, str) for x in values[n])):
                out.append("input %s is not an array of strings" % n)
        return out

    @staticmethod
    def rerun(v, ctx):
        ok = v["parent_hash"] == v["parent_digest"] and all(s in v["parent_scopes"] for s in v["child_scopes"])
        return "attenuated_and_linked" if ok else "not_attenuated_or_not_linked"


RULES = (HopContinuityAttenuation,)
