# OpenRouter Model Catalog (full)

A generated manifest of **every OpenRouter model that advertises tool calling**,
consumed by the Hermes Agent model picker via the `model_catalog` config block.

Browse the current list: <https://jorisjonkers-dev.github.io/openrouter-model-catalog/>

## Why this exists

Hermes by default shows only a *curated* subset of OpenRouter models
(`OPENROUTER_MODELS` in the CLI, or the upstream `model-catalog.json`). This
repo hosts a **full** catalog so the picker lists every usable model instead
of the curated handful. Point Hermes at it in `~/.hermes/config.yaml`:

```yaml
model_catalog:
  providers:
    openrouter:
      url: https://raw.githubusercontent.com/JorisJonkers-dev/openrouter-model-catalog/main/model-catalog.json
```

Then run `hermes model --refresh` (or `/model --refresh` in a session) to drop
the one-hour picker cache.

## Schema

Follows Hermes' model-catalog schema (version 1):

```
{"version": 1, "providers": {"openrouter": {"models": [{"id": "...", "description": "...", "metadata": {...}}]}}}
```

- Models on the upstream Hermes curated list come first, in upstream order,
  keeping upstream descriptions and the `"default": true` flag. Every other
  model follows, sorted by id.
- `description: "free"` marks models with $0 prompt + $0 completion pricing.
- `metadata` carries the display name, context length and price per million
  tokens; Hermes ignores it, the Pages site renders it.

## Publishing

`.github/workflows/publish.yml` runs daily, on dispatch, and on pushes that
touch `scripts/`. It regenerates the catalog, commits it only when the model
set changed, and deploys the Pages site.

The generator refuses to write fewer than 100 models, so a partial API reply
cannot empty the picker.

## Regenerating locally

```bash
python scripts/generate-catalog.py   # fetches OpenRouter + upstream Hermes catalog, writes model-catalog.json
python scripts/render-page.py        # renders site/index.html from model-catalog.json
```

Hermes' `fetch_openrouter_models()` re-filters the manifest against the live
OpenRouter catalog on every picker refresh, so entries that go offline
disappear automatically.
