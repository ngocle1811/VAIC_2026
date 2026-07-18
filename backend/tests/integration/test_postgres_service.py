"""Destructive migration test restricted to an explicitly named test database."""

from urllib.parse import urlparse

import pytest
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

from alembic import command

pytestmark = pytest.mark.postgres


def test_postgres_migrations_from_empty_database(integration_settings) -> None:
    if not integration_settings.run_local_integration_tests:
        pytest.skip("RUN_LOCAL_INTEGRATION_TESTS is not enabled")
    url = integration_settings.postgres_test_database_url
    if not url:
        pytest.skip("POSTGRES_TEST_DATABASE_URL is not configured")
    database_name = urlparse(url.replace("postgresql+psycopg2", "postgresql")).path.lstrip("/")
    if not database_name.endswith("_test"):
        pytest.fail("POSTGRES_TEST_DATABASE_URL must target a database ending in '_test'")

    config = Config("alembic.ini")
    config.attributes["database_url"] = url
    command.downgrade(config, "base")
    command.upgrade(config, "head")

    engine = create_engine(url)
    with engine.connect() as connection:
        assert connection.execute(text("select 1")).scalar_one() == 1
        tables = set(inspect(connection).get_table_names())
    assert {
        "alembic_version",
        "generated_reports",
        "knowledge_documents",
        "operational_reports",
    } <= tables
