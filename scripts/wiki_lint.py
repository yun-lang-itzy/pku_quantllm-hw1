#!/usr/bin/env python3
"""Check this Markdown wiki using only Python's standard library.

Supports the project's simple inline file links and flat frontmatter with JSON
arrays. Does not validate heading anchors, external URLs, or factual claims.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

SPECIAL_PAGES = {'wiki/index.md', 'wiki/log.md'}
PAGE_TYPES = {
    'overview', 'roadmap', 'dashboard', 'questions', 'glossary', 'concept',
    'guide', 'project', 'source', 'catalog', 'query', 'experiment',
}
STATUSES = {'draft', 'reviewed', 'superseded'}
REQUIRED_FIELDS = {'title', 'type', 'status', 'created', 'updated', 'sources', 'tags'}
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^)\n]+)\)')


def without_fences(text: str) -> str:
    """Ignore examples in fenced code blocks, including Markdown templates."""
    output = []
    fence_char = ''
    fence_length = 0
    for line in text.splitlines():
        marker = re.match(r'^\s{0,3}(`{3,}|~{3,})(.*)$', line)
        if not fence_char:
            if marker:
                fence_char = marker[1][0]
                fence_length = len(marker[1])
            else:
                output.append(line)
        elif (marker and marker[1][0] == fence_char
              and len(marker[1]) >= fence_length and not marker[2].strip()):
            fence_char = ''
    return '\n'.join(output)


def metadata(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0] != '---':
        raise ValueError('missing YAML frontmatter')
    fields = {}
    for line in lines[1:]:
        if line == '---':
            return fields
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        key, sep, value = line.partition(':')
        if not sep or not re.fullmatch(r'[a-z_]+', key):
            raise ValueError('use flat key: value frontmatter')
        if key in fields:
            raise ValueError(f'duplicate field: {key}')
        fields[key] = value.strip()
    raise ValueError('unclosed frontmatter')


def iso_date(value: str) -> date:
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('expected YYYY-MM-DD')
    return date.fromisoformat(value)


def check_snapshot(root: Path, item: dict, index_path: Path) -> None:
    """Verify exported repository bytes, including original framework symlinks."""
    index = json.loads(index_path.read_text(encoding='utf-8'))
    if not isinstance(index, dict) or index.get('schema_version') != 1 or index.get('commit') != item['commit']:
        raise ValueError('snapshot schema or commit mismatch')
    if index.get('snapshot_root') != item['snapshot_root']:
        raise ValueError('snapshot root mismatch')
    rel_root = Path(item['snapshot_root'])
    if rel_root.is_absolute() or '..' in rel_root.parts:
        raise ValueError('snapshot root must be a relative path within raw/')
    snapshot = (root / rel_root).resolve()
    if not snapshot.is_relative_to(root / 'raw') or not snapshot.is_dir():
        raise ValueError('snapshot directory is missing or outside raw/')
    expected = set()
    for entry in index['files']:
        rel = Path(entry['path'])
        if rel.is_absolute() or '..' in rel.parts or rel.as_posix() in expected:
            raise ValueError(f'invalid or duplicate snapshot path: {rel}')
        expected.add(rel.as_posix())
        target = snapshot / rel
        if not target.resolve().is_relative_to(snapshot):
            raise ValueError(f'snapshot link escapes its root: {rel}')
        if entry['git_mode'] == '120000':
            if target.is_symlink():
                data = os.fsencode(os.readlink(target))
            elif sys.platform == 'win32' and target.is_file():
                # Git core.symlinks=false checks out link targets as plain files
                # on Windows. Validate their exact original link-text bytes.
                data = target.read_bytes()
            else:
                raise ValueError(f'snapshot symlink missing: {rel}')
        else:
            if target.is_symlink() or not target.is_file():
                raise ValueError(f'snapshot file missing or replaced: {rel}')
            data = target.read_bytes()
        if sha256(data).hexdigest() != entry['sha256'] or len(data) != entry['bytes']:
            raise ValueError(f'snapshot file hash mismatch: {rel}')
    actual = {path.relative_to(snapshot).as_posix() for path in snapshot.rglob('*')
              if path.is_file() or path.is_symlink()}
    if actual != expected:
        raise ValueError(f'snapshot inventory changed: missing={sorted(expected - actual)}, '
                         f'extra={sorted(actual - expected)}')


def check(root: Path) -> tuple[list[str], int, int]:
    errors: list[str] = []
    source_ids: set[str] = set()
    source_paths: set[Path] = set()
    manifest_path = root / 'raw/manifest.json'
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
        if not isinstance(manifest, dict) or manifest.get('schema_version') != 1:
            raise ValueError('unsupported manifest schema')
        entries = manifest.get('sources')
        if not isinstance(entries, list):
            raise ValueError('sources must be an array')
        for item in entries:
            try:
                if not isinstance(item, dict):
                    raise ValueError('source entry must be an object')
                sid = item.get('id', '')
                if not isinstance(sid, str) or not re.fullmatch(r'S\d{3,}', sid):
                    raise ValueError('invalid source id')
                if sid in source_ids:
                    raise ValueError(f'duplicate source id: {sid}')
                source_ids.add(sid)
                if not isinstance(item.get('title'), str) or not item['title'].strip():
                    raise ValueError(f'{sid}: missing title')
                iso_date(item['ingested'])
                raw_path = Path(item['path'])
                if raw_path.is_absolute():
                    raise ValueError(f'{sid}: source path must be relative')
                target = (root / raw_path).resolve()
                if not target.is_relative_to(root / 'raw'):
                    raise ValueError(f'{sid}: source must be within raw/')
                if target in source_paths:
                    raise ValueError(f'{sid}: duplicate source path')
                source_paths.add(target)
                expected = item['sha256']
                if not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
                    raise ValueError(f'{sid}: invalid SHA-256')
                if sha256(target.read_bytes()).hexdigest() != expected:
                    errors.append(f'raw/manifest.json: {sid} source hash mismatch')
                elif item.get('kind') == 'repository-snapshot':
                    check_snapshot(root, item, target)
            except (OSError, ValueError, KeyError, TypeError) as exc:
                errors.append(f'raw/manifest.json: {exc}')
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f'raw/manifest.json: {exc}')

    # Archived originals are not interpreted as generated Wiki content.
    docs = sorted(path for path in root.rglob('*.md')
                  if not any(part in {'.git', '.venv', 'work', '__pycache__', '.obsidian'}
                             for part in path.relative_to(root).parts)
                  and not path.is_relative_to(root / 'raw/sources')
                  and not path.is_relative_to(root / 'raw/inbox')
                  and not path.is_relative_to(root / 'raw/assets'))
    wiki_pages = {path for path in docs if path.is_relative_to(root / 'wiki')}
    inbound: Counter[Path] = Counter()
    index_targets: set[Path] = set()
    summaries: set[str] = set()

    for path in docs:
        rel = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding='utf-8')
        except (OSError, UnicodeError) as exc:
            errors.append(f'{rel}: {exc}')
            continue
        if path in wiki_pages and rel not in SPECIAL_PAGES:
            try:
                fields = metadata(text)
                missing = REQUIRED_FIELDS - fields.keys()
                if missing:
                    raise ValueError(f'missing metadata: {", ".join(sorted(missing))}')
                title = json.loads(fields['title']) if fields['title'].startswith('"') else fields['title']
                if not isinstance(title, str) or not title.strip():
                    raise ValueError('title must be non-empty text')
                if fields['type'] not in PAGE_TYPES:
                    raise ValueError('unknown page type')
                if fields['status'] not in STATUSES:
                    raise ValueError('unknown page status')
                if iso_date(fields['updated']) < iso_date(fields['created']):
                    raise ValueError('updated date precedes created date')
                refs = json.loads(fields['sources'])
                tags = json.loads(fields['tags'])
                if not isinstance(refs, list) or not all(isinstance(x, str) for x in refs):
                    raise ValueError('sources must be a JSON array of source IDs')
                if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
                    raise ValueError('tags must be a JSON array of strings')
                unknown = set(refs) - source_ids
                if unknown:
                    raise ValueError(f'unknown sources: {", ".join(sorted(unknown))}')
                if not refs and fields['status'] != 'draft':
                    raise ValueError('pages without sources must remain draft')
                if fields['type'] == 'source':
                    if not refs:
                        raise ValueError('source summary must reference a registered source')
                    summaries.update(refs)
            except (ValueError, TypeError) as exc:
                errors.append(f'{rel}: {exc}')

        for match in LINK.finditer(without_fences(text)):
            destination = match[1].strip()
            # Simple inline link with an optional title or an angle-wrapped path.
            if destination.startswith('<') and '>' in destination:
                destination = destination[1:destination.index('>')]
            else:
                destination = destination.split()[0] if destination else ''
            try:
                parsed = urlsplit(destination)
            except ValueError:
                errors.append(f'{rel}: malformed link: {destination}')
                continue
            if parsed.scheme or parsed.netloc or not parsed.path:
                continue
            target = (path.parent / unquote(parsed.path)).resolve()
            if not target.is_relative_to(root):
                errors.append(f'{rel}: local link escapes project: {destination}')
            elif not target.exists():
                errors.append(f'{rel}: broken local link: {destination}')
            else:
                if path in wiki_pages and path != target:
                    inbound[target] += 1
                if rel == 'wiki/index.md':
                    index_targets.add(target)

    for path in sorted(wiki_pages):
        rel = path.relative_to(root).as_posix()
        if rel != 'wiki/index.md' and path not in index_targets:
            errors.append(f'{rel}: missing from wiki/index.md')
        if inbound[path] == 0:
            errors.append(f'{rel}: orphan page (no link from another Wiki page)')
    for sid in sorted(source_ids - summaries):
        errors.append(f'{sid}: registered source has no Wiki source summary')
    for required in ('README.md', 'AGENTS.md', 'wiki/index.md', 'wiki/log.md'):
        if not (root / required).is_file():
            errors.append(f'missing required file: {required}')
    return errors, len(wiki_pages), len(source_ids)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parent.parent,
                        help='project root (defaults to the parent of scripts/)')
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        parser.error('project root is not a directory')
    errors, page_count, source_count = check(root)
    if errors:
        for error in errors:
            print(f'ERROR {error}')
        print(f'FAIL: {len(errors)} issue(s)')
        return 1
    print(f'PASS: {page_count} Wiki pages, {source_count} registered source(s); '
          'local links, metadata, index, inbound links, source IDs, hashes and repository snapshots checked.')
    print('Content accuracy, contradictions, heading anchors and external URLs require separate review.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
