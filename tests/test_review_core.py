import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'app'))
from review_core import potential_duplicates,clean_node,clean_edge

class ReviewCoreTests(unittest.TestCase):
    def test_id_generation(self):
        node=clean_node('CONCEPT','RAG','external','external','SRC-20261105-123456','quote','review')
        self.assertRegex(node['id'],r'^KNW-\d{8}-\d{12}$')
    def test_no_assumed_learning(self):
        with self.assertRaises(ValueError):clean_node('CONCEPT','RAG','verified','external',None,'','')
    def test_hypothetical_tag(self):
        with self.assertRaises(ValueError):clean_node('CONCEPT','RAG','external','hypothetical',None,'','')
    def test_duplicates(self):
        result=potential_duplicates('  RAG ',[{'id':'a','title':'rag'},{'id':'b','title':'TensorFlow'}])
        self.assertEqual(len(result),1)
    def test_self_link(self):
        with self.assertRaises(ValueError):clean_edge('A','REQUIRES','A')
    def test_allowed_relation(self):
        edge=clean_edge('A','PART_OF','B',note='note')
        self.assertEqual(edge['relation_type'],'PART_OF')

if __name__=='__main__':unittest.main()
