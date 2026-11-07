import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from relation_discovery import explicit_candidates,validate_suggestions,related_node_pairs
N=[{'id':'KNW-20261107-111','title':'RAG','node_type':'CONCEPT'},
{'id':'KNW-20261107-222','title':'embeddings','node_type':'CONCEPT'},
{'id':'KNW-20261107-333','title':'Python','node_type':'SKILL'}]
class TestRelationDiscovery(unittest.TestCase):
 def test_explicit(self):
  r=explicit_candidates(N,'RAG uses embeddings.');self.assertEqual(len(r),1);self.assertEqual(r[0]['relation_type'],'APPLIES')
 def test_no_hallucinated_relation(self):
  self.assertEqual(explicit_candidates(N,'RAG, embeddings and Python are popular.'),[])
 def test_existing_dedup(self):
  r=explicit_candidates(N,'RAG uses embeddings.')
  self.assertEqual(validate_suggestions(r,N,[r[0]]),[])
 def test_invalid_type(self):
  self.assertEqual(validate_suggestions([{'from_node_id':N[0]['id'],'to_node_id':N[1]['id'],'relation_type':'KNOWS_EVERYTHING','evidence_quote':'RAG uses embeddings'}],N),[])
 def test_missing_evidence(self):
  self.assertEqual(validate_suggestions([{'from_node_id':N[0]['id'],'to_node_id':N[1]['id'],'relation_type':'APPLIES'}],N),[])
 def test_no_self_link(self):
  self.assertEqual(validate_suggestions([{'from_node_id':N[0]['id'],'to_node_id':N[0]['id'],'relation_type':'PART_OF','evidence_quote':'abcdefgh'}],N),[])
 def test_pairs(self):self.assertIsInstance(related_node_pairs(N),list)
if __name__=='__main__':unittest.main()
