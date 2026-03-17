"""Tests for the GlobalSettings SQLModel class."""

from datetime import datetime
from uuid import UUID

from sqlmodel import SQLModel


def test_global_settings_import():
    """GlobalSettings can be imported from models __init__ without circular import."""
    from langflow.services.database.models import GlobalSettings

    assert GlobalSettings is not None


def test_global_settings_tablename():
    """GlobalSettings has the correct __tablename__."""
    from langflow.services.database.models.global_settings import GlobalSettings

    assert GlobalSettings.__tablename__ == "global_settings"


def test_global_settings_registered_in_metadata():
    """GlobalSettings is registered in SQLModel.metadata.tables."""
    # Import to trigger registration
    from langflow.services.database.models.global_settings import GlobalSettings  # noqa: F401

    assert "global_settings" in SQLModel.metadata.tables


def test_global_settings_instantiation_required_fields():
    """GlobalSettings can be instantiated with required fields (key and value)."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="langwatch_api_key", value="some-value")
    assert gs.key == "langwatch_api_key"
    assert gs.value == "some-value"


def test_global_settings_id_is_uuid():
    """GlobalSettings id field is of type UUID and auto-generated."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value")
    assert gs.id is not None
    assert isinstance(gs.id, UUID)


def test_global_settings_key_is_str():
    """GlobalSettings key field is of type str."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="my_key", value="my_value")
    assert isinstance(gs.key, str)


def test_global_settings_value_is_str():
    """GlobalSettings value field is of type str."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="my_key", value="my_value")
    assert isinstance(gs.value, str)


def test_global_settings_is_encrypted_defaults_false():
    """GlobalSettings is_encrypted defaults to False."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value")
    assert gs.is_encrypted is False


def test_global_settings_is_encrypted_is_bool():
    """GlobalSettings is_encrypted field is of type bool."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value", is_encrypted=True)
    assert isinstance(gs.is_encrypted, bool)
    assert gs.is_encrypted is True


def test_global_settings_created_at_is_datetime():
    """GlobalSettings created_at field is of type datetime and auto-populated."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value")
    assert gs.created_at is not None
    assert isinstance(gs.created_at, datetime)


def test_global_settings_updated_at_is_datetime():
    """GlobalSettings updated_at field is of type datetime and auto-populated."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value")
    assert gs.updated_at is not None
    assert isinstance(gs.updated_at, datetime)


def test_global_settings_updated_by_defaults_none():
    """GlobalSettings updated_by field defaults to None."""
    from langflow.services.database.models.global_settings import GlobalSettings

    gs = GlobalSettings(key="test_key", value="test_value")
    assert gs.updated_by is None


def test_global_settings_updated_by_accepts_uuid():
    """GlobalSettings updated_by field accepts a UUID value."""
    import uuid

    from langflow.services.database.models.global_settings import GlobalSettings

    user_id = uuid.uuid4()
    gs = GlobalSettings(key="test_key", value="test_value", updated_by=user_id)
    assert gs.updated_by == user_id
    assert isinstance(gs.updated_by, UUID)


def test_global_settings_key_unique_constraint():
    """GlobalSettings key field has a unique constraint defined."""
    # Import to trigger table registration
    import langflow.services.database.models.global_settings  # noqa: F401

    # Inspect the SQLAlchemy table column for unique constraint
    table = SQLModel.metadata.tables["global_settings"]
    key_col = table.c["key"]
    assert key_col.unique is True


def test_global_settings_models_init_exports():
    """GlobalSettings is accessible from the models package __init__."""
    import langflow.services.database.models as models_pkg

    assert hasattr(models_pkg, "GlobalSettings")
