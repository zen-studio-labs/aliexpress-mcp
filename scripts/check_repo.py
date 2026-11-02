#!/usr/bin/env python3
"""Consistency checks for this repository. Run: python3 scripts/check_repo.py

- every config, example and install link points at the server URL in .mcp.json
- server.json meets the registry limits (and its JSON schema when jsonschema is installed)
- public text avoids the em dash and wording about how data is obtained
"""

import base64
import json
import pathlib
import re
import sys
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEXT_SUFFIXES = {".md", ".json", ".toml", ".yml", ".yaml", ".py", ".txt", ""}
SKIP_DIRS = {".git", "node_modules"}
COPY_TERMS = re.compile(r"\b(scrap\w*|crawl\w*|prox(y|ies)|upstream|fallback|provider|backup|partners?|official api|unofficial)\b|数据源|来源|爬虫|代理|备用|采集", re.IGNORECASE)
# "source" in the data-origin sense; .md and .txt only, because server.json keeps its schema key "source": "github".
SOURCE_TERM = re.compile(r"(?<!open-)\bsources?\b", re.IGNORECASE)
COPY_FILES = ["README.md", "llms.txt", "CHANGELOG.md", "server.json", ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json", "skills/aliexpress/SKILL.md"]

errors = []


def fail(msg):
    errors.append(msg)


def text_files():
    for path in ROOT.rglob("*"):
        if path.is_file() and not SKIP_DIRS.intersection(path.parts) and path.suffix in TEXT_SUFFIXES:
            yield path


def query_param(link, key):
    return urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get(key, [None])[0]


def check_links(url, readme):
    cursor = re.findall(r"https://cursor\.com/en/install-mcp\?[^)\s]+", readme)
    vscode = re.findall(r"https://(?:insiders\.)?vscode\.dev/redirect/mcp/install\?[^)\s]+", readme)
    if not cursor or len(vscode) < 2:
        fail("README: expected one Cursor and two VS Code install links")
    for link in cursor:
        config = json.loads(base64.b64decode(query_param(link, "config")))
        if config != {"url": url} or query_param(link, "name") != "aliexpress":
            fail(f"README: Cursor link config mismatch: {config}")
    for link in vscode:
        config = json.loads(query_param(link, "config"))
        if config != {"type": "http", "url": url} or query_param(link, "name") != "aliexpress":
            fail(f"README: VS Code link config mismatch: {config}")


def check_server_json(url):
    server = json.loads((ROOT / "server.json").read_text())
    if server["remotes"][0]["url"] != url:
        fail("server.json: remote URL differs from .mcp.json")
    if len(server["description"].encode()) > 100:
        fail("server.json: description exceeds 100 bytes")
    try:
        import jsonschema
    except ImportError:
        print("note: jsonschema not installed, schema validation skipped")
        return
    with urllib.request.urlopen(server["$schema"], timeout=30) as resp:
        schema = json.load(resp)
    validator = jsonschema.validators.validator_for(schema)(schema)
    for err in validator.iter_errors(server):
        fail(f"server.json: {err.message}")


def main():
    url = json.loads((ROOT / ".mcp.json").read_text())["mcpServers"]["aliexpress"]["url"]
    assert url.startswith("https://mcp.apify.com/?tools="), url
    actors = re.findall(r"zen-studio/([a-z0-9-]+)", url)
    actor_id = re.compile("|".join(map(re.escape, actors)))

    for path in text_files():
        text = path.read_text(encoding="utf-8")
        rel = path.relative_to(ROOT).as_posix()
        if chr(0x2014) in text:
            fail(f"{rel}: contains an em dash")
        if rel.startswith("examples/") and url not in text:
            fail(f"{rel}: server URL differs from .mcp.json")
    for rel in COPY_FILES:
        stripped = actor_id.sub("", (ROOT / rel).read_text(encoding="utf-8"))
        for match in COPY_TERMS.finditer(stripped):
            fail(f"{rel}: customer copy uses '{match.group(0)}'")
        if rel.endswith((".md", ".txt")):
            for match in SOURCE_TERM.finditer(stripped):
                fail(f"{rel}: customer copy uses '{match.group(0)}'")

    for name in ("README.md",):
        readme = (ROOT / name).read_text(encoding="utf-8")
        if url not in readme:
            fail(f"{name}: server URL differs from .mcp.json")
        check_links(url, readme)
    if url not in (ROOT / "llms.txt").read_text(encoding="utf-8"):
        fail("llms.txt: server URL differs from .mcp.json")
    check_server_json(url)

    for msg in errors:
        print(f"FAIL {msg}")
    print("OK" if not errors else f"{len(errors)} problem(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
