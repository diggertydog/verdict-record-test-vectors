# Handoff-record replay

A handoff record says three things about a document: which bytes were read (their sha256 and length), which program read them (its sha256), and every statement the program took from them, each as a byte range of those bytes. Replay means running the program on the bytes again and comparing what comes out with the record, field for field. It needs no network and writes nothing.

## Files

| file | what it is |
|---|---|
| `replay.py` | The replay. Python 3, standard library only. |
| `vl_docs.py` | The extractor, as a **redacted copy**: the code that writes records into Sencor's store has been removed. The extraction itself (`extract()`) is unchanged. Because the file is not the whole program, its sha256 is **not** the `extractor_sha256` a record names. |

## Check what you fetched

```
sha256sum replay.py vl_docs.py
```

Compare those values with the files in this repository's commit history (`git log -p -- handoff-record-replay/`) and with any copy you got by another route. A copy with different bytes is a different program.

## Run it on a file of your own (no Sencor data needed)

1. Make a small Markdown file, `sample.md`. This invented example gives the extractor something to find:
   ```
   ## Waiting on Darren
   - Choose the meeting room (intent)

   **Cowork's calls:**
   - Use the larger room
   ```
2. Make a record from it, and name the extractor by its hash:
   ```
   python3 vl_docs.py sample.md > record.json
   python3 -c "import json,hashlib; r=json.load(open('record.json')); r['extractor_sha256']=hashlib.sha256(open('vl_docs.py','rb').read()).hexdigest(); json.dump(r,open('record.json','w'))"
   ```
3. Replay it: `python3 replay.py --bytes sample.md --record-json record.json`. The verdict is `IDENTICAL`.
4. Change one byte of `sample.md` and replay again. The verdict is `REFUSED`: these are not the bytes recorded.
5. Restore the file, edit one statement's `byte_end` in `record.json`, and replay. The verdict is `DIFFERENT`. A statement is matched by its byte range, so the moved statement counts as one `only_in_record` and the program's own as one `only_derived`.

## Run it against a Sencor record

Whoever holds a handoff's exact bytes and its record (the record's `claim_metadata` as JSON, for example from the claude.ai Sencor connector's `read_record(id, part='claim_metadata')`) runs:

```
python3 replay.py --bytes handoff.md --record-json record.json
```

The answer to expect from this copy is `IDENTICAL_BY_OTHER_EXTRACTOR`, with `statements_recorded` equal to `statements_derived` and `field_differences` 0. That means this extractor gives exactly the recorded statements back from those bytes, but this is not the file whose hash the record names.

Possible verdicts:

| verdict | meaning |
|---|---|
| `REFUSED` | The bytes are not the bytes recorded, or the record is an alias whose statements are held in another record. |
| `IDENTICAL` | The extractor the record names, run on these bytes, gives exactly the record. |
| `IDENTICAL_BY_OTHER_EXTRACTOR` | The same result, from a program other than the one the record names. |
| `DIFFERENT` | The program gives other statements. The differences are counted by field. |

## What this does not show

- **No records and no documents are published here.** The handoffs and their records are not public. Without them you can run the tool only on files of your own, as above.
- **The redaction is checked by Sencor, not by you.** Before publication, this copy was derived from the full program by named line ranges and run on Sencor's machine against every loaded record whose bytes were at hand (362). All of them gave the same statements back, field for field. You cannot check this from here, because the full program is not public.
- **The record's route is the machine that wrote it.** The connector that serves a record is answered by the same machine that wrote it. A replay checks a record against the bytes and a program. It does not show that the record was not rewritten on that machine afterwards.
- **The extractor can miss things.** A replay shows that the program and the record agree, not that the record holds everything the document says.
