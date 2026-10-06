"""Regression test for MAINT-002: removal of unused invalid backup_snippets module."""
from pathlib import Path


def test_backup_snippets_module_does_not_exist():
    repo_root = Path(__file__).resolve().parent.parent
    backup_snippets_path = repo_root / "src" / "core" / "backup_snippets.py"
    assert not backup_snippets_path.exists(), (
        f"Invalid backup snippets module found at {backup_snippets_path}"
    )
