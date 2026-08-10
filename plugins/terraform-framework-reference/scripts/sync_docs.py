#!/usr/bin/env python3
"""Sync Terraform Plugin Framework and Plugin Testing docs into the plugin data directory.

The docs are published as .mdx source in hashicorp/web-unified-docs, versioned per
minor release. This script resolves the versions a provider actually compiles against
from its go.mod, copies the matching .mdx files to disk, and writes an INDEX.md map
plus a MANIFEST.json recording provenance.

Nothing is fetched at lookup time: agents read local files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = "https://github.com/hashicorp/web-unified-docs.git"

# Product name in web-unified-docs -> (go module suffix, local subdirectory)
PRODUCTS = {
    "terraform-plugin-framework": ("terraform-plugin-framework", "framework"),
    "terraform-plugin-testing": ("terraform-plugin-testing", "testing"),
}

# Sections deliberately not synced. The migrating guide covers moving a provider from
# SDKv2 to the framework, which is not relevant to a provider already on the framework.
EXCLUDED_SECTIONS = {"migrating"}

DESCRIPTION_LIMIT = 110


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed: {' '.join(cmd)}\n{result.stderr.strip()}"
        )
    return result.stdout


def detect_versions(project: Path) -> dict[str, str]:
    """Read required minor versions from go.mod, e.g. {'terraform-plugin-framework': 'v1.17.x'}."""
    gomod = project / "go.mod"
    if not gomod.is_file():
        raise RuntimeError(f"no go.mod in {project}; pass versions explicitly")

    raw = run(["go", "mod", "edit", "-json"], cwd=project)
    requires = json.loads(raw).get("Require") or []

    found: dict[str, str] = {}
    for product, (module_suffix, _) in PRODUCTS.items():
        for req in requires:
            if req["Path"].rsplit("/", 1)[-1] != module_suffix:
                continue
            major, minor = req["Version"].lstrip("v").split(".")[:2]
            found[product] = f"v{major}.{minor}.x"
            break
    if not found:
        raise RuntimeError(
            f"{gomod} requires neither terraform-plugin-framework nor terraform-plugin-testing"
        )
    return found


def version_sort_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in re.findall(r"\d+", version))


def available_versions(clone: Path, product: str) -> list[str]:
    """List published version directories without fetching any file contents."""
    listing = run(
        ["git", "ls-tree", "--name-only", "HEAD", f"content/{product}/"], cwd=clone
    )
    versions = [Path(line).name for line in listing.splitlines() if line.strip()]
    return sorted(versions, key=version_sort_key)


def resolve(requested: str, published: list[str]) -> tuple[str, str | None]:
    """Return the version to sync, plus a note when the requested one is unpublished."""
    if requested in published:
        return requested, None
    newest = published[-1]
    return newest, f"{requested} is not published upstream; using {newest} instead"


def parse_frontmatter(text: str) -> tuple[str, str]:
    """Extract page_title and description from .mdx YAML frontmatter.

    Handles the plain, folded (>-) and literal (|-) scalar styles HashiCorp uses.
    Returns empty strings for anything it cannot read, so a malformed page still
    reaches the index rather than aborting the sync.
    """
    if not text.startswith("---"):
        return "", ""
    end = text.find("\n---", 3)
    if end == -1:
        return "", ""
    block = text[3:end]

    values: dict[str, str] = {}
    key: str | None = None
    parts: list[str] = []

    def flush() -> None:
        if key:
            values[key] = " ".join(parts).strip()

    for line in block.splitlines():
        if line.startswith("#") or not line.strip():
            continue
        match = re.match(r"^([a-z_]+):\s*(.*)$", line)
        if match:
            flush()
            key, inline = match.group(1), match.group(2).strip()
            parts = [] if inline in {">-", "|-", ">", "|", ""} else [inline]
        elif key:
            parts.append(line.strip())
    flush()

    title = values.get("page_title", "").strip().strip("\"'")
    description = re.sub(r"\s+", " ", values.get("description", "")).strip()
    return title, description


def collect(source: Path, destination: Path) -> list[tuple[str, str, str, int]]:
    """Copy .mdx files, skipping excluded sections. Returns index rows."""
    rows: list[tuple[str, str, str, int]] = []
    for path in sorted(source.rglob("*.mdx")):
        relative = path.relative_to(source)
        if relative.parts and relative.parts[0] in EXCLUDED_SECTIONS:
            continue
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = path.read_text(encoding="utf-8")
        target.write_text(text, encoding="utf-8")
        title, description = parse_frontmatter(text)
        rows.append(
            (
                f"{destination.name}/{relative.as_posix()}",
                title or relative.stem,
                description,
                len(text.encode("utf-8")),
            )
        )
    return rows


def write_index(data_dir: Path, synced: dict, rows: list[tuple[str, str, str, int]]) -> None:
    versions = ", ".join(
        f"{product} {info['version']}" for product, info in sorted(synced.items())
    )

    lines = [
        "# Terraform Plugin Framework documentation index",
        "",
        f"Upstream: hashicorp/web-unified-docs @ {synced[next(iter(synced))]['commit'][:12]}",
        f"Versions: {versions}",
        "",
        "Every path below is relative to this file's directory. Grep this index for a",
        "keyword to find the page, then read that one file.",
        "",
    ]

    by_section: dict[str, list[tuple[str, str, str, int]]] = {}
    for row in rows:
        parts = row[0].split("/")
        section = "/".join(parts[:2]) if len(parts) > 2 else parts[0]
        by_section.setdefault(section, []).append(row)

    for section in sorted(by_section):
        lines.append(f"## {section}")
        for path, title, description, _ in by_section[section]:
            if len(description) > DESCRIPTION_LIMIT:
                description = description[: DESCRIPTION_LIMIT - 1].rstrip() + "…"
            suffix = f" — {description}" if description else ""
            lines.append(f"- `{path}` — {title}{suffix}")
        lines.append("")

    (data_dir / "INDEX.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="provider directory holding go.mod (default: cwd)",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="where to write docs; pass ${CLAUDE_PLUGIN_DATA} from the skill",
    )
    parser.add_argument(
        "--framework-version",
        help="override the framework version, e.g. v1.17.x",
    )
    parser.add_argument(
        "--testing-version",
        help="override the plugin-testing version, e.g. v1.14.x",
    )
    args = parser.parse_args()

    data_dir: Path = args.data_dir.expanduser()
    project: Path = args.project.expanduser().resolve()

    requested: dict[str, str]
    overrides = {
        "terraform-plugin-framework": args.framework_version,
        "terraform-plugin-testing": args.testing_version,
    }
    if all(overrides.values()):
        requested = dict(overrides)
        print("Using versions given on the command line:")
    else:
        requested = detect_versions(project)
        for product, override in overrides.items():
            if override:
                requested[product] = override
        print(f"Detected from {project / 'go.mod'}:")
    for product, version in sorted(requested.items()):
        print(f"  {product} {version}")

    temp = Path(tempfile.mkdtemp(prefix="tf-docs-"))
    clone = temp / "web-unified-docs"
    try:
        print("Cloning docs index (no file contents yet)…")
        run(
            [
                "git", "clone",
                "--filter=blob:none", "--no-checkout",
                "--depth", "1", "--single-branch",
                REPO, str(clone),
            ]
        )
        commit = run(["git", "rev-parse", "HEAD"], cwd=clone).strip()

        resolved: dict[str, str] = {}
        sparse_paths: list[str] = []
        for product, version in requested.items():
            published = available_versions(clone, product)
            if not published:
                raise RuntimeError(f"no versions published for {product}")
            actual, note = resolve(version, published)
            if note:
                print(f"  note: {product}: {note}")
            resolved[product] = actual
            sparse_paths.append(f"content/{product}/{actual}/docs")

        print(f"Fetching {len(sparse_paths)} doc tree(s)…")
        run(["git", "sparse-checkout", "init", "--cone"], cwd=clone)
        run(["git", "sparse-checkout", "set", *sparse_paths], cwd=clone)
        run(["git", "checkout", "--quiet"], cwd=clone)

        synced: dict[str, dict] = {}
        rows: list[tuple[str, str, str, int]] = []
        for product, version in resolved.items():
            _, local_name = PRODUCTS[product]
            source = (
                clone / "content" / product / version / "docs" / "plugin" / local_name
            )
            if not source.is_dir():
                raise RuntimeError(f"expected docs at {source}, which does not exist")

            destination = data_dir / local_name
            if destination.exists():
                shutil.rmtree(destination)
            destination.mkdir(parents=True, exist_ok=True)

            product_rows = collect(source, destination)
            rows.extend(product_rows)
            synced[product] = {
                "version": version,
                "requested": requested[product],
                "commit": commit,
                "local_path": local_name,
                "files": len(product_rows),
                "bytes": sum(row[3] for row in product_rows),
            }
            print(
                f"  {local_name}: {len(product_rows)} files, "
                f"{synced[product]['bytes'] // 1024} KB"
            )

        write_index(data_dir, synced, rows)
        manifest = {
            "synced_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "source_repo": REPO,
            "source_commit": commit,
            "project": str(project),
            "excluded_sections": sorted(EXCLUDED_SECTIONS),
            "products": synced,
        }
        (data_dir / "MANIFEST.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
    finally:
        shutil.rmtree(temp, ignore_errors=True)

    total_files = sum(entry["files"] for entry in synced.values())
    total_kb = sum(entry["bytes"] for entry in synced.values()) // 1024
    print(f"\nSynced {total_files} files ({total_kb} KB) to {data_dir}")
    print(f"Index: {data_dir / 'INDEX.md'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except RuntimeError as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
