# Path: src/backend/langbuilder/services/database/models/publish_record/model.py

from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import JSON, Column, Enum as SQLEnum, Text, UniqueConstraint, text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from langbuilder.services.database.models.flow.model import Flow
    from langbuilder.services.database.models.user.model import User


class PublishStatusEnum(str, Enum):
    """Status of a published flow."""

    ACTIVE = "ACTIVE"
    UNPUBLISHED = "UNPUBLISHED"
    ERROR = "ERROR"
    PENDING = "PENDING"


class PublishRecordBase(SQLModel):
    """Base model for tracking flow publications to external platforms."""

    # Suppresses warnings during migrations
    __mapper_args__ = {"confirm_deleted_rows": False}

    flow_id: UUID = Field(foreign_key="flow.id", index=True, nullable=False)
    platform: str = Field(index=True, nullable=False, description="Target platform (e.g., 'openwebui', 'mcp')")
    platform_url: str = Field(nullable=False, description="Base URL of the target platform")
    external_id: str = Field(
        nullable=False, description="ID of the model/resource in the external platform"
    )
    published_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    published_by: UUID = Field(foreign_key="user.id", nullable=False)
    status: PublishStatusEnum = Field(
        default=PublishStatusEnum.ACTIVE,
        sa_column=Column(
            SQLEnum(
                PublishStatusEnum,
                name="publish_status_enum",
                values_callable=lambda enum: [member.value for member in enum],
            ),
            nullable=False,
            server_default=text("'ACTIVE'"),
        ),
    )
    metadata_: dict | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
        description="Additional platform-specific metadata",
        alias="metadata",
    )
    last_sync_at: datetime | None = Field(default=None, nullable=True)
    error_message: str | None = Field(
        default=None,
        sa_column=Column(Text, nullable=True),
        description="Error message if status is ERROR",
    )


class PublishRecord(PublishRecordBase, table=True):  # type: ignore[call-arg]
    """Tracks flow publications to external platforms like OpenWebUI."""

    __tablename__ = "publish_record"

    id: UUID = Field(default_factory=uuid4, primary_key=True, unique=True)

    # Relationships
    flow: Optional["Flow"] = Relationship(back_populates="publish_records")
    user: Optional["User"] = Relationship()

    __table_args__ = (
        # Ensure one active publication per flow per platform per URL
        UniqueConstraint(
            "flow_id",
            "platform",
            "platform_url",
            "status",
            name="unique_active_publication",
        ),
    )


class PublishRecordCreate(PublishRecordBase):
    """Model for creating a new publish record."""

    pass


class PublishRecordRead(BaseModel):
    """Model for reading publish record data."""

    id: UUID
    flow_id: UUID
    platform: str
    platform_url: str
    external_id: str
    published_at: datetime
    published_by: UUID
    status: PublishStatusEnum
    metadata_: dict | None = Field(None, alias="metadata")
    last_sync_at: datetime | None = None
    error_message: str | None = None


class PublishRecordUpdate(BaseModel):
    """Model for updating a publish record."""

    status: PublishStatusEnum | None = None
    metadata_: dict | None = Field(None, alias="metadata")
    last_sync_at: datetime | None = None
    error_message: str | None = None
