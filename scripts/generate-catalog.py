#!/usr/bin/env python3
"""Regenerate model-catalog.json from the live OpenRouter /v1/models endpoint.

Filters to models that advertise tool calling (agent-usable), preserving the
Hermes model-catalog schema (version 1). Reads page through OpenRouter's
catalog; writes model-catalog.json in the repo root.

Usage:  python scripts/generate-catalog.py [--output model-catalog.json]
"""
import argparse
import datetime
import json
import urllib.request

OPENROUTER_CATALOG_URL = "https://openrouter.ai/api/v1/models"


def supports_tools(item):
    """Mirror hermes_cli.models._openrouter_model_supports_tools: keep a model
    unless it explicitly lists supported_parameters that omit ``tools``."""
    if not isinstance(item, dict):
        return True
    params = item.get("supported_parameters")
    if not isinstance(params, list):
        return True  # unknown capability -> allow
    return "tools" in params


def is_free(item):
    pricing = item.get("pricing") or {}
    try:
        return (float(pricing.get("prompt", "0")) == 0
                and float(pricing.get("completion", "0")) == 0)
    except (TypeError, ValueError):
        return False


def fetch_models():
    req = urllib.request.Request(
        OPENROUTER_CATALOG_URL, headers={"Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode())
    items = payload.get("data", [])
    if not isinstance(items, list):
        raise SystemExit("Unexpected /v1/models payload (no data list)")
    return [i for i in items if supports_tools(i)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="model-catalog.json")
    args = ap.parse_args()

    models = sorted(fetch_models(), key=lambda i: i["id"])
    manifest = {
        "version": 1,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "metadata": {
            "generated_from": OPENROUTER_CATALOG_URL,
            "generator": "JorisJonkers-dev openrouter-model-catalog",
            "comment": (
                "Complete list of OpenRouter models that advertise tool "
                "calling. Exposes every usable model to the Hermes picker "
                "instead of the upstream curated subset."
            ),
        },
        "providers": {
            "openrouter": {
                "metadata": {"scope": "full"},
                "models": [
                    {
                        "id": m["id"],
                        "description": "free" if is_free(m) else "",
                    }
                    for m in models
                ],
            }
        },
    }
    with open(args.output, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {len(manifest['providers']['openrouter']['models'])} "
          f"models to {args.output}")


if __name__ == "__main__":
    main()