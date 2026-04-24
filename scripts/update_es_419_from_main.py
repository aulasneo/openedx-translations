#!/usr/bin/env python3
"""
Update es_419 frontend translation files from the same file on the main branch.

Only keys that already exist in the current branch file are updated. Keys that
exist only on main are ignored.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path


DEFAULT_TRANSLATIONS_DIR = Path('translations')
TARGET_FILE_GLOB = '*/src/i18n/messages/es_419.json'


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--base-ref',
        default='main',
        help='Git ref to compare against. Defaults to "main".',
    )
    parser.add_argument(
        '--translations-dir',
        type=Path,
        default=DEFAULT_TRANSLATIONS_DIR,
        help='Directory containing translation projects. Defaults to "translations".',
    )
    return parser.parse_args()


def get_target_files(translations_dir: Path) -> list[Path]:
    """
    Find all es_419 frontend translation files.
    """
    return sorted(path.resolve() for path in translations_dir.glob(TARGET_FILE_GLOB) if path.is_file())


def load_json_file(path: Path) -> dict[str, str]:
    """
    Load a JSON translation file.
    """
    with path.open(encoding='utf-8') as file_handle:
        return json.load(file_handle)


def load_json_from_git_ref(git_ref: str, repo_relative_path: Path) -> dict[str, str] | None:
    """
    Load a JSON file from a git ref.

    Returns None when the file does not exist on the given ref.
    """
    completed_process = subprocess.run(
        ['git', 'show', f'{git_ref}:{repo_relative_path.as_posix()}'],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed_process.returncode != 0:
        stderr = completed_process.stderr.lower()
        if 'exists on disk, but not in' in stderr or 'does not exist' in stderr:
            return None
        raise RuntimeError(
            f'Failed to load {repo_relative_path} from {git_ref}: {completed_process.stderr.strip()}'
        )
    return json.loads(completed_process.stdout)


def merge_existing_keys(current_data: dict[str, str], base_data: dict[str, str]) -> dict[str, str]:
    """
    Update only keys that already exist in the current file.
    """
    updated_data = dict(current_data)
    for key in current_data:
        if key in base_data:
            updated_data[key] = base_data[key]
    return updated_data


def update_file_from_ref(file_path: Path, git_ref: str, repo_root: Path) -> tuple[bool, str]:
    """
    Update a single file from the given git ref.

    Returns a tuple of (changed, status_message).
    """
    repo_relative_path = file_path.relative_to(repo_root)
    base_data = load_json_from_git_ref(git_ref, repo_relative_path)
    if base_data is None:
        return False, f'SKIPPED {repo_relative_path} (missing on {git_ref})'

    current_data = load_json_file(file_path)
    updated_data = merge_existing_keys(current_data, base_data)

    if updated_data == current_data:
        return False, f'UNCHANGED {repo_relative_path}'

    with file_path.open('w', encoding='utf-8') as file_handle:
        json.dump(updated_data, file_handle, indent=2, ensure_ascii=False)
        file_handle.write('\n')
    return True, f'UPDATED {repo_relative_path}'


def main() -> int:
    """
    Update all target files and print a summary.
    """
    args = parse_args()
    repo_root = Path.cwd()
    target_files = get_target_files(args.translations_dir)

    changed_count = 0
    skipped_count = 0

    for file_path in target_files:
        try:
            changed, message = update_file_from_ref(file_path, args.base_ref, repo_root)
        except Exception as exc:
            print(f'ERROR {file_path}: {exc}', file=sys.stderr)
            return 1

        print(message)
        if message.startswith('SKIPPED '):
            skipped_count += 1
        elif changed:
            changed_count += 1

    print(
        f'Processed {len(target_files)} files. '
        f'Updated {changed_count}. Skipped {skipped_count}.'
    )
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
