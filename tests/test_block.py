"""Regression tests for block/unblock.

The old implementation used a plain UPDATE, which silently affected 0 rows
when the target had no row yet (e.g. a user who never interacted with the
bot) — making /block trivially bypassable. Blocking must upsert instead.
"""

import os

import pytest

from app.db import init_db, register_user, is_blocked_db, block_entity_db, unblock_entity_db


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    test_db = tmp_path / "test_block_bot.db"
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr("app.db.base.DB_FILE", str(test_db))
    init_db()
    yield
    if test_db.exists():
        os.remove(test_db)


def test_blocking_unregistered_user_works():
    # No row exists for this user yet — the old code would silently no-op.
    assert is_blocked_db(999999) is False
    block_entity_db(999999)
    assert is_blocked_db(999999) is True


def test_blocking_registered_user_works():
    register_user(42, "target")
    assert is_blocked_db(42) is False
    block_entity_db(42)
    assert is_blocked_db(42) is True


def test_unblock_after_block():
    block_entity_db(777)
    assert is_blocked_db(777) is True
    unblock_entity_db(777)
    assert is_blocked_db(777) is False


def test_blocking_group_id_works():
    # Supergroup IDs are negative; they live in the groups table.
    assert is_blocked_db(-1001234567890) is False
    block_entity_db(-1001234567890)
    assert is_blocked_db(-1001234567890) is True
    unblock_entity_db(-1001234567890)
    assert is_blocked_db(-1001234567890) is False


def test_block_does_not_affect_other_users():
    register_user(1, "alice")
    register_user(2, "bob")
    block_entity_db(1)
    assert is_blocked_db(1) is True
    assert is_blocked_db(2) is False
