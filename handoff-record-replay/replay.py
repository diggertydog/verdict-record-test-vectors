#!/usr/bin/env python3
"""replay: re-derive a loaded handoff's record from its bytes and say whether it is the record the store holds.

Nothing is written anywhere. Any machine can run it:
  - the bytes: the exact bytes of the Drive file (any route that returns them; the record's sha256 refuses any other);
  - the record: the record's claim_metadata as JSON (--record-json): the `text` of the claude.ai Sencor connector's
    read_record(id, part='claim_metadata'), or a whole read_record answer;
  - the extractor: the program whose sha256 the record names (extractor_sha256). The vl_docs.py beside this file
    is a REDACTED copy of it (store code removed), so its sha256 differs and the best answer here is
    IDENTICAL_BY_OTHER_EXTRACTOR.

The answer, per record:
  REFUSED                       the bytes are not the bytes recorded (sha256 or length), or the record is an alias;
  IDENTICAL                     the named extractor, run on these bytes, gives every recorded statement back, field
                                for field, and no other;
  IDENTICAL_BY_OTHER_EXTRACTOR  the same, but the extractor the record names was not available and another was used
                                (said by sha256; the record's own extractor is then NOT shown to reproduce it);
  DIFFERENT                     the extractor gives a different set of statements; the differences are counted by field.

Usage:
  replay.py --bytes FILE --record-json FILE [--extractor PATH]
Exit status: 0 if every record replayed is IDENTICAL, 1 otherwise.

Limit: the record is served by the box that wrote it. A replay off the box checks the record against the bytes and
a named program; it does not show that the record was not rewritten on the box.
"""
import argparse, hashlib, importlib.util, json, os, subprocess, sys

FIELDS = ('stmt_key', 'kind', 'origin', 'section', 'label', 'line', 'byte_start', 'byte_end', 'text', 'time_hint',
          'family', 'state_in_text', 'attributed_by', 'about')
HERE = os.path.dirname(os.path.abspath(__file__))


def sha256_file(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def load_extractor(path):
    spec = importlib.util.spec_from_file_location('handoff_extractor', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def find_extractor(named, given):
    """The extractor whose sha256 the record names: the given path, else any .py beside this file."""
    cands = [given] if given else [os.path.join(HERE, f) for f in sorted(os.listdir(HERE)) if f.endswith('.py')]
    shas = {p: sha256_file(p) for p in cands if p and os.path.exists(p)}
    for p, s in shas.items():
        if s == named:
            return p, s, True
    fallback = given or os.path.join(HERE, 'vl_docs.py')
    return fallback, shas.get(fallback) or sha256_file(fallback), False


def record_from_json(path):
    d = json.load(open(path))
    if isinstance(d, dict) and 'text' in d and d.get('part') == 'claim_metadata':
        d = json.loads(d['text'])
    return d


def replay_one(md, raw, extractor=None, claim_id=None):
    out = {'claim_id': claim_id, 'ref': md.get('ref'), 'title': md.get('title'), 'sha256_recorded': md.get('sha256'),
           'sha256_bytes': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
    if out['sha256_bytes'] != md.get('sha256') or len(raw) != md.get('bytes'):
        out.update(verdict='REFUSED', why='these bytes are not the bytes recorded')
        return out
    if md.get('same_bytes_as'):
        out.update(verdict='REFUSED', why=f"alias: same bytes as {md['same_bytes_as']}, which holds the statements")
        return out
    path, used, named_ok = find_extractor(md.get('extractor_sha256'), extractor)
    derived = load_extractor(path).extract(raw)['statements']
    rec = md.get('statements') or []
    key = lambda s: (s['byte_start'], s['byte_end'], s['kind'])
    a = {key(s): s for s in rec}
    b = {key(s): s for s in derived}
    diff = {f: sum(1 for k in a.keys() & b.keys() if a[k].get(f) != b[k].get(f)) for f in FIELDS}
    only_rec, only_der = len(a.keys() - b.keys()), len(b.keys() - a.keys())
    same = not only_rec and not only_der and not any(diff.values()) and len(rec) == len(a) and len(derived) == len(b)
    out.update({'extractor_named': md.get('extractor_sha256'), 'extractor_used': used, 'extractor_path': path,
                'statements_recorded': len(rec), 'statements_derived': len(derived),
                'only_in_record': only_rec, 'only_derived': only_der, 'differences_by_field': diff,
                'verdict': ('IDENTICAL' if named_ok else 'IDENTICAL_BY_OTHER_EXTRACTOR') if same else 'DIFFERENT'})
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--bytes')
    ap.add_argument('--record-json')
    ap.add_argument('--extractor')
    ap.add_argument('--out', help='write every per-record result here as JSON lines')
    a = ap.parse_args()
    results = []
    if not a.bytes or not a.record_json:
        ap.error('give --bytes and --record-json')
    results.append(replay_one(record_from_json(a.record_json), open(a.bytes, 'rb').read(), a.extractor))
    if a.out:
        with open(a.out, 'w') as f:
            for r in results:
                f.write(json.dumps(r, sort_keys=True) + '\n')
    tally = {}
    for r in results:
        tally[r['verdict']] = tally.get(r['verdict'], 0) + 1
    if len(results) == 1:
        print(json.dumps(results[0], indent=1, sort_keys=True))
    print(json.dumps({'records': len(results), 'verdicts': tally,
                      'statements_recorded': sum(r.get('statements_recorded', 0) for r in results),
                      'statements_derived': sum(r.get('statements_derived', 0) for r in results),
                      'field_differences': sum(sum((r.get('differences_by_field') or {}).values()) for r in results)},
                     sort_keys=True))
    sys.exit(0 if results and all(r['verdict'] == 'IDENTICAL' for r in results) else 1)


if __name__ == '__main__':
    main()
