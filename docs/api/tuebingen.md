# Tübingen pilot snapshot

Verified 14 November 2026 against the official source.

- Index: https://webdav.tuebingen.mpg.de/cause-effect/
- Archive: https://webdav.tuebingen.mpg.de/cause-effect/pairs.zip
- Metadata: https://webdav.tuebingen.mpg.de/cause-effect/pairmeta.txt
- Overview: https://webdav.tuebingen.mpg.de/cause-effect/README
- Per-pair files: `pairNNNN.txt`, `pairNNNN_des.txt`.

Metadata has six whitespace-separated fields: pair number, first/last cause column,
first/last effect column, weight. Columns are one-based and can be reversed or
multidimensional. Numeric files are whitespace-separated rows, not CSV files.
Descriptions contain reference-direction text and must never enter prompts.
The archive contains 108 pairs, metadata and descriptions; save the separately
downloaded overview too. Record exact bytes/hashes rather than asserting a release
date from the current URL. The official source warns reference labels can be wrong.

Only positive-weight scalar pairs are candidates for this pilot. Source grouping,
sanitized names and measurement caveats require description review; weights alone
do not define independent source families. Keep all related UNdata pairs out of
future held-out data once any UNdata pair has been used in the pilot.

Raw files and prepared outputs stay in ignored `runs/pilot-preparation/`. A checked-in
manifest pins the source hashes, reviewed labels/groups and bounded pilot selection.
No gold, raw description, original pair ID, group or weight enters RuntimePair.
