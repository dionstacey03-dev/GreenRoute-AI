"""Persist estimated journey comparison differences.

Revision ID: 0003_journey_differences
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_journey_differences"
down_revision = "0002_clerk_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "saved_journeys",
        sa.Column(
            "estimated_cost_difference_lkr",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "saved_journeys",
        sa.Column(
            "estimated_co2_difference_kg",
            sa.Float(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("saved_journeys", "estimated_co2_difference_kg")
    op.drop_column("saved_journeys", "estimated_cost_difference_lkr")
