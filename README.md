# Evolving Self AI — Public Protocol v0.1

This **public** repository contains schemas, documentation, validation scripts, and fictional examples only. Do not commit personal knowledge, secrets, tokens, or real private documents.

## Layout

- `schemas/`: node and relation definitions
- `docs/`: ingestion, storage, and data rules
- `scripts/`: graph validator
- `examples/`: fictional sample Markdown nodes and relationships
- `migrations/`: future schema/database migrations

## Validate examples

```bash
python3 -m pip install -r requirements.txt
python3 scripts/validate_graph.py --examples
```

The `--examples` mode validates public, fictional sample data. Real vault data should be validated separately; the original v0.1 script's default mode assumed one combined directory, so it is not yet integrated with the separate private vault.

## Separation

The companion private repository `evolving-jacky-vault` stores real personal knowledge and its canonical approved relations. The database and object storage will be configured in later versions.
