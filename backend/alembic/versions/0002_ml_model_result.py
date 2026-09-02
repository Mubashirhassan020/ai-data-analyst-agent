"""add result column to ml_models

Revision ID: 0002_ml_model_result
Revises: 0001_initial
Create Date: 2026-09-03 00:00:00
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_ml_model_result"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ml_models",
        sa.Column("result", sa.JSON, nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("ml_models", "result")
