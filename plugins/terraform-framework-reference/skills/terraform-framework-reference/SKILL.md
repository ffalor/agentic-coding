---
name: terraform-framework-reference
description: Up-to-date Terraform Plugin Framework and terraform-plugin-testing documentation, synced to the versions a provider compiles against, for looking up how the Framework actually works. Covers schemas, attributes and blocks, custom types, plan modification, defaults, state upgrade, identity, import, private state, timeouts, write-only arguments, validators, diagnostics, ephemeral resources, actions, list resources, RPC internals, and acceptance testing with statecheck and plancheck. Use it when writing or reviewing provider code, when checking a Framework interface or method signature, or when the user asks whether a feature exists in their version.
allowed-tools: Bash, Read, Grep, Glob
---

# Terraform Framework Reference

HashiCorp's own documentation for `terraform-plugin-framework` and
`terraform-plugin-testing`, kept on disk for the exact versions a provider compiles
against. It describes what the Framework API is and how the protocol behaves. The files
are byte-identical to what HashiCorp publishes, so code blocks and method signatures are
the real ones rather than a summary.

The Framework gains and renames things between minor versions (`Identity`, `MoveState`,
write-only arguments, `Float32`/`Int32` types), so which version is on disk matters.

## Locate the docs

```bash
DOCS=$(ls -d ~/.claude/plugins/data/terraform-framework-reference-*/ 2>/dev/null | head -1)
echo "$DOCS"
```

If that prints nothing, or `$DOCS/INDEX.md` is missing, the docs have not been synced
yet. Tell the user to run `/terraform-framework-reference:update` and stop. The rendered
site at `developer.hashicorp.com` only serves the newest version, so it is not a
substitute.

## Find the right page

`INDEX.md` is generated at sync time and maps every page to its path, with the title and
a one-line summary. It is the authoritative list of what is available. Grep it for the
concept rather than reading the whole file:

```bash
grep -i 'plan modification\|default' "$DOCS/INDEX.md"
```

Then `Read` the file the index points at. Most pages are a few KB; a handful are long
enough to read in parts when you only need one section.

When a term could live in several places, grep the doc bodies instead of the index:

```bash
grep -rl 'UseStateForUnknown' "$DOCS/framework" | head
```

If the index has no page for what you need, the docs do not cover it.

## Check the version matches

`MANIFEST.json` records what was synced. When a question hinges on whether a feature
exists, compare it against the provider's `go.mod`:

```bash
python3 -c "import json; m=json.load(open('$DOCS/MANIFEST.json')); [print(k, v['version']) for k,v in m['products'].items()]"
grep -E 'terraform-plugin-(framework|testing)' go.mod
```

If they disagree, say so and suggest `/terraform-framework-reference:update`.
