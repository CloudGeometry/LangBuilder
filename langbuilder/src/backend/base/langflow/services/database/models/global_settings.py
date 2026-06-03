from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class GlobalSettings(SQLModel, table=True):  # type: ignore[call-arg]
    """Org-level (deployment-wide) key/value configuration store.

    Used to store system-level settings such as API keys that are scoped
    to the entire deployment rather than per-user. The LangWatch API key
    is the first entry. is_encrypted=True indicates Fernet-encrypted values.
    """

    __tablename__ = "global_settings"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(index=True, unique=True, max_length=100)
    value: str = Field()  # Fernet-encrypted for sensitive values
    is_encrypted: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))
    updated_by: UUID | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
    )
