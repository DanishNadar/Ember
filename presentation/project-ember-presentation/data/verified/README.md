# Verified snapshot

`presentationSnapshot.json` is the deck's only source of results. Produce it with:

    EMBER_REPO=/path/to/ember npm run ingest

Rules: every non-null section has `source.path` (+ `sha256`); missing values are `null`, never `0`;
`workflow.playback` is always `"recorded"`. Invalid sections are dropped and listed in Explore → Data & evidence.
Hand edits are allowed. Cite the artifact in `source.path`.
