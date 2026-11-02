-- Evolving Self AI v0.1.2: minimal grants for private knowledge tables.
-- Run from the Supabase SQL Editor with database owner permissions.
-- No table, data, or RLS policy is dropped.
BEGIN;

REVOKE ALL PRIVILEGES ON TABLE
  public.knowledge_nodes,
  public.knowledge_edges,
  public.sources,
  public.review_queue,
  public.change_events,
  public.sync_jobs
FROM PUBLIC, anon, authenticated;

GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
  public.knowledge_nodes,
  public.knowledge_edges,
  public.sources,
  public.review_queue,
  public.sync_jobs
TO authenticated;

-- Temporary app-side insert for early development; harden audit writes later.
GRANT SELECT, INSERT ON TABLE public.change_events TO authenticated;

COMMIT;
