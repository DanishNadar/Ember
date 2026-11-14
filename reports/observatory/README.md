# Reviewable Observatory snapshots

Run `python scripts/export_observatory.py` from the canonical Ember checkout.
Read [the development guide](../../DEVELOPMENT.md) for storage, review and explicit
publication commands. Generated version directories and ZIPs are ignored until a
specific manifest is approved for publication.

Each snapshot includes a rendered report, executed notebook, saved PNGs, actual
run metrics/histories, provenance and checksums. There are no model checkpoints or
raw training datasets in the publication bundle. Original unredacted notebooks
and experiment artifacts remain in local verified backups/storage.

After approval, the publisher returns immutable GitHub URLs. Give ChatGPT the
exact snapshot URL/ref, or upload the generated ZIP. This shares a saved snapshot,
not live access to local files or unsaved cells.
