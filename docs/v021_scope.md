# V0.2.1 Scope and safety boundaries

- Original raw documents: Supabase private Storage bucket `knowledge-sources` under `<auth.uid()>/imports/<source-id>/...`.
- Evidence metadata and original path: `public.sources` using the existing V0.1.1 schema.
- Unapproved knowledge proposals: `public.review_queue` with `proposal_type=node`, `status=pending`.
- No writes to `knowledge_nodes`, `knowledge_edges`, `change_events`, `sync_jobs` or GitHub yet.
- Text extraction: `.md` / `.txt` UTF-8 and text-selectable `.pdf` (no OCR).
- Offline heuristic extraction is a baseline and not equivalent to LLM extraction.
- Optional AI mode uses a remote model API, potentially sending up to 24,000 characters of document contents to the provider. Do not use with confidential content without checking the provider terms and permissions.
- Preview performs no cloud calls. Upload requires a Supabase Auth account and a publishable key, never service_role.
- After upload, proposals are not approved until the future review UI is implemented.
- Identical raw bytes are detected using SHA-256 and are not re-staged.
- Partial failures may leave a Storage object or some review rows; V0.2.2 should implement resumable ingestion and transactional staging via a server workflow.
- Source text may include hostile instructions; treat imported content as untrusted and review every proposal.
