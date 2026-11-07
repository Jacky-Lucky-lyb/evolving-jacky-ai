import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
SQL=(ROOT/'migrations/0004_node_evidence_merge.sql').read_text()
APP=(ROOT/'app/evidence_merge_tab.py').read_text()

class MigrationContractTests(unittest.TestCase):
    def test_evidence_table(self):
        self.assertIn('CREATE TABLE IF NOT EXISTS public.knowledge_node_evidence',SQL)
        self.assertIn('UNIQUE (owner_id, originating_review_id)',SQL)
    def test_cross_owner_references(self):
        self.assertIn('FOREIGN KEY (owner_id, node_id)',SQL)
        self.assertIn('FOREIGN KEY (owner_id, source_id)',SQL)
        self.assertIn('FOREIGN KEY (owner_id, originating_review_id)',SQL)
    def test_no_direct_write_from_browser(self):
        self.assertIn('GRANT SELECT ON public.knowledge_node_evidence TO authenticated',SQL)
        self.assertNotIn('GRANT INSERT ON public.knowledge_node_evidence TO authenticated',SQL)
    def test_atomic_rpc_access(self):
        self.assertIn('SECURITY DEFINER SET search_path',SQL)
        self.assertIn('WHERE id = p_merge_id AND owner_id = v_user FOR UPDATE',SQL)
        self.assertIn('REVOKE ALL ON FUNCTION public.approve_node_reuse(uuid) FROM PUBLIC, anon',SQL)
    def test_event_and_queue(self):
        self.assertIn('INSERT INTO public.change_events',SQL)
        self.assertIn('INSERT INTO public.sync_jobs',SQL)
        self.assertIn('ON CONFLICT (owner_id,idempotency_key) DO NOTHING',SQL)
    def test_ui_never_directly_writes_evidence(self):
        self.assertIn("api.rpc('approve_node_reuse'",APP)
        self.assertNotIn("api.create('knowledge_node_evidence'",APP)

if __name__=='__main__':unittest.main()
