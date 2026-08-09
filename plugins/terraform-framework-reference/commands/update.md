---
description: Download the Framework and plugin-testing docs matching this provider's go.mod
allowed-tools: Bash, Read
---

Sync the local Terraform Plugin Framework documentation so it matches the versions this
provider compiles against.

## Run the sync

The script reads `go.mod`, resolves each version to its published docs directory, and
writes the `.mdx` files plus `INDEX.md` and `MANIFEST.json` into the plugin's persistent
data directory.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync_docs.py" --project "$(pwd)"
```

If that path does not exist because the variable was not expanded, find the script and
resolve the data directory by hand, then pass it explicitly:

```bash
SCRIPT=$(ls -d ~/.claude/plugins/cache/*/terraform-framework-reference/*/scripts/sync_docs.py 2>/dev/null | sort -V | tail -1)
DATA=$(ls -d ~/.claude/plugins/data/terraform-framework-reference-*/ 2>/dev/null | head -1)
python3 "$SCRIPT" --project "$(pwd)" --data-dir "${DATA:-$HOME/.claude/plugins/data/terraform-framework-reference-agentic-coding}"
```

Requires `git`, `python3`, and `go` on PATH, and network access to github.com. The sync
takes a few seconds and lands about 1.3 MB across roughly 166 files.

## When there is no go.mod

If the current directory is not a Go module, ask the user which versions they want and
pass both explicitly rather than guessing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync_docs.py" \
  --framework-version v1.17.x --testing-version v1.14.x
```

The script also reports when a requested version has no published docs and falls back to
the newest available. Pass that note along to the user, since it means the docs are
slightly ahead of their code.

## Report the result

Show the user what changed, reading it from the script's output and `MANIFEST.json`
rather than describing it generically:

- the framework and plugin-testing versions synced, and whether either was substituted
- file count and total size
- the upstream commit the docs came from
- where the docs landed, and that lookups now happen locally with no network

If the sync fails, report the actual error. The usual causes are no network, `go` missing
from PATH, or a `go.mod` that requires neither module.
