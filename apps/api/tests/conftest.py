import os
import pytest
from app.common.test_database import assert_safe_test_database

_test_url = os.environ.get("TEST_DATABASE_URL", "")
if _test_url:
    assert_safe_test_database(_test_url, os.environ.get("DEVELOPMENT_DATABASE_URL"))
    os.environ["DATABASE_URL"] = _test_url
    # app.common.db may have been imported while pytest plugins initialized the
    # application. Rebind its session factory before any integration test runs
    # so every application path uses the explicitly isolated test database.
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker
    import app.common.db as database

    database.engine = create_engine(_test_url, pool_pre_ping=True)
    database.SessionLocal = sessionmaker(
        bind=database.engine, expire_on_commit=False, class_=Session
    )


@pytest.fixture(scope="session")
def test_database_url():
    value = os.environ.get("TEST_DATABASE_URL", "")
    assert_safe_test_database(value, os.environ.get("DATABASE_URL"))
    return value
