"""Add Clerk identity mapping and make local password fields optional.

Revision ID: 0002_clerk_identity
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_clerk_identity"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("clerk_user_id", sa.String(length=255), nullable=True))
    op.create_index("ix_users_clerk_user_id", "users", ["clerk_user_id"], unique=True)
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=True)


def downgrade() -> None:
    op.alter_column("users", "password_hash", existing_type=sa.String(length=255), nullable=False)
    op.alter_column("users", "email", existing_type=sa.String(length=320), nullable=False)
    op.drop_index("ix_users_clerk_user_id", table_name="users")
    op.drop_column("users", "clerk_user_id")
