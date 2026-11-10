"""Held by the checker, for the vectors of -02 Appendix A.2 only: format rules for delegation hop records that apply
the requirement the draft says that format has, a signature (-02 lines 1185-1187: "The hops carry no signature,
which the format of [I-D.durga-agenttrust-trace-verification] requires. A checker that applies that requirement
reports held, at step 2."). This module checks only that requirement's first condition, that a signature is
present; it does not implement that format's signature check, which no vector here needs.
"""
import json

SOURCE = {"url": "https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt", "lines": "1185-1187",
          "note": "test-only: an item without a signature member does not meet the format's rules"}


class HopsSignatureRequired:
    NAME = "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/"

    @staticmethod
    def check_item(b, ctx):
        try:
            d = json.loads(b)
        except ValueError:
            return False, "not JSON", None
        if not (isinstance(d, dict) and "signature" in d):
            return False, "the hop record carries no signature, which its format requires", None
        return False, "this test-only module holds no signature check", None


FORMATS = (HopsSignatureRequired,)
