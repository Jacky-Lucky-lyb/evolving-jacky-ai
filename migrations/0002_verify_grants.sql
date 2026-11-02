-- Expected: no rows returned.
-- Verify actual effective privileges, including inherited/PUBLIC privileges.
WITH tables AS (
 SELECT unnest(ARRAY[
  'knowledge_nodes','knowledge_edges','sources',
  'review_queue','change_events','sync_jobs'
 ]) AS table_name
), operations AS (
 SELECT unnest(ARRAY[
  'SELECT','INSERT','UPDATE','DELETE','TRUNCATE','REFERENCES','TRIGGER'
 ]) AS privilege
), roles AS (
 SELECT unnest(ARRAY['anon','authenticated']) AS role_name
)
SELECT t.table_name, r.role_name, o.privilege
FROM tables t CROSS JOIN roles r CROSS JOIN operations o
WHERE has_table_privilege(r.role_name, 'public.'||quote_ident(t.table_name), o.privilege)
  AND (
    r.role_name = 'anon'
    OR o.privilege IN ('TRUNCATE','REFERENCES','TRIGGER')
    OR (t.table_name='change_events' AND o.privilege IN ('UPDATE','DELETE'))
  )
ORDER BY t.table_name, r.role_name, o.privilege;
