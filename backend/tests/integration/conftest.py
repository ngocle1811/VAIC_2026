import pytest

from app.config import Settings


@pytest.fixture(scope="session")
def integration_settings() -> Settings:
    return Settings()
