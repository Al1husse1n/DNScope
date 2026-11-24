"""public investigations

Revision ID: 0003_public_investigations
Revises: 0002_auth_and_jobs
Create Date: 2026-11-24 16:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_public_investigations"
down_revision: str | None = "0002_auth_and_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "public_investigations",
        sa.Column("share_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("normalized_domain", sa.String(length=253), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        op.f("ix_public_investigations_domain"),
        "public_investigations",
        ["domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_public_investigations_expires_at"),
        "public_investigations",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_public_investigations_expires_at"),
        table_name="public_investigations",
    )
    op.drop_index(
        op.f("ix_public_investigations_domain"),
        table_name="public_investigations",
    )
    op.drop_table("public_investigations")

