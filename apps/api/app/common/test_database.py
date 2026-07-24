from sqlalchemy.engine import make_url


def assert_safe_test_database(database_url: str, development_url: str | None = None) -> None:
    if not database_url:
        raise RuntimeError("TEST_DATABASE_URL is required for integration tests")
    url = make_url(database_url)
    name = (url.database or "").lower()
    if url.get_backend_name() == "sqlite":
        raise RuntimeError("SQLite is not allowed for PostgreSQL integration tests")
    if not any(token in name for token in ("test", "testing", "ci")):
        raise RuntimeError(f"Unsafe integration database name: {url.database}")
    if development_url and database_url == development_url:
        raise RuntimeError("TEST_DATABASE_URL must not equal DATABASE_URL")
