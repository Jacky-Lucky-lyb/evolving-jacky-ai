# Evolving Self AI — V0.2.3 semantic extraction (incremental package)

## What changes

New files only: `scripts/semantic_extraction.py`, `scripts/ingest_semantic.py`, `tests/test_semantic_extraction.py`. **Do not replace** the existing `scripts/ingest_knowledge.py`, Streamlit review center, database schema, or earlier tests.

This add-on calls the OpenAI Responses API only when explicitly invoked with a local `OPENAI_API_KEY`. It uses structured JSON outputs and filters candidate quotes to require an **exact** match within the submitted document chunk. It rejects generic section headings, attaches character offsets and section names, deduplicates candidate titles, and sets `knowledge_space=external`, `knowledge_status=unverified` for **every** extracted candidate. Output still requires human review.

## Install and run

From repo root:

```bash
python3 -m pip install openai
python3 -m unittest discover -s tests -p 'test_semantic_extraction.py' -v
```

For AI mode, set the key in your shell, not in your Git repository. Example prompts in the commands below will read the existing non-private sample. Avoid supplying personal data to a model API without reviewing its data processing policies.

```bash
export OPENAI_API_KEY='YOUR_API_KEY' # LOCAL SHELL ONLY, never commit
python3 scripts/ingest_semantic.py --file examples/sample_learning.md --mode preview
```

Only after checking preview and confirming the right Supabase project:

```bash
export SUPABASE_URL='https://YOUR_PROJECT.supabase.co'
export SUPABASE_PUBLISHABLE_KEY='YOUR_PUBLISHABLE_KEY'
python3 scripts/ingest_semantic.py --file examples/sample_learning.md --mode upload
```

Do not use secret or service-role keys for uploads. The CLI reuses V0.2.1's Supabase Auth login, Storage upload, `sources` and `review_queue` writes; nothing directly enters `knowledge_nodes` or `knowledge_edges`.

**IMPORTANT:** V0.2.1 uses source SHA-256 deduplication. If you already uploaded the same `examples/sample_learning.md`, running `--mode upload` again will report an existing source and will **not** add fresh proposals. For integration testing, make a new copy and add a harmless paragraph so the file bytes differ, or use a fresh original text document.

## Current limits

- Maximum 8 MB source file (inherited from V0.2.1) and maximum **6 chunks × 6500 characters** for AI extraction (configurable). Anything longer is refused, rather than silently truncating.
- PDF extraction only handles text-based PDFs (`pypdf` optional). Scanned PDFs not supported.
- Evidence offsets are for **extracted text**, not PDF page/coordinates. PDF source-page mapping is a future improvement.
- A model might return **zero** accepted candidates even when text has meaningful knowledge. Exact-quote grounding is intentionally strict.
- Fuzzy duplicate matching and relationship inference remain separate V0.2.4 scope.
- API may charge for tokens; check cost and data policy before invoking.
- Existing review UI only displays evidence quote and title. Offsets remain in the proposal payload until a node-detail UI surfaces them.
- No server-side workflow, Git sync, transaction coordination, or independently audited security is included.

## Architecture

`Source (.md/.txt/text-PDF)` → `AI candidate extraction` → `exact-evidence validator` → `preview` → `optional staged upload` → `review_queue` → `existing human approval UI`.

The model is **not** evidence of the user's opinion or competence. Approved external-source concept nodes remain external knowledge.
