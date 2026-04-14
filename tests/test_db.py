import pytest
import os
import sqlite3
from app.db import init_db, register_user, get_all_users, get_user_count, search_users, set_lang, get_lang, get_top_referrers

@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch, tmp_path):
    # Use a temporary database file for testing
    test_db = tmp_path / "test_bot.db"
    monkeypatch.setenv("DATABASE_URL", "") # Force SQLite
    monkeypatch.setattr("app.db.DB_FILE", str(test_db))
    init_db()
    yield
    if test_db.exists():
        os.remove(test_db)

def test_user_registration():
    register_user(123, "testuser")
    users = get_all_users()
    assert len(users) == 1
    assert users[0][0] == 123
    assert users[0][1] == "testuser"

def test_user_count_and_pagination():
    for i in range(15):
        register_user(i, f"user{i}")
    
    assert get_user_count() == 15
    
    # Test pagination
    page1 = get_all_users(limit=10, offset=0)
    assert len(page1) == 10
    
    page2 = get_all_users(limit=10, offset=10)
    assert len(page2) == 5

def test_search_users():
    register_user(1, "alice")
    register_user(2, "bob")
    register_user(3, "charlie")
    
    results = search_users("bo")
    assert len(results) == 1
    assert results[0][1] == "bob"
    
    results_id = search_users("3")
    assert len(results_id) == 1
    assert results_id[0][1] == "charlie"

def test_language_settings():
    register_user(1, "user1")
    assert get_lang(1) == "en" # Default
    
    set_lang(1, "am")
    assert get_lang(1) == "am"

def test_referrals():
    register_user(1, "referrer")
    register_user(2, "referred", referred_by=1)
    
    # Check if referral is counted in all_users
    users = get_all_users(sort_by="referrals")
    referrer = next(u for u in users if u[0] == 1)
    assert referrer[6] == 1 # referrals count is index 6
    
    # Check top referrers
    top = get_top_referrers()
    assert len(top) == 1
    assert top[0][0] == 1
    assert top[0][2] == 1
