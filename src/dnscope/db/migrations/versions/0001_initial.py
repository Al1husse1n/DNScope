"""initial

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-24 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "investigations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("normalized_domain", sa.String(length=253), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column("findings", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assessment", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(op.f("ix_investigations_domain"), "investigations", ["domain"], unique=False)
    op.create_index(
        op.f("ix_investigations_normalized_domain"),
        "investigations",
        ["normalized_domain"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigations_risk_score"), "investigations", ["risk_score"], unique=False
    )
    op.create_index(
        op.f("ix_investigations_risk_level"), "investigations", ["risk_level"], unique=False
    )
    op.create_index(
        op.f("ix_investigations_created_at"), "investigations", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_investigations_created_at"), table_name="investigations")
    op.drop_index(op.f("ix_investigations_risk_level"), table_name="investigations")
    op.drop_index(op.f("ix_investigations_risk_score"), table_name="investigations")
    op.drop_index(op.f("ix_investigations_normalized_domain"), table_name="investigations")
    op.drop_index(op.f("ix_investigations_domain"), table_name="investigations")
    op.drop_table("investigations")
