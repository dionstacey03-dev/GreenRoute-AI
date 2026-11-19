"""Create users and user-owned saved journeys.

Revision ID: 0001_initial
"""
from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "saved_journeys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("origin", sa.String(length=150), nullable=False),
        sa.Column("destination", sa.String(length=150), nullable=False),
        sa.Column("route_name", sa.String(length=100), nullable=False),
        sa.Column("preference", sa.String(length=20), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_cost_lkr", sa.Float(), nullable=False),
        sa.Column("estimated_co2_kg", sa.Float(), nullable=False),
        sa.Column("green_score", sa.Float(), nullable=False),
        sa.Column("ranking_score", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_saved_journeys_user_created", "saved_journeys", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_saved_journeys_user_created", table_name="saved_journeys")
    op.drop_table("saved_journeys")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
