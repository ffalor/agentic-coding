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
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync_docs.py" \
  --project "$(pwd)" \
  --data-dir "${CLAUDE_PLUGIN_DATA}"
```

Both paths must be passed as arguments. Claude Code substitutes these two placeholders
into this file's text before you read it, but it does not export them as environment
variables to Bash, so the script cannot look them up itself.

If either placeholder reaches the shell unexpanded, the plugin is not installed. Say so
and stop rather than guessing a path: a hand-built path under
`~/.claude/plugins/data/` embeds the marketplace name, and reading a directory left over
from an older marketplace name would silently serve stale docs.

Requires `git`, `python3`, and `go` on PATH, and network access to github.com. The sync
takes a few seconds and lands about 1.3 MB across roughly 166 files.

## When there is no go.mod

If the current directory is not a Go module, ask the user which versions they want and
pass both explicitly rather than guessing:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/sync_docs.py" \
  --data-dir "${CLAUDE_PLUGIN_DATA}" \
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
