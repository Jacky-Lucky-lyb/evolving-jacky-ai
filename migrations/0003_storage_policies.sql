-- Evolving Self AI: Storage policies, migration 0003
-- Target: existing private bucket knowledge-sources.
-- Run in Supabase SQL Editor with project administrator privileges.
-- Each object path begins with authenticated user's UUID.
BEGIN;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM storage.buckets
    WHERE id = 'knowledge-sources' AND public = false
  ) THEN
    RAISE EXCEPTION 'Bucket knowledge-sources is missing or not private';
  END IF;
END $$;

-- Only replace policies owned by this migration. Do not change other buckets.
DROP POLICY IF EXISTS "esa_sources_select_own" ON storage.objects;
DROP POLICY IF EXISTS "esa_sources_insert_own" ON storage.objects;
DROP POLICY IF EXISTS "esa_sources_update_own" ON storage.objects;
DROP POLICY IF EXISTS "esa_sources_delete_own" ON storage.objects;

CREATE POLICY "esa_sources_select_own"
ON storage.objects FOR SELECT TO authenticated
USING (
  bucket_id = 'knowledge-sources'
  AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  AND owner_id = (SELECT auth.uid()::text)
);

CREATE POLICY "esa_sources_insert_own"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
  bucket_id = 'knowledge-sources'
  AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  AND owner_id = (SELECT auth.uid()::text)
);

CREATE POLICY "esa_sources_update_own"
ON storage.objects FOR UPDATE TO authenticated
USING (
  bucket_id = 'knowledge-sources'
  AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  AND owner_id = (SELECT auth.uid()::text)
)
WITH CHECK (
  bucket_id = 'knowledge-sources'
  AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  AND owner_id = (SELECT auth.uid()::text)
);

CREATE POLICY "esa_sources_delete_own"
ON storage.objects FOR DELETE TO authenticated
USING (
  bucket_id = 'knowledge-sources'
  AND (storage.foldername(name))[1] = (SELECT auth.uid()::text)
  AND owner_id = (SELECT auth.uid()::text)
);

COMMIT;
