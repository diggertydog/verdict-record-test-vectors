#!/usr/bin/env python3
"""vl_docs — load a findings file (handoff / leg report) from Drive into the store as a fingerprinted record.

verdict-lanes leg, lane 3, 10 Nov 2026.

What it does, deterministically (same bytes in -> same record out):
  1. fingerprint: sha256 and byte length of the exact bytes the Drive connector returned;
  2. statements, each a byte range [start, end) of those bytes, never a paraphrase:
     - his_words   origin=darren  : a quoted span ("..." or “...”) on a line attributed to Darren, either
                                    because the line names him / 'his words' / 'he said', or because it sits under a
                                    bold label naming him (e.g. '**Darren's (Paris time):**');
     - reported_decision origin=cowork, about darren : a line where the author reports a decision of Darren's
                                    ('Darren's direction: ...', 'Darren approved ...') without his words; never read as his words;
     - cowork_call origin=cowork  : a list item under a bold label naming Cowork (e.g. '**Cowork's calls, his to overrule:**');
     - open_item   origin=cowork  : a top-level list item in a section whose heading says it is for Darren to do or
                                    decide ('Acts only Darren can perform', 'Waiting on Darren', ...), with the family
                                    (money, name, intent, risk appetite, hand) read from the item's own text when stated;
  3. (not in this published copy) the loader that writes the record into Sencor's store, and its usage.

Published copy: the extractor only. Run it on a file to see the statements it takes:
  python3 vl_docs.py <bytes-file>        -> JSON on stdout: sha256, bytes, statements
"""
import argparse, hashlib, json, re, subprocess, sys

EXTRACTOR_VERSION = 'vl_docs/1 2026-11-10'
H = re.compile(rb'^(#{1,6})\s+(.*?)\s*$')
LABEL = re.compile(rb'^\s*(?:[-*]\s+)?\*\*([^*]{2,120}?:)\*\*\s*$|^\s*(?:[-*]\s+)?\*\*([^*]{2,120}?)\*\*\s*:\s*$')
LABEL_INLINE = re.compile(rb'^\s*\*\*([^*]{2,120}?:)\*\*')
LIST = re.compile(rb'^(\s*)(?:[-*+]|\d+[a-z]?[.)])\s+(.*)$')
QUOTE = re.compile('(“[^”]{1,2000}”|"[^"\n]{1,2000}")'.encode())
TIME = re.compile(rb'^\s*(?:[-*]|\d+[.)])?\s*\*{0,2}~?(\d{1,2}:\d{2}(?:,\s*\d{1,2}\s+\w{3})?)\*{0,2}\s*:')
DARREN_LINE = re.compile(rb"(?i)\bdarren\b|\bhis words\b|\bhe (?:also )?(?:said|says|wrote|asked|replied|answered)\b")
# a quote is his on a line only when an explicit speech marker ends within 80 bytes before it, with no quote between
ATTR = re.compile(rb"(?i)(?:darren(?:['\xe2\x80\x99]s)?\s*(?:\([^)]{0,40}\))?\s*(?::|,?\s*(?:said|says|wrote|writes|asked|asks|replied|answered|typed|answer(?:ed)?|in chat)\b)"
                  rb"|approved by darren[^\"\xe2]{0,40}\("
                  rb"|\b(?:in )?his (?:own )?words\b[^\"\xe2]{0,6}"
                  rb"|\bhe (?:also )?(?:said|says|wrote|writes|asked|asks|replied|answered|typed)\b[^\"\xe2]{0,6})[^\"\xe2]{0,40}$")
DARREN_LABEL = re.compile(rb"(?i)\bdarren\b|\bhis (?:words|decisions?|answers?|calls?)\b")
COWORK_LABEL = re.compile(rb"(?i)\bcowork\b")
OPEN_HEAD = re.compile(rb"(?i)(acts? only (?:darren|he)|only darren can|for darren|waiting on (?:darren|him)|left for darren|"
                       rb"darren['\xe2\x80\x99]*s? (?:acts|queue|list|actions|to-?do|decisions? (?:pending|open|owed|outstanding))|"
                       rb"his (?:acts|queue|list)|what (?:darren|he) (?:must|needs to|has to))")
FAMILY = re.compile(r"(?i)\b(money|name|intent|risk[ _]appetite|risk|hand)\b")
CODE_SPAN = re.compile(rb'`[^`\n]*`')
# a line where the author reports a decision of Darren's without quoting him (kept apart from his_words: origin cowork)
REPORTED = re.compile(rb"(?i)\bdarren(?:['\xe2\x80\x99]s)?\s+(?:own\s+)?(?:direction|decision|decided|ruling|ruled|approved|approves|agreed|agrees|"
                      rb"rejected|rejects|chose|chooses|confirmed|confirms|corrected|instructed|directed|declined|signed|accepted|"
                      rb"accepts|refused|overruled|vetoed|authori[sz]ed|answered)\b")


def family_of(text):
    # the family as the item states it, in a parenthesis or after a colon; never inferred from the topic
    for par in re.findall(r'\(([^()]{1,60})\)', text):
        m = FAMILY.findall(par)
        if m:
            fams = []
            for f in m:
                f = f.lower().replace(' ', '_')
                f = 'risk_appetite' if f == 'risk' else f
                if f not in fams:
                    fams.append(f)
            return fams
    return []


def extract(raw):
    sha = hashlib.sha256(raw).hexdigest()
    try:
        raw.decode('utf-8')
    except UnicodeDecodeError as e:
        return {'sha256': sha, 'bytes': len(raw), 'refused': f'not utf-8: {e}'}
    out, heads, label, label_kind = [], [], None, None
    pos, line_no, in_fence = 0, 0, False
    for line in raw.split(b'\n'):
        line_no += 1
        start = pos
        pos += len(line) + 1
        if line.lstrip().startswith(b'```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = H.match(line)
        if m:
            lvl = len(m.group(1))
            heads = [h for h in heads if h[0] < lvl] + [(lvl, m.group(2).decode('utf-8', 'replace'))]
            label, label_kind = None, None
            continue
        line_label, line_kind = label, label_kind
        lm = LABEL.match(line)
        li = None if lm else LABEL_INLINE.match(line)
        if lm or li:
            lab = next(g for g in (lm or li).groups() if g is not None)
            kind_ = 'cowork' if COWORK_LABEL.search(lab) else ('darren' if DARREN_LABEL.search(lab) else 'other')
            line_label, line_kind = lab.decode('utf-8', 'replace'), kind_
            if lm:  # a label on a line of its own governs the lines under it; an inline label governs its own line only
                label, label_kind = line_label, line_kind
        section = ' > '.join(h[1] for h in heads)
        head_text = heads[-1][1].encode() if heads else b''
        tm = TIME.match(line)
        time_hint = tm.group(1).decode() if tm else None
        lst = LIST.match(line)
        # his words
        line_is_darren = bool(DARREN_LINE.search(line)) and not COWORK_LABEL.search(line[:40])
        if (line_kind == 'darren' and (lst or lm or li)) or line_is_darren:
            masked = CODE_SPAN.sub(lambda c: b'\x00' * len(c.group(0)), line)
            for q in QUOTE.finditer(masked):
                a, b = q.start() + 1 + (2 if masked[q.start():q.start()+3] == '“'.encode() else 0), q.end() - (3 if masked[q.end()-3:q.end()] == '”'.encode() else 1)
                # the span between the quote marks, exact bytes
                if line[q.start():q.start()+3] == '“'.encode():
                    a, b = q.start() + 3, q.end() - 3
                else:
                    a, b = q.start() + 1, q.end() - 1
                if b <= a:
                    continue
                if line_kind != 'darren':
                    prev = max([0] + [x.end() for x in QUOTE.finditer(masked) if x.end() <= q.start()])
                    if not ATTR.search(line[max(prev, q.start() - 80):q.start()]):
                        continue
                words = line[a:b].decode('utf-8')
                if len(words.split()) < 2 and not re.search(r'[A-Za-z]{4,}', words):
                    continue
                out.append({'kind': 'his_words', 'origin': 'darren', 'section': section, 'label': line_label,
                            'line': line_no, 'byte_start': start + a, 'byte_end': start + b, 'text': words,
                            'time_hint': time_hint,
                            'attributed_by': 'label' if line_kind == 'darren' else 'line'})
        if REPORTED.search(line) and not any(o['line'] == line_no and o['kind'] == 'his_words' for o in out[-20:]):
            body = lst.start(2) if lst else len(line) - len(line.lstrip())
            a, b = start + body, start + len(line)
            if b > a:
                out.append({'kind': 'reported_decision', 'origin': 'cowork', 'about': 'darren', 'section': section,
                            'label': line_label, 'line': line_no, 'byte_start': a, 'byte_end': b,
                            'text': raw[a:b].decode('utf-8'), 'time_hint': time_hint, 'attributed_by': 'line'})
        # cowork calls
        if line_kind == 'cowork' and lst and not lm:
            a = start + lst.start(2)
            b = start + len(line)
            out.append({'kind': 'cowork_call', 'origin': 'cowork', 'section': section, 'label': label,
                        'line': line_no, 'byte_start': a, 'byte_end': b, 'text': raw[a:b].decode('utf-8'),
                        'time_hint': time_hint, 'attributed_by': 'label'})
        # open items for Darren
        if lst and len(lst.group(1)) == 0 and OPEN_HEAD.search(head_text):
            a = start + lst.start(2)
            b = start + len(line)
            text = raw[a:b].decode('utf-8')
            low = text.lower()
            state = 'closed_in_text' if ('~~' in text[:6] or re.search(r'\*\*done\b|\bdone\.\*\*|^done\b', low)) else 'open_in_text'
            out.append({'kind': 'open_item', 'origin': 'cowork', 'section': section, 'label': label,
                        'line': line_no, 'byte_start': a, 'byte_end': b, 'text': text,
                        'family': family_of(text), 'state_in_text': state, 'attributed_by': 'heading'})
    for s in out:
        s['stmt_key'] = hashlib.sha256(f"{sha}|{s['kind']}|{s['byte_start']}|{s['byte_end']}".encode()).hexdigest()[:32]
    return {'sha256': sha, 'bytes': len(raw), 'statements': out}


# (not in this published copy) the store client, the loader, unload and compare: they read and write Sencor's store.
if __name__ == '__main__':
    print(json.dumps(extract(open(sys.argv[1], 'rb').read()), ensure_ascii=False, indent=1))
