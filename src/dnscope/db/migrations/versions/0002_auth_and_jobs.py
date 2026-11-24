"""auth and jobs

Revision ID: 0002_auth_and_jobs
Revises: 0001_initial
Create Date: 2026-11-24 14:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002_auth_and_jobs"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("hmac_prefix", sa.String(length=16), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f("ix_api_keys_key_hash"), "api_keys", ["key_hash"], unique=True)
    op.create_index(op.f("ix_api_keys_hmac_prefix"), "api_keys", ["hmac_prefix"], unique=False)

    # 2. P5 auth retrofit: existing P4 smoke rows have no owner; safe to purge for dev DBs.
    op.execute("DELETE FROM investigations")

    # 3. Add api_key_id column to investigations
    op.add_column(
        "investigations",
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_foreign_key(
        "fk_investigations_api_key_id_api_keys",
        "investigations",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        op.f("ix_investigations_api_key_id"),
        "investigations",
        ["api_key_id"],
        unique=False,
    )

    # 4. Create investigation_jobs table
    op.create_table(
        "investigation_jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("api_key_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("domain", sa.String(length=253), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("investigation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("error", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_foreign_key(
        "fk_investigation_jobs_api_key_id_api_keys",
        "investigation_jobs",
        "api_keys",
        ["api_key_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_investigation_jobs_investigation_id_investigations",
        "investigation_jobs",
        "investigations",
        ["investigation_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_investigation_jobs_api_key_id"),
        "investigation_jobs",
        ["api_key_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigation_jobs_status"),
        "investigation_jobs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigation_jobs_investigation_id"),
        "investigation_jobs",
        ["investigation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_investigation_jobs_created_at"),
        "investigation_jobs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("investigation_jobs")
    op.drop_constraint(
        "fk_investigations_api_key_id_api_keys", "investigations", type_="foreignkey"
    )
    op.drop_index(op.f("ix_investigations_api_key_id"), table_name="investigations")
    op.drop_column("investigations", "api_key_id")
    op.drop_table("api_keys")
