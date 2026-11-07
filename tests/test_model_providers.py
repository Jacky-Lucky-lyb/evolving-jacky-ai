import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from model_providers import load_config, make_provider, parse_output
from semantic_extraction import preview

TEXT='# RAG\n\nRAG retrieves external documents before answering.\n'
QUOTE='RAG retrieves external documents before answering.'
class FakeCompletions:
    def __init__(self): self.kwargs=None
    def create(self, **kwargs):
        self.kwargs=kwargs
        return SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',message=SimpleNamespace(content='{"candidates":[{"node_type":"CONCEPT","title":"RAG","evidence_quote":"'+QUOTE+'","rationale":"retrieval"}]}'))])
class TestProviders(unittest.TestCase):
    def test_deepseek_defaults(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY':'test-secret'}, clear=True):
            config=load_config('deepseek')
        self.assertEqual(config.base_url,'https://api.deepseek.com')
        self.assertEqual(config.model,'deepseek-flash')
    def test_openai_defaults(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY':'test-secret'}, clear=True):
            self.assertIsNone(load_config('openai').base_url)
    def test_model_override(self):
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY':'fake'}, clear=True):
            self.assertEqual(load_config('deepseek','deepseek-v4-pro').model,'deepseek-v4-pro')
    def test_missing_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError,'DEEPSEEK_API_KEY'):
                load_config('deepseek')
    def test_custom_rejects_non_https(self):
        with patch.dict(os.environ, {'CUSTOM_API_BASE_URL':'http://third-party.example','CUSTOM_API_KEY':'x','CUSTOM_API_MODEL':'one'}, clear=True):
            with self.assertRaises(ValueError): load_config('custom')
    def test_empty_response(self):
        with self.assertRaisesRegex(ValueError,'empty'): parse_output('  ')
    def test_fake_provider_json_request_and_validator(self):
        fake=FakeCompletions(); cfg=SimpleNamespace(name='deepseek',model='deepseek-flash',base_url='https://api.deepseek.com',api_key='fake')
        captured={}
        def factory(**kwargs):
            captured.update(kwargs)
            return SimpleNamespace(chat=SimpleNamespace(completions=fake))
        p=make_provider(cfg,client_factory=factory)
        output=preview(TEXT,p)
        self.assertEqual(len(output['candidates']),1)
        self.assertEqual(fake.kwargs['response_format'], {'type':'json_object'})
        self.assertEqual(captured['base_url'],'https://api.deepseek.com')
        self.assertEqual(output['candidates'][0]['knowledge_space'],'external')
if __name__=='__main__': unittest.main()
