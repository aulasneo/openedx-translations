"""
Tests for update_es_419_from_main.py.
"""

import json
from pathlib import Path

from ..update_es_419_from_main import (
    get_target_files,
    merge_existing_keys,
    update_file_from_ref,
)


def test_merge_existing_keys_updates_overlapping_keys_only():
    current_data = {
        'existing': 'old value',
        'unchanged': 'keep me',
    }
    base_data = {
        'existing': 'new value',
        'new-on-main': 'should not be added',
    }

    updated_data = merge_existing_keys(current_data, base_data)

    assert updated_data == {
        'existing': 'new value',
        'unchanged': 'keep me',
    }


def test_get_target_files_finds_es_419_files(tmp_path):
    translations_dir = tmp_path / 'translations'
    target_file = translations_dir / 'frontend-app-example/src/i18n/messages/es_419.json'
    target_file.parent.mkdir(parents=True)
    target_file.write_text('{}\n', encoding='utf-8')

    non_target_file = translations_dir / 'frontend-app-example/src/i18n/messages/es.json'
    non_target_file.write_text('{}\n', encoding='utf-8')

    assert get_target_files(translations_dir) == [target_file]


def test_update_file_from_ref_updates_only_existing_keys(tmp_path, monkeypatch):
    repo_root = tmp_path
    file_path = repo_root / 'translations/frontend-app-example/src/i18n/messages/es_419.json'
    file_path.parent.mkdir(parents=True)
    file_path.write_text(
        json.dumps(
            {
                'existing': 'old value',
                'local-only': 'keep local',
            },
            indent=2,
        ) + '\n',
        encoding='utf-8',
    )

    monkeypatch.setattr(
        'scripts.update_es_419_from_main.load_json_from_git_ref',
        lambda git_ref, repo_relative_path: {
            'existing': 'new value',
            'main-only': 'should not be added',
        },
    )

    changed, message = update_file_from_ref(file_path, 'main', repo_root)

    assert changed is True
    assert message == 'UPDATED translations/frontend-app-example/src/i18n/messages/es_419.json'
    assert json.loads(file_path.read_text(encoding='utf-8')) == {
        'existing': 'new value',
        'local-only': 'keep local',
    }


def test_update_file_from_ref_skips_missing_base_file(tmp_path, monkeypatch):
    repo_root = tmp_path
    file_path = repo_root / 'translations/frontend-app-example/src/i18n/messages/es_419.json'
    file_path.parent.mkdir(parents=True)
    file_path.write_text('{\n  "existing": "old value"\n}\n', encoding='utf-8')

    monkeypatch.setattr(
        'scripts.update_es_419_from_main.load_json_from_git_ref',
        lambda git_ref, repo_relative_path: None,
    )

    changed, message = update_file_from_ref(file_path, 'main', repo_root)

    assert changed is False
    assert message == 'SKIPPED translations/frontend-app-example/src/i18n/messages/es_419.json (missing on main)'
    assert json.loads(file_path.read_text(encoding='utf-8')) == {
        'existing': 'old value',
    }
