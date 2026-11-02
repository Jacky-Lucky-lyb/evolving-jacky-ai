-- Read-only inspection. Expect one private bucket and four policies.
SELECT id, name, public, file_size_limit
FROM storage.buckets WHERE id = 'knowledge-sources';

SELECT policyname, cmd, roles, qual, with_check
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
  AND policyname LIKE 'esa_sources_%'
ORDER BY policyname;

-- Important: review all policies, not only ESA policies; permissive policies
-- are OR-combined and other policies might broaden access.
SELECT policyname, cmd, roles, qual, with_check
FROM pg_policies
WHERE schemaname = 'storage' AND tablename = 'objects'
ORDER BY policyname;
