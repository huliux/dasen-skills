# Reuse relevant Wiki evidence

Resolve the brief's frozen content root with dasen-content/scripts/content_paths.py. The bound knowledge location is `<content-root>/wiki/`; do not search ancestor or unrelated project Wikis. Read schema/index when present, select relevant entries, then read their pages and original source locators. An index miss or absent Wiki is an ordinary fallback to supplied material/online research, never a reason to initialize a Wiki or block writing. A broken reference is reported as a gap, not reconstructed from memory.

The article's Research Gate records `hit`, `partial`, `miss` or `absent`, selected page paths and adopted source IDs. Research reads leave all Wiki files unchanged, including logs and sidecar state. Explicit knowledge queries retain their own logging rules. This is a file-based agent workflow, not an automatic search service or embedding index.

## Transfer into sources.md

For evidence adopted from a Wiki summary, retain:

- `wiki_path`: content-root-relative summary path.
- `raw_path`: original local material path when available.
- `origin`: original HTTP(S) URL or content-root-relative source locator.
- `origin_type`: original type, also used as the source's `type`.
- `checked_at`: the actual source verification time. Reading a summary today is not a fresh factual verification; record reading/rechecking separately when needed.
- `supports`: claims actually supported, plus uncertainty and contradictions in the body.

Use `purpose: fact` for factual evidence and `purpose: structure` for structural inspiration. A summary, translation, mirror or retelling of one origin does not increase the count of independent factual origins. Declare the same origin on derived copies; preflight deduplicates declared origins and excludes structural references. A claim-level independence judgment still requires human/agent analysis; the checker cannot discover undeclared common origins.

Freshness depends on the claim. Recheck current capabilities, prices, versions and similar changing facts at the original source. Retain stable older evidence with its real date and limits. Never silently update source check times.

## Candidate ingestion

Keep newly researched evidence in the article first. At delivery, list only materials with specific reuse value in sources.md, with source IDs and a brief reason. The user can confirm the whole batch once; an existing authorization must identify its source scope. Persistent raw/pages and reflect are separate knowledge operations. Neither an empty candidate list nor a query miss requires another question. Operational scans, install inventories and backups are not content knowledge.
