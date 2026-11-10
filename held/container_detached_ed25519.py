"""Held by the checker: one container rule (draft-wright-verdict-record-02 Section 3, lines 318-330).

The container is the stand-in an interop case uses in place of a SCITT Signed Statement: a detached Ed25519
signature over the record's exact bytes, the key shown to belong to the writer by the checker's trust anchors.
Source: Laurent Lemonnier, dps-scitt-decision-layer, interop/verdict-record/README.md lines 127-129 ("What is not
shown"), at commit 9e1c7a0b047129d71c5694995e0014eecdf2289c; the member names are those of the containers that case
publishes (out/**/verdict-record.container.json). Trust anchor set: writers {writer: {key_ref: public key hex}}.

STOPGAP, labelled: this is not the container -02 names (Section 3 names a SCITT Signed Statement with a Receipt). It
is held only so that the one chain case's published containers can be read. Retires when the case, or the vectors,
carry a SCITT container and this checker holds a rule for it.
"""
import base64
import hashlib

SOURCE = {"url": "https://github.com/Laurent-Lemonnier/dps-scitt-decision-layer/blob/"
                 "9e1c7a0b047129d71c5694995e0014eecdf2289c/interop/verdict-record/README.md#L127-L129",
          "stopgap": "stand-in container; retires when a SCITT container rule is held"}


class DetachedEd25519:
    KIND = "detached-ed25519-signature"

    @staticmethod
    def shows(record_bytes, writer, c, anchors):
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        from cryptography.exceptions import InvalidSignature
        if c.get("record_sha256") != hashlib.sha256(record_bytes).hexdigest():
            return "the container names other bytes"
        if c.get("algorithm") != "Ed25519":
            return "the container's algorithm is not one this rule reads"
        if c.get("writer") != writer:
            return "the container binds the bytes to a party the record does not name in writer"
        key = (anchors.get("writers") or {}).get(writer, {}).get(c.get("key_ref"))
        if key is None:
            return "no key in the trust anchors for this writer and key_ref"
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)).verify(base64.b64decode(c["signature_b64"]),
                                                                          record_bytes)
        except (InvalidSignature, ValueError, KeyError):
            return "the signature does not hold under the writer's key"
        return None


CONTAINERS = (DetachedEd25519,)
