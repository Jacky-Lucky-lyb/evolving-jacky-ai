-- Read-only permission + schema verification for migration 0006.
-- Every row should report passed=true. This does NOT establish end-to-end concurrency safety.
WITH checks(name, passed) AS (
  VALUES
   ('guard trigger installed', EXISTS (
      SELECT 1 FROM pg_trigger t JOIN pg_class c ON c.oid=t.tgrelid
       JOIN pg_namespace ns ON ns.oid=c.relnamespace
       WHERE ns.nspname='public' AND c.relname='review_queue'
         AND t.tgname='trg_guard_merge_proposal' AND NOT t.tgisinternal)),
   ('review node RPC exists', to_regprocedure('public.review_node_proposal(uuid,text,text,text,text,text,text)') IS NOT NULL),
   ('review edge RPC exists', to_regprocedure('public.review_edge_proposal(uuid,text,text,text)') IS NOT NULL),
   ('reject merge RPC exists', to_regprocedure('public.reject_merge_proposal(uuid)') IS NOT NULL),
   ('authenticated can approve node RPC', has_function_privilege('authenticated','public.review_node_proposal(uuid,text,text,text,text,text,text)','EXECUTE')),
   ('anonymous cannot approve node RPC', NOT has_function_privilege('anon','public.review_node_proposal(uuid,text,text,text,text,text,text)','EXECUTE')),
   ('authenticated can review edge RPC', has_function_privilege('authenticated','public.review_edge_proposal(uuid,text,text,text)','EXECUTE')),
   ('authenticated can reject merge RPC', has_function_privilege('authenticated','public.reject_merge_proposal(uuid)','EXECUTE')),
   ('authenticated cannot directly insert final node', NOT has_table_privilege('authenticated','public.knowledge_nodes','INSERT')),
   ('authenticated cannot directly modify review', NOT has_table_privilege('authenticated','public.review_queue','UPDATE')),
   ('authenticated cannot directly delete review', NOT has_table_privilege('authenticated','public.review_queue','DELETE'))
)
SELECT name, passed FROM checks ORDER BY name;
