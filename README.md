# OpenRouter Model Catalog (full)

A generated manifest of **every OpenRouter model that advertises tool calling**,
consumed by the Hermes Agent model picker via the `model_catalog` config block.

## Why this exists

Hermes by default shows only a *curated* subset of OpenRouter models
(`OPENROUTER_MODELS` in the CLI, or the upstream `model-catalog.json`). This
repo hosts a **full** catalog so the picker lists every usable model instead
of the curated handful. The estate points:

```yaml
model_catalog:
  providers:
    openrouter:
      url: https://raw.githubusercontent.com/JorisJonkers-dev/openrouter-model-catalog/main/model-catalog.json
```

## Schema

Follows Hermes' model-catalog schema (version 1):

```
{"version": 1, "providers": {"openrouter": {"models": [{"id": "...", "description": "..."}]}}}
```

- `description: "free"` marks models with $0 prompt + $0 completion pricing.

## Regenerating

```bash
python scripts/generate-catalog.py   # fetches https://openrouter.ai/api/v1/models, filters tool-capable, writes model-catalog.json
```

Hermes' `fetch_openrouter_models()` re-filters the manifest against the live
OpenRouter catalog on every picker open, so entries that go offline disappear
automatically; this file just needs to exist and list the IDs.
