import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from entity_alignment import normalize, acronym, suggest_matches, build_reuse_proposal

NODES=[{'id':'KNW-20261107-546152007574','title':'RAG','node_type':'CONCEPT','knowledge_space':'external','metadata':{}},
       {'id':'KNW-20261107-083806026204','title':'Embeddings','node_type':'CONCEPT','knowledge_space':'external','metadata':{}},
       {'id':'KNW-20261107-083806026205','title':'Decision making','node_type':'CONCEPT','knowledge_space':'current','metadata':{}}]

class AlignmentTests(unittest.TestCase):
    def test_normalize(self):self.assertEqual(normalize(' RAG  '),'rag')
    def test_acronym(self):self.assertEqual(acronym('Retrieval-Augmented Generation (RAG)'),'rag')
    def test_expansion_match(self):
        out=suggest_matches({'title':'Retrieval-Augmented Generation (RAG)','node_type':'CONCEPT','knowledge_space':'external'},NODES)
        self.assertEqual(out[0]['node_title'],'RAG')
        self.assertEqual(out[0]['action'],'review_reuse')
    def test_no_generic_heading(self):self.assertEqual(suggest_matches({'title':'Limitations'},NODES),[])
    def test_type_mismatch(self):self.assertEqual(suggest_matches({'title':'RAG','node_type':'PROJECT'},NODES),[])
    def test_cross_space_requires_manual(self):
        x=suggest_matches({'title':'Decision making','node_type':'CONCEPT','knowledge_space':'external'},NODES)
        self.assertEqual(x[0]['action'],'manual_comparison')
    def test_alias_match(self):
        nodes=[{'id':'KNW-20261107-555','title':'Retrieval-Augmented Generation','node_type':'CONCEPT','knowledge_space':'external','metadata':{'aliases':['RAG']}}]
        out=suggest_matches({'title':'RAG','node_type':'CONCEPT','knowledge_space':'external'},nodes)
        self.assertEqual(out[0]['score'],1.0)
    def test_build_reuse_proposal(self):
        p={'id':'review-123','payload':{'title':'Retrieval-Augmented Generation (RAG)','node_type':'CONCEPT','knowledge_space':'external','evidence_quote':'RAG retrieves external documents before answering.'}}
        out=build_reuse_proposal(p,NODES[0],'SRC-20261105-174333437011','Verified they refer to same method')
        self.assertEqual(out['proposal_type'],'merge')
        self.assertEqual(out['payload']['target_node_id'],NODES[0]['id'])
    def test_reject_missing_evidence(self):
        p={'id':'review-123','payload':{'title':'RAG','node_type':'CONCEPT','knowledge_space':'external','evidence_quote':'RAG'}}
        with self.assertRaises(ValueError):build_reuse_proposal(p,NODES[0],'SRC-20261105-174333437011','same')
    def test_reject_cross_space_merge(self):
        p={'id':'review-123','payload':{'title':'Decision making','node_type':'CONCEPT','knowledge_space':'external','evidence_quote':'Decision making is an important leadership skill.'}}
        with self.assertRaises(ValueError):build_reuse_proposal(p,NODES[2],'SRC-20261105-174333437011','same')

if __name__=='__main__':unittest.main()
