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
    # Batch mode keeps this migration portable to SQLite test databases while
    # producing ordinary ALTER TABLE operations on PostgreSQL.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("clerk_user_id", sa.String(length=255), nullable=True))
        batch.alter_column("email", existing_type=sa.String(length=320), nullable=True)
        batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=True)
        batch.create_index("ix_users_clerk_user_id", ["clerk_user_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.alter_column("password_hash", existing_type=sa.String(length=255), nullable=False)
        batch.alter_column("email", existing_type=sa.String(length=320), nullable=False)
        batch.drop_index("ix_users_clerk_user_id")
        batch.drop_column("clerk_user_id")
