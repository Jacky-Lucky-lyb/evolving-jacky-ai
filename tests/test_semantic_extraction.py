import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from semantic_extraction import (split_with_offsets, validate_candidates, extract_semantically, STOP_TITLES)

TEXT='# RAG\n\nRAG retrieves external documents before an answer is produced.\n\n## Limitations\n\nNot all retrieval methods use embeddings.\n'

class TestSemanticExtraction(unittest.TestCase):
    def test_exact_offsets(self):
        quote='RAG retrieves external documents before an answer is produced.'
        out=extract_semantically(TEXT, lambda chunk:[{'title':'RAG','node_type':'CONCEPT','evidence_quote':quote,'rationale':'explicit'}])
        self.assertEqual(len(out),1)
        loc=out[0]['evidence_locator']
        self.assertEqual(TEXT[loc['char_start']:loc['char_end']],quote)
        self.assertEqual(out[0]['knowledge_space'],'external')
    def test_fake_evidence_rejected(self):
        self.assertEqual(extract_semantically(TEXT,lambda _: [{'title':'RAG','node_type':'CONCEPT','evidence_quote':'A sentence that does not exist in this text','rationale':''}]),[])
    def test_generic_heading_rejected(self):
        self.assertEqual(extract_semantically(TEXT,lambda _: [{'title':'Limitations','node_type':'CONCEPT','evidence_quote':'Not all retrieval methods use embeddings.','rationale':''}]),[])
    def test_duplicate_dedup(self):
        quote='RAG retrieves external documents before an answer is produced.'
        it={'title':'RAG','node_type':'CONCEPT','evidence_quote':quote,'rationale':''}
        self.assertEqual(len(extract_semantically(TEXT,lambda _: [it,it])),1)
    def test_chunk_coverage(self):
        long='abcd\n\n'*300
        chunks=split_with_offsets(long,105)
        self.assertEqual(''.join(c for _,c in chunks),long)
    def test_too_many_chunks_prevents_partial_import(self):
        with self.assertRaises(ValueError):
            extract_semantically('abcdef '*1500,lambda _: [],max_chunks=1)
    def test_no_auto_identity_assertions(self):
        quote='RAG retrieves external documents before an answer is produced.'
        item={'title':'RAG','node_type':'CONCEPT','evidence_quote':quote,'rationale':''}
        out=extract_semantically(TEXT,lambda _:[item])[0]
        self.assertNotEqual(out['knowledge_space'],'current')
        self.assertEqual(out['knowledge_status'],'unverified')

if __name__=='__main__': unittest.main()
