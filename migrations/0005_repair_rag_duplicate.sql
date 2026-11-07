-- Evolving Self AI: one-time repair for the confirmed RAG duplicate.
-- PRECONDITIONS: run on the intended Supabase project via SQL Editor;
-- take a database backup first. Does NOT delete nodes, relationships or reviews.
-- This is a DATA REPAIR, NOT a general merge RPC or future-conflict guard.
BEGIN;

-- Prevent a relationship/evidence row being added to the duplicate during this repair.
LOCK TABLE public.knowledge_edges, public.knowledge_node_evidence IN SHARE ROW EXCLUSIVE MODE;

DO $repair$
DECLARE
  v_main_id CONSTANT text := 'KNW-20261107-546152007574';
  v_dup_id CONSTANT text := 'KNW-20261107-693745323057';
  v_source_id CONSTANT text := 'SRC-20261107-381487356634';
  v_review_id CONSTANT uuid := '58f5d116-3c32-497c-a275-4382463733b9';
  v_merge_id CONSTANT uuid := 'f6fdde09-18d5-4589-bdc2-e0f7c12b8b28';
  v_owner uuid;
  v_main public.knowledge_nodes%ROWTYPE;
  v_dup public.knowledge_nodes%ROWTYPE;
  v_candidate public.review_queue%ROWTYPE;
  v_merge public.review_queue%ROWTYPE;
  v_quote text;
  v_locator jsonb;
  v_evidence_id uuid;
BEGIN
  SELECT * INTO STRICT v_main FROM public.knowledge_nodes WHERE id=v_main_id FOR UPDATE;
  SELECT * INTO STRICT v_dup FROM public.knowledge_nodes WHERE id=v_dup_id FOR UPDATE;
  v_owner := v_main.owner_id;

  IF v_dup.owner_id IS DISTINCT FROM v_owner OR
     v_main.node_type <> 'CONCEPT' OR v_dup.node_type <> 'CONCEPT' OR
     v_main.knowledge_space <> 'external' OR v_dup.knowledge_space <> 'external' OR
     v_main.status <> 'external' OR v_dup.status <> 'external' OR
     v_main.title <> 'RAG' OR v_dup.title <> 'Retrieval-Augmented Generation (RAG)' THEN
    RAISE EXCEPTION 'Precondition failed: node identity, owner, title, type or state changed';
  END IF;
  IF EXISTS(SELECT 1 FROM public.knowledge_edges
     WHERE (from_node_id=v_dup_id OR to_node_id=v_dup_id)) THEN
    RAISE EXCEPTION 'Duplicate node now has edges: review manually';
  END IF;
  IF EXISTS(SELECT 1 FROM public.knowledge_node_evidence WHERE node_id=v_dup_id) THEN
    RAISE EXCEPTION 'Duplicate node now has evidence: review manually';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM public.sources WHERE id=v_source_id AND owner_id=v_owner) THEN
    RAISE EXCEPTION 'Source unavailable or belongs to a different user';
  END IF;

  SELECT * INTO STRICT v_candidate FROM public.review_queue
    WHERE id=v_review_id AND owner_id=v_owner FOR UPDATE;
  SELECT * INTO STRICT v_merge FROM public.review_queue
    WHERE id=v_merge_id AND owner_id=v_owner FOR UPDATE;
  IF v_candidate.proposal_type <> 'node' OR v_candidate.status <> 'approved' OR
     v_merge.proposal_type <> 'merge' OR v_merge.status <> 'pending' OR
     v_merge.payload->>'candidate_review_id' IS DISTINCT FROM v_review_id::text OR
     v_merge.payload->>'target_node_id' IS DISTINCT FROM v_main_id OR
     COALESCE(v_candidate.source_ref, v_candidate.payload->>'source_id') IS DISTINCT FROM v_source_id OR
     COALESCE(v_merge.source_ref, v_merge.payload->>'source_id') IS DISTINCT FROM v_source_id OR
     v_candidate.payload->>'title' IS DISTINCT FROM v_dup.title THEN
    RAISE EXCEPTION 'Precondition failed: review status, linkage, or source has changed';
  END IF;

  v_quote := btrim(COALESCE(v_candidate.payload->>'evidence_quote',''));
  IF length(v_quote) < 12 OR
     v_quote IS DISTINCT FROM btrim(COALESCE(v_merge.payload->>'evidence_quote','')) THEN
    RAISE EXCEPTION 'Evidence quote missing or disagrees between candidate and merge';
  END IF;
  v_locator := v_candidate.payload->'evidence_locator';
  IF jsonb_typeof(v_locator) IS DISTINCT FROM 'object' THEN
    v_locator := '{}'::jsonb;
  END IF;

  INSERT INTO public.knowledge_node_evidence
    (owner_id,node_id,source_id,evidence_quote,evidence_locator,claim_kind,originating_review_id)
  VALUES (v_owner,v_main_id,v_source_id,v_quote,v_locator,'source_claim',v_merge_id)
  RETURNING id INTO v_evidence_id;

  UPDATE public.knowledge_nodes
  SET status='obsolete',
      metadata = metadata || jsonb_build_object('merge',jsonb_build_object(
          'merged_into',v_main_id,
          'method','manual_verified_repair',
          'reason','RAG acronym/full-name duplicate created during review conflict',
          'merge_review_id',v_merge_id,
          'merged_at',now())),
      updated_at=now()
  WHERE id=v_dup_id AND owner_id=v_owner;

  UPDATE public.review_queue
  SET status='approved', reviewed_at=now(),
      payload=payload || jsonb_build_object('resolution','reconciled_after_duplicate_creation',
        'duplicate_node_id',v_dup_id,'evidence_id',v_evidence_id)
  WHERE id=v_merge_id AND owner_id=v_owner;

  INSERT INTO public.change_events(owner_id,event_type,entity_id,payload)
  VALUES(v_owner,'duplicate_node_reconciled',v_main_id,
       jsonb_build_object('duplicate_id',v_dup_id,'source_id',v_source_id,
                          'review_id',v_merge_id,'evidence_id',v_evidence_id,
                          'action','obsolete_and_redirect'));

  INSERT INTO public.sync_jobs(owner_id,operation,idempotency_key,payload)
  VALUES(v_owner,'export_node_evidence','repair-rag:'||v_merge_id::text,
         jsonb_build_object('node_id',v_main_id,'duplicate_id',v_dup_id,
                            'evidence_id',v_evidence_id,'source_id',v_source_id))
  ON CONFLICT (owner_id,idempotency_key) DO NOTHING;

  RAISE NOTICE 'RAG repair committed inside transaction: owner %, evidence %, duplicate %', v_owner, v_evidence_id, v_dup_id;
EXCEPTION
  WHEN NO_DATA_FOUND THEN
    RAISE EXCEPTION 'Required node or review not found; nothing modified';
END;
$repair$;
COMMIT;
