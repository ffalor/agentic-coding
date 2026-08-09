# terraform-framework-reference

Puts HashiCorp's Terraform Plugin Framework and `terraform-plugin-testing` documentation
on disk, matched to the versions your provider compiles against, so Claude can look up
how the Framework works.

## Install

```
/plugin marketplace add ffalor/agentic-coding
/plugin install terraform-framework-reference@agentic-coding
```

No documentation ships with the plugin. Sync it once per provider repository:

```
/terraform-framework-reference:update
```

The command reads `go.mod`, resolves each module to its published docs version, and
downloads the matching `.mdx` files. Re-run it after bumping either dependency.

From then on the skill handles lookups on its own: it greps the generated index for the
topic and reads the one page it needs, with no network access.

## What you get

Documentation lands in the plugin's persistent data directory,
`~/.claude/plugins/data/terraform-framework-reference-agentic-coding/`, which survives
plugin updates:

```
INDEX.md          every page's path, title and summary
MANIFEST.json     versions synced, upstream commit, date
framework/        terraform-plugin-framework docs
testing/          terraform-plugin-testing docs
```

For `terraform-plugin-framework v1.17.x` and `terraform-plugin-testing v1.14.x` that is
about 165 files and 1.3 MB.

Files are copied verbatim from `hashicorp/web-unified-docs` at the commit recorded in
`MANIFEST.json`, so code blocks and method signatures are exactly what HashiCorp
publishes.

## Details worth knowing

- If a requested version has no published docs, the sync uses the newest available and
  says so.
- The SDKv2-to-Framework migration guide is not synced. It only matters when porting a
  provider off SDKv2.
- Uninstalling the plugin deletes the data directory unless you pass `--keep-data`.

## Requirements

`git`, `python3` and `go` on PATH, plus network access to github.com when syncing. The
sync uses a blobless sparse clone, so it downloads only the two documentation trees it
needs and removes the temporary clone afterwards.
