-- Read-only verification after running 0001_initial_schema.sql
select tablename, rowsecurity as rls_enabled
from pg_tables
where schemaname = 'public'
  and tablename in ('knowledge_nodes','knowledge_edges','sources','review_queue','change_events','sync_jobs')
order by tablename;
