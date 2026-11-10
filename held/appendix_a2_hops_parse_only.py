"""Held by the checker, for the vectors of -02 Appendix A.2 only: format rules for delegation hop records that
require the item to be a JSON object and nothing else. This is the second checker of -02 lines 1187-1190 ("a
checker that verified these hop records without a signature, which this document does not yet define"); it is not
the format of draft-durga-agenttrust-trace-verification, which requires a signature (-02 lines 1185-1186).
Source: draft-wright-verdict-record-02 lines 1185-1194; open point I-9 (what "verify" means without a signature).
"""
import json

SOURCE = {"url": "https://www.ietf.org/archive/id/draft-wright-verdict-record-02.txt", "lines": "1185-1194",
          "note": "test-only reading of the hop format: parse only, no signature"}


class HopsParseOnly:
    NAME = "https://datatracker.ietf.org/doc/draft-durga-agenttrust-trace-verification/"

    @staticmethod
    def check_item(b, ctx):
        try:
            ok = isinstance(json.loads(b), dict)
        except ValueError:
            ok = False
        return ok, None if ok else "not a JSON object", None


FORMATS = (HopsParseOnly,)
