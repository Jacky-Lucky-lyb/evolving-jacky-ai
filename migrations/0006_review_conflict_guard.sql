-- Evolving Self AI / Migration 0006
-- Prevent the same source candidate being approved as a NEW node while a merge review is pending.
-- Requires 0001..0005. Review/backup first. Run once in the correct Supabase project.
BEGIN;

-- 1) Serialize creation of merge proposals against candidate review approval.
CREATE OR REPLACE FUNCTION public.guard_merge_proposal()
RETURNS trigger LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_candidate public.review_queue%ROWTYPE;
  v_target public.knowledge_nodes%ROWTYPE;
  v_candidate_id uuid;
BEGIN
  -- Only validate new pending merges. Existing resolved history remains unchanged.
  IF NEW.proposal_type <> 'merge' OR NEW.status <> 'pending' THEN RETURN NEW; END IF;
  IF NEW.payload->>'candidate_review_id' IS NULL OR
     (NEW.payload->>'candidate_review_id') !~* '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$' THEN
    RAISE EXCEPTION 'merge proposal requires valid candidate_review_id' USING ERRCODE='P0001';
  END IF;
  v_candidate_id := (NEW.payload->>'candidate_review_id')::uuid;
  -- Acquiring the candidate row lock is also what makes concurrent approvals serialize.
  SELECT * INTO v_candidate FROM public.review_queue
   WHERE id = v_candidate_id AND owner_id = NEW.owner_id FOR UPDATE;
  IF NOT FOUND OR v_candidate.proposal_type <> 'node' OR v_candidate.status <> 'pending' THEN
    RAISE EXCEPTION 'Original node proposal unavailable or already resolved' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO v_target FROM public.knowledge_nodes
   WHERE id = NEW.payload->>'target_node_id' AND owner_id=NEW.owner_id;
  IF NOT FOUND OR v_target.status = 'obsolete' OR v_target.node_type <> (v_candidate.payload->>'node_type') OR
    v_target.knowledge_space <> 'external' OR
    coalesce(v_candidate.payload->>'knowledge_space','external') <> 'external' THEN
    RAISE EXCEPTION 'Merge target not eligible' USING ERRCODE='P0001';
  END IF;
  IF coalesce(NEW.source_ref,NEW.payload->>'source_id') IS DISTINCT FROM
     coalesce(v_candidate.source_ref,v_candidate.payload->>'source_id') THEN
    RAISE EXCEPTION 'Merge candidate source mismatch' USING ERRCODE='P0001';
  END IF;
  IF EXISTS (SELECT 1 FROM public.review_queue q
      WHERE q.owner_id=NEW.owner_id AND q.proposal_type='merge' AND q.status='pending'
        AND q.id <> NEW.id AND q.payload->>'candidate_review_id'=v_candidate_id::text) THEN
    RAISE EXCEPTION 'Candidate already has pending merge review' USING ERRCODE='P0001';
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_guard_merge_proposal ON public.review_queue;
CREATE TRIGGER trg_guard_merge_proposal
BEFORE INSERT OR UPDATE OF payload, proposal_type, status ON public.review_queue
FOR EACH ROW EXECUTE FUNCTION public.guard_merge_proposal();

-- 2) Replace the unsafe client workflow (node INSERT -> review UPDATE) with an atomic RPC.
CREATE OR REPLACE FUNCTION public.review_node_proposal(
    p_review_id uuid, p_action text,
    p_node_type text DEFAULT NULL, p_title text DEFAULT NULL,
    p_space text DEFAULT NULL, p_status text DEFAULT NULL, p_note text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_user uuid := auth.uid();
  v_review public.review_queue%ROWTYPE;
  v_id text;
  v_type text;
  v_title text;
  v_space text;
  v_status text;
  v_source text;
  v_quote text;
  v_result_status text;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING ERRCODE='P0001'; END IF;
  IF p_action IS NULL OR p_action NOT IN ('approve','reject','needs_revision') THEN
    RAISE EXCEPTION 'Unsupported review action' USING ERRCODE='P0001';
  END IF;
  SELECT * INTO v_review FROM public.review_queue
     WHERE id=p_review_id AND owner_id=v_user FOR UPDATE;
  IF NOT FOUND OR v_review.proposal_type <> 'node' THEN
    RAISE EXCEPTION 'Node proposal not found' USING ERRCODE='P0001';
  END IF;
  IF v_review.status <> 'pending' THEN
    RAISE EXCEPTION 'Node proposal already resolved' USING ERRCODE='P0001';
  END IF;
  -- A pending merge must first be resolved (approved/rejected) through its own entry point.
  IF EXISTS (SELECT 1 FROM public.review_queue m
    WHERE m.owner_id=v_user AND m.proposal_type='merge' AND m.status='pending'
    AND m.payload->>'candidate_review_id'=p_review_id::text) THEN
    RAISE EXCEPTION 'Pending reuse proposal: resolve merge review before node review' USING ERRCODE='P0001';
  END IF;
  IF p_action='approve' THEN
    v_type := coalesce(p_node_type,v_review.payload->>'node_type');
    v_title := btrim(coalesce(p_title,v_review.payload->>'title',''));
    v_space := coalesce(p_space,'external');
    v_status := coalesce(p_status,'external');
    IF v_type NOT IN ('PERSON','GOAL','CONCEPT','SKILL','PROJECT','EXPERIENCE','BELIEF','DECISION','SOURCE') OR
       length(v_title) NOT BETWEEN 1 AND 200 OR
       v_space NOT IN ('current','external','hypothetical') OR
       v_status NOT IN ('observed','verified','external','hypothesized','disputed','obsolete') OR
       (v_space='external' AND v_status <> 'external') OR
       (v_space='hypothetical' AND v_status <> 'hypothesized') OR
       (v_space='current' AND v_status IN ('external','hypothesized','obsolete')) THEN
      RAISE EXCEPTION 'Invalid node type / title / knowledge space / status' USING ERRCODE='P0001';
    END IF;
    -- Fail closed for personal assertions: promotion to personal space requires a future reviewed workflow.
    IF v_space <> 'external' THEN
      RAISE EXCEPTION 'V0006 imports only external knowledge; personal claims need dedicated verification' USING ERRCODE='P0001';
    END IF;
    v_source := coalesce(v_review.source_ref,v_review.payload->>'source_id');
    IF v_source IS NOT NULL AND NOT EXISTS
      (SELECT 1 FROM public.sources WHERE owner_id=v_user AND id=v_source) THEN
      RAISE EXCEPTION 'Source not owned or unavailable' USING ERRCODE='P0001';
    END IF;
    v_quote := coalesce(v_review.payload->>'evidence_quote','');
    -- Defensive duplicate check, not semantic alignment. Application review still required.
    IF EXISTS (SELECT 1 FROM public.knowledge_nodes n
       WHERE n.owner_id=v_user AND n.status <> 'obsolete' AND n.node_type=v_type
         AND n.knowledge_space=v_space AND lower(btrim(n.title))=lower(v_title)) THEN
       RAISE EXCEPTION 'Exact active node title already exists; review reuse first' USING ERRCODE='P0001';
    END IF;
    v_id := 'KNW-'||to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYYMMDD')||'-'||lpad((floor(random()*1000000000000)::bigint)::text,12,'0');
    INSERT INTO public.knowledge_nodes
      (id,owner_id,node_type,title,status,knowledge_space,privacy,metadata)
    VALUES (v_id,v_user,v_type,v_title,v_status,v_space,'private',
      jsonb_build_object('review_origin','review_node_proposal_v0006','review_id',p_review_id,
       'source_id',v_source,'evidence_quote',left(v_quote,1200),'review_note',left(coalesce(p_note,''),1200)));
    v_result_status := 'approved';
  ELSE
    v_result_status := CASE WHEN p_action='reject' THEN 'rejected' ELSE 'needs_revision' END;
  END IF;
  UPDATE public.review_queue SET status=v_result_status,reviewed_at=now()
    WHERE id=p_review_id AND owner_id=v_user;
  INSERT INTO public.change_events(owner_id,event_type,entity_id,payload)
    VALUES(v_user,'review_node_'||v_result_status,coalesce(v_id,p_review_id::text),
      jsonb_build_object('proposal_id',p_review_id,'node_id',v_id,'action',p_action,
        'title',coalesce(v_title,v_review.payload->>'title'),'note',coalesce(p_note,'')));
  IF v_id IS NOT NULL THEN
    INSERT INTO public.sync_jobs(owner_id,operation,idempotency_key,payload)
      VALUES(v_user,'export_node','review-node:'||p_review_id::text,
        jsonb_build_object('node_id',v_id,'review_id',p_review_id))
      ON CONFLICT (owner_id,idempotency_key) DO NOTHING;
  END IF;
  RETURN jsonb_build_object('status',v_result_status,'node_id',v_id,'review_id',p_review_id);
END;
$$;

-- 3) Dedicated rejection path for merge proposals, after which ordinary node review may resume.
CREATE OR REPLACE FUNCTION public.reject_merge_proposal(p_merge_id uuid)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_user uuid := auth.uid();
  v_merge public.review_queue%ROWTYPE;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING ERRCODE='P0001'; END IF;
  SELECT * INTO v_merge FROM public.review_queue
    WHERE id=p_merge_id AND owner_id=v_user FOR UPDATE;
  IF NOT FOUND OR v_merge.proposal_type <> 'merge' OR v_merge.status <> 'pending' THEN
    RAISE EXCEPTION 'Pending merge not found' USING ERRCODE='P0001';
  END IF;
  UPDATE public.review_queue SET status='rejected',reviewed_at=now()
    WHERE id=p_merge_id AND owner_id=v_user;
  INSERT INTO public.change_events(owner_id,event_type,entity_id,payload)
    VALUES(v_user,'review_merge_rejected',p_merge_id::text,
        jsonb_build_object('proposal_id',p_merge_id,'candidate_review_id',v_merge.payload->>'candidate_review_id'));
  RETURN jsonb_build_object('status','rejected','review_id',p_merge_id);
END;
$$;

-- 4) Existing relation-review UI must also stop using direct review_queue UPDATE.
CREATE OR REPLACE FUNCTION public.review_edge_proposal(
  p_review_id uuid, p_action text, p_relation_type text DEFAULT NULL, p_note text DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE
  v_user uuid := auth.uid();
  v_review public.review_queue%ROWTYPE;
  v_from text;
  v_to text;
  v_relation text;
  v_id text;
  v_source text;
  v_status text;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required' USING ERRCODE='P0001'; END IF;
  IF p_action IS NULL OR p_action NOT IN ('approve','reject') THEN RAISE EXCEPTION 'Invalid edge action' USING ERRCODE='P0001'; END IF;
  SELECT * INTO v_review FROM public.review_queue
    WHERE id=p_review_id AND owner_id=v_user FOR UPDATE;
  IF NOT FOUND OR v_review.proposal_type <> 'edge' OR v_review.status <> 'pending' THEN
    RAISE EXCEPTION 'Pending edge proposal not found' USING ERRCODE='P0001';
  END IF;
  IF p_action='approve' THEN
    v_from := v_review.payload->>'from_node_id';
    v_to := v_review.payload->>'to_node_id';
    v_relation := coalesce(p_relation_type,v_review.payload->>'relation_type');
    IF v_relation NOT IN ('HAS_GOAL','KNOWS','HAS_SKILL','REQUIRES','PREREQUISITE_OF','APPLIES','PART_OF','DERIVED_FROM','SUPPORTS','CONTRADICTS','MOTIVATED_BY','REVISED_BY') OR
      v_from IS NULL OR v_to IS NULL OR v_from=v_to OR length(btrim(coalesce(p_note,'')))=0 THEN
      RAISE EXCEPTION 'Invalid edge input' USING ERRCODE='P0001';
    END IF;
    IF (SELECT count(*) FROM public.knowledge_nodes
       WHERE owner_id=v_user AND status <> 'obsolete' AND id IN (v_from,v_to)) <> 2 THEN
      RAISE EXCEPTION 'Edge endpoints missing or obsolete' USING ERRCODE='P0001';
    END IF;
    IF EXISTS (SELECT 1 FROM public.knowledge_edges
        WHERE owner_id=v_user AND from_node_id=v_from AND to_node_id=v_to
        AND relation_type=v_relation AND review_status='approved') THEN
      RAISE EXCEPTION 'Exact relationship already approved' USING ERRCODE='P0001';
    END IF;
    v_source := coalesce(v_review.source_ref,v_review.payload->>'source_id');
    IF v_source IS NOT NULL AND NOT EXISTS (SELECT 1 FROM public.sources
        WHERE owner_id=v_user AND id=v_source) THEN
      RAISE EXCEPTION 'Source not found' USING ERRCODE='P0001';
    END IF;
    v_id := 'REL-'||to_char(clock_timestamp() AT TIME ZONE 'UTC','YYYYMMDD')||'-'||lpad((floor(random()*1000000000000)::bigint)::text,12,'0');
    INSERT INTO public.knowledge_edges
      (id,owner_id,from_node_id,to_node_id,relation_type,evidence_source_id,evidence_locator,review_status,metadata)
    VALUES (v_id,v_user,v_from,v_to,v_relation,v_source,left(p_note,500),'approved',
      jsonb_build_object('review_origin','review_edge_proposal_v0006','review_id',p_review_id));
    v_status := 'approved';
  ELSE v_status := 'rejected'; END IF;
  UPDATE public.review_queue SET status=v_status,reviewed_at=now()
    WHERE id=p_review_id AND owner_id=v_user;
  INSERT INTO public.change_events(owner_id,event_type,entity_id,payload)
    VALUES (v_user,'review_edge_'||v_status,coalesce(v_id,p_review_id::text),
      jsonb_build_object('proposal_id',p_review_id,'edge_id',v_id));
  IF v_id IS NOT NULL THEN
    INSERT INTO public.sync_jobs(owner_id,operation,idempotency_key,payload)
     VALUES (v_user,'export_edge','review-edge:'||p_review_id::text,jsonb_build_object('edge_id',v_id))
     ON CONFLICT (owner_id,idempotency_key) DO NOTHING;
  END IF;
  RETURN jsonb_build_object('status',v_status,'edge_id',v_id,'review_id',p_review_id);
END;
$$;

-- Privilege boundary: no direct API creation of final nodes, no direct review status changes.
REVOKE INSERT ON public.knowledge_nodes FROM PUBLIC, anon, authenticated;
REVOKE UPDATE, DELETE ON public.review_queue FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.guard_merge_proposal() FROM PUBLIC, anon, authenticated;
REVOKE ALL ON FUNCTION public.review_edge_proposal(uuid,text,text,text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.review_edge_proposal(uuid,text,text,text) TO authenticated;
REVOKE ALL ON FUNCTION public.review_node_proposal(uuid,text,text,text,text,text,text) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.review_node_proposal(uuid,text,text,text,text,text,text) TO authenticated;
REVOKE ALL ON FUNCTION public.reject_merge_proposal(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.reject_merge_proposal(uuid) TO authenticated;

-- WARNING: Admin/service-role/API paths still require separate controls; direct inserts by privileged code remain possible.
COMMIT;
