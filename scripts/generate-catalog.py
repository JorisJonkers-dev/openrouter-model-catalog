#!/usr/bin/env python3
"""Regenerate model-catalog.json from the live OpenRouter /v1/models endpoint.

Keeps every model that advertises tool calling (agent-usable), in the Hermes
model-catalog schema (version 1). Models on the upstream Hermes curated list
come first, in upstream order and with upstream descriptions and default
flag, so the picker's "recommended" entry and silent default stay unchanged.
Every other model follows, sorted by id.

Usage:  python scripts/generate-catalog.py [--output model-catalog.json]
"""
import argparse
import datetime
import json
import urllib.request

OPENROUTER_CATALOG_URL = "https://openrouter.ai/api/v1/models"
UPSTREAM_CATALOG_URL = (
    "https://raw.githubusercontent.com/NousResearch/hermes-agent/main/"
    "website/static/api/model-catalog.json"
)


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "JorisJonkers-dev/openrouter-model-catalog",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def supports_tools(item):
    """Mirror hermes_cli.models._openrouter_model_supports_tools: keep a model
    unless it explicitly lists supported_parameters that omit ``tools``."""
    if not isinstance(item, dict):
        return True
    params = item.get("supported_parameters")
    if not isinstance(params, list):
        return True  # unknown capability -> allow
    return "tools" in params


def per_million(value):
    """OpenRouter prices per token as a string; negative means variable."""
    try:
        price = float(value)
    except (TypeError, ValueError):
        return None
    return None if price < 0 else round(price * 1_000_000, 4)


def is_free(item):
    pricing = item.get("pricing") or {}
    try:
        return (float(pricing.get("prompt", "0")) == 0
                and float(pricing.get("completion", "0")) == 0)
    except (TypeError, ValueError):
        return False


def fetch_live_models():
    payload = fetch_json(OPENROUTER_CATALOG_URL)
    items = payload.get("data", [])
    if not isinstance(items, list):
        raise SystemExit("Unexpected /v1/models payload (no data list)")
    return {i["id"]: i for i in items if isinstance(i, dict) and i.get("id")}


def fetch_upstream_curated():
    payload = fetch_json(UPSTREAM_CATALOG_URL)
    models = payload.get("providers", {}).get("openrouter", {}).get("models")
    if not isinstance(models, list) or not models:
        raise SystemExit("Upstream Hermes catalog has no openrouter models")
    return [m for m in models if isinstance(m, dict) and m.get("id")]


def entry(item, upstream):
    pricing = item.get("pricing") or {}
    description = (upstream or {}).get("description") or (
        "free" if is_free(item) else ""
    )
    out = {
        "id": item["id"],
        "description": description,
        "metadata": {
            "name": item.get("name") or item["id"],
            "context_length": item.get("context_length"),
            "prompt_per_mtok": per_million(pricing.get("prompt")),
            "completion_per_mtok": per_million(pricing.get("completion")),
            "curated_upstream": upstream is not None,
        },
    }
    if (upstream or {}).get("default") is True:
        out["default"] = True
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="model-catalog.json")
    ap.add_argument(
        "--min-models",
        type=int,
        default=100,
        help="refuse to write a catalog smaller than this (guards a partial API reply)",
    )
    args = ap.parse_args()

    live = {mid: i for mid, i in fetch_live_models().items() if supports_tools(i)}
    upstream = fetch_upstream_curated()

    models = []
    seen = set()
    for up in upstream:
        item = live.get(up["id"])
        if item is not None and up["id"] not in seen:
            models.append(entry(item, up))
            seen.add(up["id"])
    for mid in sorted(live):
        if mid not in seen:
            models.append(entry(live[mid], None))

    if len(models) < args.min_models:
        raise SystemExit(
            f"Only {len(models)} tool-capable models (< {args.min_models}); "
            "refusing to overwrite the catalog"
        )

    manifest = {
        "version": 1,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "metadata": {
            "generated_from": OPENROUTER_CATALOG_URL,
            "curated_order_from": UPSTREAM_CATALOG_URL,
            "generator": "JorisJonkers-dev openrouter-model-catalog",
            "comment": (
                "Complete list of OpenRouter models that advertise tool "
                "calling. Exposes every usable model to the Hermes picker "
                "instead of the upstream curated subset."
            ),
        },
        "providers": {
            "openrouter": {
                "metadata": {"scope": "full", "count": len(models)},
                "models": models,
            }
        },
    }
    with open(args.output, "w") as fh:
        json.dump(manifest, fh, indent=2)
        fh.write("\n")
    print(f"Wrote {len(models)} models ({len(seen)} upstream-curated) to {args.output}")


if __name__ == "__main__":
    main()
