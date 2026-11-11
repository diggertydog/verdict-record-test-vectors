# One chain case: our state and steps beside the case's

Case commit read: `f0d766a1ca8422c64ad792fad7876db2737a7f72`. Policy: the case's own, verbatim (sha256 `c2839fed12d7a006c89810a8e5dfaab83558fcca314e080191a4a84bb5c02582`). Written by run.py.

| directory | record | stated | ours | container | agree | class |
|---|---|---|---|---|---|---|
| positive | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| positive | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| stated-negative | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| stated-negative | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N1-approval-of-other-arguments-everything-downstream-claims-as-approved | verdict-record.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | shows the record | yes |  |
| N1-approval-of-other-arguments-everything-downstream-claims-as-approved | verdict-record-other-result.json | released PASS/PASS/PASS | released PASS/PASS/PASS | not published | yes |  |
| N2-verdict-altered-after-the-packet-cited-it | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N2-verdict-altered-after-the-packet-cited-it | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N3-settlement-150-with-headline-120 | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N3-settlement-150-with-headline-120 | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N4-confirm-without-approval | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N4-confirm-without-approval | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N5-packet-cites-another-verdict-about-the-same-chain | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N5-packet-cites-another-verdict-about-the-same-chain | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N6-custody-event-altered | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N6-custody-event-altered | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N7-ledger-event-altered-after-chaining | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N7-ledger-event-altered-after-chaining | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N8-settlement-anchor-content-changed-hash-stale | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N8-settlement-anchor-content-changed-hash-stale | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N9-manifest-without-settlement-block | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N9-manifest-without-settlement-block | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N10-receipt-payload-edited-after-signing | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N10-receipt-payload-edited-after-signing | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N11-receipt-signed-by-a-key-not-the-issuers | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N11-receipt-signed-by-a-key-not-the-issuers | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N12-issuer-id-not-the-kid | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N12-issuer-id-not-the-kid | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N13-a2-altered-after-the-verdict-cited-it | verdict-record.json | held PASS/NOT RUN/NOT RUN | held PASS/NOT RUN/NOT RUN | shows the record | yes |  |
| N13-a2-altered-after-the-verdict-cited-it | verdict-record-other-result.json | held PASS/NOT RUN/NOT RUN | held PASS/NOT RUN/NOT RUN | not published | yes |  |
| N14-dispute-reason-code-missing | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N14-dispute-reason-code-missing | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N15-approval-after-the-allow-outcome | verdict-record.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | shows the record | yes |  |
| N15-approval-after-the-allow-outcome | verdict-record-other-result.json | released PASS/PASS/PASS | released PASS/PASS/PASS | not published | yes |  |
| N16-one-approval-used-twice | verdict-record.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | shows the record | yes |  |
| N16-one-approval-used-twice | verdict-record-other-result.json | released PASS/PASS/PASS | released PASS/PASS/PASS | not published | yes |  |
| N17-money-moved-nothing-recorded | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N17-money-moved-nothing-recorded | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N18-action-packet-hash-not-the-action-hash | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N18-action-packet-hash-not-the-action-hash | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N19-scope-event-executed-action-altered-and-rechained | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N19-scope-event-executed-action-altered-and-rechained | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N20-manifest-without-any-settlement-block | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N20-manifest-without-any-settlement-block | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N21-approval-event-for-another-action | verdict-record.json | released PASS/PASS/PASS | released PASS/PASS/PASS | shows the record | yes |  |
| N21-approval-event-for-another-action | verdict-record-other-result.json | refused PASS/PASS/FAIL | refused PASS/PASS/FAIL | not published | yes |  |
| N22-a2-issuer-seal-broken | verdict-record.json | held PASS/NOT RUN/NOT RUN | held PASS/NOT RUN/NOT RUN | shows the record | yes |  |
| N22-a2-issuer-seal-broken | verdict-record-other-result.json | held PASS/NOT RUN/NOT RUN | held PASS/NOT RUN/NOT RUN | not published | yes |  |
