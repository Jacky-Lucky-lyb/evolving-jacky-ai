import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'ingest_knowledge.py'
spec = importlib.util.spec_from_file_location('ingest_knowledge', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class IngestionTests(unittest.TestCase):
    def test_markdown_candidates(self):
        rows = mod.heuristic_extract('# RAG\nSome introductory text.\n## Embeddings\nMore text')
        self.assertEqual([x['title'] for x in rows], ['RAG','Embeddings'])
    def test_read_text(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d) / 'test.md'
            file.write_text('# Test\nHello world', encoding='utf-8')
            text, raw, name, mime = mod.load_text(file)
            self.assertEqual(mime, 'text/markdown')
            self.assertEqual(name, 'test.md')
            self.assertIn('Test', text)
    def test_reject_executable(self):
        with tempfile.TemporaryDirectory() as d:
            file = Path(d)/'x.exe'
            file.write_bytes(b'hello')
            with self.assertRaises(ValueError): mod.load_text(file)
    def test_direct_text(self):
        text, raw, _, _ = mod.load_text(direct_text='A personal observation')
        self.assertEqual(raw, text.encode('utf-8'))

if __name__ == '__main__': unittest.main()
