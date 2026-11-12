# Agents

Guidance for any coding agent working in this repository.

- Estate-wide conventions: https://github.com/JorisJonkers-dev/workspace/blob/main/CLAUDE.md

## What it holds

A generated manifest, `model-catalog.json`, of every OpenRouter model that advertises tool calling, for the Hermes Agent model picker. See `README.md` for the schema and how to point Hermes at it.

## Build

Regenerate the manifest and the browsable page (CI runs both in `.github/workflows/publish.yml`):

```bash
python3 scripts/generate-catalog.py
python3 scripts/render-page.py --site-dir site
```
