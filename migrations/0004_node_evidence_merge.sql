-- Evolving Self AI v0.2.5: durable source evidence and atomic approval of reuse proposals.
-- Run once after 0001 and 0002. Review carefully in SQL Editor.
BEGIN;

CREATE UNIQUE INDEX IF NOT EXISTS uq_review_owner_id ON public.review_queue(owner_id,id);

CREATE TABLE IF NOT EXISTS public.knowledge_node_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  owner_id uuid NOT NULL DEFAULT auth.uid() REFERENCES auth.users(id) ON DELETE CASCADE,
  node_id text NOT NULL,
  source_id text NOT NULL,
  evidence_quote text NOT NULL CHECK (length(btrim(evidence_quote)) >= 12),
  evidence_locator jsonb NOT NULL DEFAULT '{}'::jsonb CHECK (jsonb_typeof(evidence_locator) = 'object'),
  claim_kind text NOT NULL DEFAULT 'source_claim' CHECK (claim_kind IN ('source_claim','personal_observation')),
  originating_review_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (owner_id, node_id) REFERENCES public.knowledge_nodes(owner_id,id) ON DELETE CASCADE,
  FOREIGN KEY (owner_id, source_id) REFERENCES public.sources(owner_id,id),
  FOREIGN KEY (owner_id, originating_review_id) REFERENCES public.review_queue(owner_id,id),
  UNIQUE (owner_id, originating_review_id)
);
-- Composite FK references the unique index declared above.
CREATE INDEX IF NOT EXISTS idx_evidence_owner_node ON public.knowledge_node_evidence(owner_id,node_id);
CREATE INDEX IF NOT EXISTS idx_evidence_owner_source ON public.knowledge_node_evidence(owner_id,source_id);
ALTER TABLE public.knowledge_node_evidence ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON public.knowledge_node_evidence FROM PUBLIC, anon, authenticated;
GRANT SELECT ON public.knowledge_node_evidence TO authenticated;
DROP POLICY IF EXISTS evidence_read_own ON public.knowledge_node_evidence;
CREATE POLICY evidence_read_own ON public.knowledge_node_evidence
  FOR SELECT TO authenticated USING (owner_id = (SELECT auth.uid()));

-- Entire function is one database transaction. SECURITY DEFINER uses explicit owner checks for every record; table writes are denied directly.
CREATE OR REPLACE FUNCTION public.approve_node_reuse(p_merge_id uuid)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = ''
AS $$
DECLARE
  v_user uuid := auth.uid();
  v_merge public.review_queue%ROWTYPE;
  v_candidate public.review_queue%ROWTYPE;
  v_target public.knowledge_nodes%ROWTYPE;
  v_source text;
  v_quote text;
  v_locator jsonb;
  v_evidence_id uuid;
BEGIN
  IF v_user IS NULL THEN RAISE EXCEPTION 'Authentication required'; END IF;
  SELECT * INTO v_merge FROM public.review_queue
   WHERE id = p_merge_id AND owner_id = v_user FOR UPDATE;
  IF NOT FOUND OR v_merge.proposal_type <> 'merge' THEN
    RAISE EXCEPTION 'Merge proposal not found';
  END IF;
  IF v_merge.status = 'approved' THEN
    SELECT id INTO v_evidence_id FROM public.knowledge_node_evidence
     WHERE owner_id = v_user AND originating_review_id = p_merge_id;
    IF v_evidence_id IS NULL THEN RAISE EXCEPTION 'Inconsistent approved merge; manual repair required'; END IF;
    RETURN jsonb_build_object('status','already_approved','evidence_id',v_evidence_id,'node_id',v_merge.payload->>'target_node_id');
  END IF;
  IF v_merge.status <> 'pending' THEN RAISE EXCEPTION 'Proposal not pending'; END IF;
  IF (v_merge.payload->>'candidate_review_id') IS NULL THEN
    RAISE EXCEPTION 'Missing original candidate';
  END IF;
  SELECT * INTO v_candidate FROM public.review_queue
   WHERE id = (v_merge.payload->>'candidate_review_id')::uuid AND owner_id = v_user FOR UPDATE;
  IF NOT FOUND OR v_candidate.proposal_type <> 'node' OR v_candidate.status <> 'pending' THEN
    RAISE EXCEPTION 'Original node proposal unavailable or already resolved';
  END IF;
  SELECT * INTO v_target FROM public.knowledge_nodes
   WHERE id = v_merge.payload->>'target_node_id' AND owner_id = v_user FOR UPDATE;
  IF NOT FOUND OR v_target.knowledge_space <> 'external' OR v_target.node_type <> (v_candidate.payload->>'node_type') THEN
    RAISE EXCEPTION 'Target node missing, not external, or type mismatch';
  END IF;
  IF COALESCE(v_candidate.payload->>'knowledge_space','external') <> 'external' THEN
    RAISE EXCEPTION 'Cannot merge personal knowledge with external source';
  END IF;
  v_source := COALESCE(v_merge.source_ref, v_merge.payload->>'source_id');
  IF v_source IS NULL OR v_source IS DISTINCT FROM COALESCE(v_candidate.source_ref,v_candidate.payload->>'source_id') THEN
    RAISE EXCEPTION 'Source mismatch';
  END IF;
  PERFORM 1 FROM public.sources WHERE owner_id=v_user AND id=v_source;
  IF NOT FOUND THEN RAISE EXCEPTION 'Source is missing or not owned by caller'; END IF;
  v_quote := btrim(COALESCE(v_candidate.payload->>'evidence_quote',''));
  IF length(v_quote) < 12 OR v_quote IS DISTINCT FROM btrim(COALESCE(v_merge.payload->>'evidence_quote','')) THEN
    RAISE EXCEPTION 'Missing or mismatched evidence quote';
  END IF;
  v_locator := v_candidate.payload->'evidence_locator';
  IF jsonb_typeof(v_locator) IS DISTINCT FROM 'object' THEN v_locator := '{}'::jsonb; END IF;
  -- No update of original node text or knowledge status: only attach provenance.
  INSERT INTO public.knowledge_node_evidence
    (owner_id,node_id,source_id,evidence_quote,evidence_locator,claim_kind,originating_review_id)
  VALUES (v_user,v_target.id,v_source,v_quote,v_locator,'source_claim',v_merge.id)
  RETURNING id INTO v_evidence_id;

  UPDATE public.review_queue SET status='approved',reviewed_at=now()
    WHERE id=v_merge.id AND owner_id=v_user;
  UPDATE public.review_queue SET status='approved',reviewed_at=now()
    WHERE id=v_candidate.id AND owner_id=v_user;

  INSERT INTO public.change_events(owner_id,event_type,entity_id,payload)
  VALUES(v_user,'node_source_reused',v_target.id,jsonb_build_object(
    'merge_review_id',v_merge.id,'candidate_review_id',v_candidate.id,
    'source_id',v_source,'evidence_id',v_evidence_id));
  INSERT INTO public.sync_jobs(owner_id,operation,idempotency_key,payload)
  VALUES(v_user,'export_node_evidence','merge:'||v_merge.id::text,
         jsonb_build_object('node_id',v_target.id,'evidence_id',v_evidence_id))
  ON CONFLICT (owner_id,idempotency_key) DO NOTHING;

  RETURN jsonb_build_object('status','approved','node_id',v_target.id,'evidence_id',v_evidence_id);
END;
$$;
REVOKE ALL ON FUNCTION public.approve_node_reuse(uuid) FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.approve_node_reuse(uuid) TO authenticated;

COMMIT;
