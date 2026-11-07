import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from apply_v0006_ui_patch import patch_review,patch_alignment,patch_api,patch_relation

class PatchTests(unittest.TestCase):
    def test_review_switches_to_rpc(self):
        sample='import streamlit as st\nwith tab1:\n    api.create("knowledge_nodes", {})\nwith tab2:\n    pass\n'
        result=patch_review(sample)
        self.assertIn('render_guarded_nodes',result)
        self.assertNotIn('api.create("knowledge_nodes"',result)
    def test_api_whitelist(self):
        sample='if function_name != "approve_node_reuse":\n    raise ValueError()'
        result=patch_api(sample)
        self.assertIn('"review_node_proposal"',result)
    def test_idempotent(self):
        x='with tab1:\n    pass\nwith tab2:\n    pass\n'
        self.assertEqual(patch_review(patch_review(x)),patch_review(x))
    def test_relation_rpc(self):
        original = "                    if action=='批准关系':\n                        pass\n                    st.success('操作完成');st.rerun()"
        patched=patch_relation(original)
        self.assertIn('review_edge_proposal',patched)
        compile('def fn():\n'+patched,'test','exec')
    def test_alignment_reject(self):
        x="updated=api.update('review_queue',m['id'],{'status':'rejected','reviewed_at':datetime.now(timezone.utc).isoformat()}, {'status':'eq.pending'})\n                    if not updated: raise RuntimeError('审核记录未更新；请刷新')"
        self.assertIn('reject_merge_proposal',patch_alignment(x))

if __name__=='__main__': unittest.main()
