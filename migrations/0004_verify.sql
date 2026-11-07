-- Read only: structural verification after migration 0004.
SELECT 'evidence table exists' AS check_name,
       to_regclass('public.knowledge_node_evidence') IS NOT NULL AS passed
UNION ALL
SELECT 'evidence RLS on', COALESCE((SELECT relrowsecurity FROM pg_class WHERE oid='public.knowledge_node_evidence'::regclass),FALSE)
UNION ALL
SELECT 'authenticated read evidence', has_table_privilege('authenticated','public.knowledge_node_evidence','SELECT')
UNION ALL
SELECT 'authenticated cannot insert evidence', NOT has_table_privilege('authenticated','public.knowledge_node_evidence','INSERT')
UNION ALL
SELECT 'anonymous cannot read evidence', NOT has_table_privilege('anon','public.knowledge_node_evidence','SELECT')
UNION ALL
SELECT 'authenticated can call RPC', has_function_privilege('authenticated','public.approve_node_reuse(uuid)','EXECUTE')
UNION ALL
SELECT 'anonymous cannot call RPC', NOT has_function_privilege('anon','public.approve_node_reuse(uuid)','EXECUTE');
