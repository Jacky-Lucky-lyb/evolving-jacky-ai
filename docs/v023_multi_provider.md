# V0.2.3 — Multi-provider semantic extraction patch

Install as an **incremental update** to V0.2.3. Copy these two files into `scripts/`:

- `model_providers.py` (new)
- `ingest_semantic.py` (replace prior V0.2.3 version)

Add `tests/test_model_providers.py` and this documentation to matching folders. Keep your existing `semantic_extraction.py`, `ingest_knowledge.py`, Streamlit app, Supabase schema and previously working tests unchanged.

## Install and test

```bash
python3 -m pip install openai
python3 -m unittest discover -s tests -p 'test_model_providers.py' -v
```

## DeepSeek (default)

Use your **own local** terminal, and never commit your API key. If possible, use an OS password manager or secure environment injection; `export` in a terminal persists only for that shell session unless you save it elsewhere.

```bash
export DEEPSEEK_API_KEY='YOUR_DEEPSEEK_KEY'
python3 scripts/ingest_semantic.py --provider deepseek --file examples/sample_learning.md --mode preview
```

Default DeepSeek model is `deepseek-flash`. Override it only with a model your account/API supports, e.g. `--model deepseek-v4-pro`.

## OpenAI

```bash
export OPENAI_API_KEY='YOUR_OPENAI_KEY'
python3 scripts/ingest_semantic.py --provider openai --file examples/sample_learning.md --mode preview
```

## Other OpenAI-compatible APIs

```bash
export CUSTOM_API_BASE_URL='https://provider.example.com/v1'
export CUSTOM_API_MODEL='provider-model'
export CUSTOM_API_KEY='YOUR_PROVIDER_KEY'
python3 scripts/ingest_semantic.py --provider custom --file examples/sample_learning.md --mode preview
```

Custom endpoints must support `/chat/completions` and `response_format={"type":"json_object"}`. Not all providers do. A custom base URL is trusted with the key and the submitted document; only configure a provider you trust. Key names and contents are **never** stored in knowledge records. The code does not silently fall back to another provider when a request fails.

The CLI prints provider/model only (never API key). Model input is transmitted to the selected provider and may incur cost. Use `--mode preview` with non-sensitive materials first. Structured JSON is parsed and then passed through your existing exact-quote, deduplication and external-only validator. Even approved external knowledge never implies personal mastery. To stage candidates for review after checking preview, use `--mode upload` with your existing Supabase env vars and an authenticated ordinary user; the existing source hash may reject repeated uploads.

**Testing status:** Python local unit tests validate configuration and mocked responses. No real DeepSeek/OpenAI request is made by the test suite; live API availability, billing, and model output quality require separate testing.
