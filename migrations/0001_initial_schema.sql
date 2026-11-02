-- Evolving Self AI / V0.1.1: initial cloud schema
-- Execute once in Supabase SQL Editor, as the project database administrator.
-- No personal data is inserted by this migration.
begin;

create table if not exists public.knowledge_nodes (
  id text primary key check (id ~ '^[A-Z]{3}-[0-9]{8}-[0-9]{3,}$'),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  node_type text not null check (node_type in ('PERSON','GOAL','CONCEPT','SKILL','PROJECT','EXPERIENCE','BELIEF','DECISION','SOURCE')),
  title text not null check (length(trim(title)) > 0),
  status text not null default 'observed' check (status in ('observed','verified','external','hypothesized','disputed','obsolete')),
  knowledge_space text not null default 'current' check (knowledge_space in ('current','external','hypothetical')),
  privacy text not null default 'private' check (privacy in ('private','sensitive','shareable','public')),
  markdown_path text,
  metadata jsonb not null default '{}'::jsonb check (jsonb_typeof(metadata) = 'object'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, id)
);

create table if not exists public.sources (
  id text primary key check (id ~ '^SRC-[0-9]{8}-[0-9]{3,}$'),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  title text not null,
  source_type text not null default 'document',
  bucket_id text,
  object_path text,
  original_uri text,
  sha256 text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (owner_id, id),
  check ((bucket_id is null) = (object_path is null))
);

create table if not exists public.knowledge_edges (
  id text primary key check (id ~ '^REL-[0-9]{8}-[0-9]{3,}$'),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  from_node_id text not null,
  relation_type text not null check (relation_type in ('HAS_GOAL','KNOWS','HAS_SKILL','REQUIRES','PREREQUISITE_OF','APPLIES','PART_OF','DERIVED_FROM','SUPPORTS','CONTRADICTS','MOTIVATED_BY','REVISED_BY')),
  to_node_id text not null,
  evidence_source_id text,
  evidence_locator text,
  review_status text not null default 'pending' check (review_status in ('pending','approved','rejected')),
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (owner_id, from_node_id) references public.knowledge_nodes(owner_id, id) on delete cascade,
  foreign key (owner_id, to_node_id) references public.knowledge_nodes(owner_id, id) on delete cascade,
  foreign key (owner_id, evidence_source_id) references public.sources(owner_id, id),
  check (from_node_id <> to_node_id),
  unique (owner_id,id)
);

create table if not exists public.review_queue (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  proposal_type text not null check (proposal_type in ('node','edge','merge','change')),
  payload jsonb not null check (jsonb_typeof(payload) = 'object'),
  status text not null default 'pending' check (status in ('pending','approved','rejected','needs_revision')),
  source_ref text,
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

create table if not exists public.change_events (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  event_type text not null,
  entity_id text,
  payload jsonb not null default '{}'::jsonb,
  git_commit_sha text,
  created_at timestamptz not null default now()
);

create table if not exists public.sync_jobs (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade default auth.uid(),
  operation text not null,
  status text not null default 'queued' check (status in ('queued','running','succeeded','failed')),
  idempotency_key text not null,
  payload jsonb not null default '{}'::jsonb,
  attempts integer not null default 0 check (attempts >= 0),
  last_error text,
  git_commit_sha text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (owner_id, idempotency_key)
);

create index if not exists idx_nodes_owner_type on public.knowledge_nodes (owner_id,node_type);
create index if not exists idx_edges_from on public.knowledge_edges (owner_id,from_node_id);
create index if not exists idx_edges_to on public.knowledge_edges (owner_id,to_node_id);
create index if not exists idx_review_owner_status on public.review_queue (owner_id,status);
create index if not exists idx_sync_owner_status on public.sync_jobs (owner_id,status);

-- Keep the new tables protected even if project-level auto-RLS was disabled.
alter table public.knowledge_nodes enable row level security;
alter table public.knowledge_edges enable row level security;
alter table public.sources enable row level security;
alter table public.review_queue enable row level security;
alter table public.change_events enable row level security;
alter table public.sync_jobs enable row level security;

-- Explicitly grant authenticated access only; RLS determines row-level permissions.
revoke all on public.knowledge_nodes, public.knowledge_edges, public.sources, public.review_queue, public.change_events, public.sync_jobs from anon;
grant select, insert, update, delete on public.knowledge_nodes, public.knowledge_edges, public.sources, public.review_queue, public.sync_jobs to authenticated;
grant select, insert on public.change_events to authenticated;

-- Owner-only policies; authentication must be configured before client use.
create policy "owner_access_nodes" on public.knowledge_nodes for all to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "owner_access_edges" on public.knowledge_edges for all to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "owner_access_sources" on public.sources for all to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "owner_access_reviews" on public.review_queue for all to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));
create policy "owner_select_events" on public.change_events for select to authenticated using (owner_id = (select auth.uid()));
create policy "owner_insert_events" on public.change_events for insert to authenticated with check (owner_id = (select auth.uid()));
create policy "owner_access_sync" on public.sync_jobs for all to authenticated using (owner_id = (select auth.uid())) with check (owner_id = (select auth.uid()));

commit;
