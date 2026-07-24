import os
import pytest
from app.common.test_database import assert_safe_test_database

_test_url = os.environ.get("TEST_DATABASE_URL", "")
if _test_url:
    assert_safe_test_database(_test_url, os.environ.get("DEVELOPMENT_DATABASE_URL"))
    os.environ["DATABASE_URL"] = _test_url


@pytest.fixture(scope="session")
def test_database_url():
    value = os.environ.get("TEST_DATABASE_URL", "")
    assert_safe_test_database(value, os.environ.get("DATABASE_URL"))
    return value
