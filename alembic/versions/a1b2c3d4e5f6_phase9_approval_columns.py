"""phase9 approval columns

Revision ID: a1b2c3d4e5f6
Revises: 59b0daecd68e
Create Date: 2026-09-26
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "59b0daecd68e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE approvals ADD COLUMN IF NOT EXISTS approval_type VARCHAR(64) DEFAULT 'general'")
    op.execute("ALTER TABLE approvals ADD COLUMN IF NOT EXISTS payload_json TEXT")


def downgrade() -> None:
    op.drop_column("approvals", "payload_json")
    op.drop_column("approvals", "approval_type")
