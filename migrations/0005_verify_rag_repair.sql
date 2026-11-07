-- Read-only single-result verification after repair. All checks should be true.
SELECT
  EXISTS (SELECT 1 FROM public.knowledge_nodes
    WHERE id='KNW-20261107-546152007574' AND title='RAG' AND status='external') AS main_node_preserved,
  EXISTS (SELECT 1 FROM public.knowledge_nodes
    WHERE id='KNW-20261107-693745323057' AND status='obsolete'
      AND metadata #>> '{merge,merged_into}' = 'KNW-20261107-546152007574') AS duplicate_marked_redirected,
  (SELECT count(*) FROM public.knowledge_node_evidence
    WHERE node_id='KNW-20261107-546152007574'
      AND source_id='SRC-20261107-381487356634'
      AND originating_review_id='f6fdde09-18d5-4589-bdc2-e0f7c12b8b28') = 1 AS evidence_attached_once,
  EXISTS (SELECT 1 FROM public.review_queue
    WHERE id='f6fdde09-18d5-4589-bdc2-e0f7c12b8b28'
      AND status='approved' AND payload->>'resolution'='reconciled_after_duplicate_creation') AS merge_reconciled,
  EXISTS (SELECT 1 FROM public.review_queue
    WHERE id='58f5d116-3c32-497c-a275-4382463733b9' AND status='approved') AS original_review_preserved,
  EXISTS (SELECT 1 FROM public.change_events
    WHERE event_type='duplicate_node_reconciled'
      AND entity_id='KNW-20261107-546152007574') AS audit_event_recorded,
  EXISTS (SELECT 1 FROM public.sync_jobs
    WHERE idempotency_key='repair-rag:f6fdde09-18d5-4589-bdc2-e0f7c12b8b28') AS git_sync_job_queued,
  NOT EXISTS (SELECT 1 FROM public.knowledge_edges
    WHERE from_node_id='KNW-20261107-693745323057'
       OR to_node_id='KNW-20261107-693745323057') AS duplicate_has_no_edges,
  EXISTS (SELECT 1 FROM public.knowledge_edges
    WHERE id='REL-20261107-583686133611'
      AND from_node_id='KNW-20261107-546152007574'
      AND relation_type='APPLIES') AS original_relation_preserved;
