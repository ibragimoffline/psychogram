"""Add authenticated-encryption envelope metadata for participant PII.

Revision ID: 0002_pii_aes_gcm
Revises: 0001_initial
Create Date: 2026-07-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_pii_aes_gcm"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    connection = op.get_bind()
    legacy_rows = connection.execute(
        sa.text("SELECT COUNT(*) FROM participant_pii")
    ).scalar_one()
    if legacy_rows:
        raise RuntimeError(
            "0002 cannot infer AES-GCM nonces for legacy participant_pii rows; "
            "the pre-B11 API never wrote these rows, so investigate before upgrade"
        )
    with op.batch_alter_table("participant_pii") as batch_op:
        batch_op.add_column(sa.Column("nonce", sa.String(length=32), nullable=False))
        batch_op.add_column(
            sa.Column("algorithm", sa.String(length=32), nullable=False)
        )
        batch_op.add_column(
            sa.Column("key_version", sa.String(length=64), nullable=False)
        )
        batch_op.add_column(sa.Column("field_names", sa.JSON(), nullable=False))
        batch_op.add_column(
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False)
        )
        batch_op.add_column(
            sa.Column("updated_by", sa.String(length=36), nullable=False)
        )
        batch_op.create_foreign_key(
            "fk_participant_pii_updated_by_users", "users", ["updated_by"], ["id"]
        )


def downgrade() -> None:
    with op.batch_alter_table("participant_pii") as batch_op:
        batch_op.drop_constraint(
            "fk_participant_pii_updated_by_users", type_="foreignkey"
        )
        batch_op.drop_column("updated_by")
        batch_op.drop_column("updated_at")
        batch_op.drop_column("field_names")
        batch_op.drop_column("key_version")
        batch_op.drop_column("algorithm")
        batch_op.drop_column("nonce")
