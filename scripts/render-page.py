#!/usr/bin/env python3
"""Render the GitHub Pages site from model-catalog.json.

Writes <site-dir>/index.html (a searchable model list) and a copy of the
manifest at <site-dir>/model-catalog.json. Needs no network access.

Usage:  python scripts/render-page.py [--catalog model-catalog.json] [--site-dir site]
"""
import argparse
import html
import json
import pathlib
import shutil

RAW_URL = (
    "https://raw.githubusercontent.com/JorisJonkers-dev/"
    "openrouter-model-catalog/main/model-catalog.json"
)

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hermes OpenRouter Models</title>
<style>
:root {{
  --bg: #fafaf9; --fg: #1c1917; --muted: #78716c; --line: #e7e5e4;
  --card: #ffffff; --accent: #0f766e; --badge: #f5f5f4;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    --bg: #0c0a09; --fg: #f5f5f4; --muted: #a8a29e; --line: #292524;
    --card: #1c1917; --accent: #5eead4; --badge: #292524;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}}
main {{ max-width: 1100px; margin: 0 auto; padding: 32px 16px 64px; }}
h1 {{ font-size: 1.6rem; margin: 0 0 4px; }}
p.lead {{ color: var(--muted); margin: 0 0 24px; }}
pre {{
  background: var(--card); border: 1px solid var(--line); border-radius: 8px;
  padding: 12px 14px; overflow-x: auto; font-size: 13px;
}}
code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }}
.controls {{ display: flex; gap: 8px; flex-wrap: wrap; margin: 24px 0 12px; }}
input, select {{
  font: inherit; color: var(--fg); background: var(--card);
  border: 1px solid var(--line); border-radius: 6px; padding: 8px 10px;
}}
input {{ flex: 1 1 260px; }}
.count {{ color: var(--muted); font-size: 13px; margin-bottom: 8px; }}
.table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
table {{ width: 100%; border-collapse: collapse; background: var(--card); }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }}
th {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: var(--muted); }}
td.num, th.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
td.id code {{ color: var(--accent); }}
.badge {{
  display: inline-block; font-size: 11px; padding: 1px 6px; margin-left: 6px;
  border-radius: 4px; background: var(--badge); color: var(--muted);
}}
a {{ color: var(--accent); }}
</style>
</head>
<body>
<main>
<h1>Hermes OpenRouter models</h1>
<p class="lead">{count} OpenRouter models that advertise tool calling, as offered by the Hermes
model picker. Updated {updated}. <a href="model-catalog.json">Manifest (JSON)</a></p>

<p>Point Hermes at this catalog in <code>~/.hermes/config.yaml</code>:</p>
<pre><code>model_catalog:
  providers:
    openrouter:
      url: {raw_url}</code></pre>

<div class="controls">
  <input id="q" type="search" placeholder="Filter by id or name, e.g. mistral" aria-label="Filter models">
  <select id="vendor" aria-label="Vendor"><option value="">All vendors</option>{vendor_options}</select>
</div>
<div class="count" id="count"></div>
<div class="table-wrap">
<table>
<thead><tr>
  <th>Model id</th><th>Name</th><th class="num">Context</th>
  <th class="num">$ in / 1M</th><th class="num">$ out / 1M</th>
</tr></thead>
<tbody id="rows">
{rows}
</tbody>
</table>
</div>
</main>
<script>
const q = document.getElementById("q");
const vendor = document.getElementById("vendor");
const rows = [...document.querySelectorAll("#rows tr")];
const count = document.getElementById("count");
function apply() {{
  const text = q.value.trim().toLowerCase();
  const v = vendor.value;
  let shown = 0;
  for (const r of rows) {{
    const ok = (!v || r.dataset.vendor === v) && (!text || r.dataset.search.includes(text));
    r.hidden = !ok;
    if (ok) shown++;
  }}
  count.textContent = shown + " of " + rows.length + " models";
}}
q.addEventListener("input", apply);
vendor.addEventListener("change", apply);
apply();
</script>
</body>
</html>
"""


def fmt_price(value):
    if value is None:
        return "variable"
    return "0" if value == 0 else f"{value:g}"


def fmt_context(value):
    if not isinstance(value, int):
        return ""
    if value >= 1_000_000:
        return f"{value / 1_000_000:g}M"
    return f"{value // 1000}K" if value >= 1000 else str(value)


def row(model):
    meta = model.get("metadata") or {}
    mid = model["id"]
    name = meta.get("name") or mid
    badges = []
    if model.get("default"):
        badges.append("default")
    if meta.get("curated_upstream"):
        badges.append("curated")
    if model.get("description") and model["description"] not in badges:
        badges.append(model["description"])
    badge_html = "".join(f'<span class="badge">{html.escape(b)}</span>' for b in badges)
    return (
        f'<tr data-vendor="{html.escape(mid.split("/")[0])}" '
        f'data-search="{html.escape((mid + " " + name).lower())}">'
        f'<td class="id"><code>{html.escape(mid)}</code>{badge_html}</td>'
        f"<td>{html.escape(name)}</td>"
        f'<td class="num">{fmt_context(meta.get("context_length"))}</td>'
        f'<td class="num">{fmt_price(meta.get("prompt_per_mtok"))}</td>'
        f'<td class="num">{fmt_price(meta.get("completion_per_mtok"))}</td>'
        "</tr>"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", default="model-catalog.json")
    ap.add_argument("--site-dir", default="site")
    args = ap.parse_args()

    manifest = json.loads(pathlib.Path(args.catalog).read_text())
    models = manifest["providers"]["openrouter"]["models"]
    vendors = sorted({m["id"].split("/")[0] for m in models})

    site = pathlib.Path(args.site_dir)
    site.mkdir(parents=True, exist_ok=True)
    (site / "index.html").write_text(
        PAGE.format(
            count=len(models),
            updated=html.escape(manifest.get("updated_at", "unknown")),
            raw_url=RAW_URL,
            vendor_options="".join(
                f'<option value="{html.escape(v)}">{html.escape(v)}</option>' for v in vendors
            ),
            rows="\n".join(row(m) for m in models),
        )
    )
    shutil.copyfile(args.catalog, site / "model-catalog.json")
    print(f"Rendered {len(models)} models into {site}/")


if __name__ == "__main__":
    main()
