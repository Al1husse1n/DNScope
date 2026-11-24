import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Investigation(Base):
    """Investigation ORM model.

    Notes:
      - findings and assessment are stored as JSONB — denormalized, queryable.
      - risk_score and risk_level are duplicated out of assessment for fast
        filtering on the list endpoint; the canonical source of truth remains assessment.
      - created_at uses server_default=func.now() for monotonic DB-side timestamps.
    """

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain: Mapped[str] = mapped_column(String(253), nullable=False, index=True)
    normalized_domain: Mapped[str] = mapped_column(String(253), nullable=False, index=True)
    risk_score: Mapped[int] = mapped_column(nullable=False, index=True)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    findings: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    assessment: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
