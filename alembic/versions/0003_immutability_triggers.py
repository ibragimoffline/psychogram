"""Database triggers that keep validated revisions and published versions immutable.

The API role needs UPDATE on response_revisions and methodology_versions to move
drafts forward, so grants alone cannot stop a direct UPDATE of a validated revision
or a published methodology version. These triggers enforce the same rule as the ORM
before_flush hook in src/models/domain.py, for every connection.

Revision ID: 0003_immutability_triggers
Revises: 0002_pii_aes_gcm
Create Date: 2026-10-02
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0003_immutability_triggers"
down_revision: Union[str, Sequence[str], None] = "0002_pii_aes_gcm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, status column, frozen statuses, message) — mirrors enforce_immutable_records.
RULES = [
    (
        "response_revisions",
        "status",
        ("validated", "superseded", "withdrawn"),
        "Validated response revision is immutable",
    ),
    (
        "methodology_versions",
        "lifecycle_status",
        ("published", "deprecated", "withdrawn"),
        "Published methodology version is immutable",
    ),
]


def _frozen(statuses: tuple[str, ...]) -> str:
    return ", ".join(f"'{status}'" for status in statuses)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    for table, column, statuses, message in RULES:
        name = f"{table}_immutable"
        if dialect == "postgresql":
            op.execute(f"""
                CREATE FUNCTION {name}() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF OLD.{column} IN ({_frozen(statuses)}) THEN
                        RAISE EXCEPTION '{message}' USING ERRCODE = 'restrict_violation';
                    END IF;
                    RETURN NEW;
                END
                $$
                """)
            op.execute(
                f"CREATE TRIGGER {name} BEFORE UPDATE ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {name}()"
            )
        elif dialect == "sqlite":
            op.execute(f"""
                CREATE TRIGGER {name} BEFORE UPDATE ON {table}
                FOR EACH ROW WHEN OLD.{column} IN ({_frozen(statuses)})
                BEGIN
                    SELECT RAISE(ABORT, '{message}');
                END
                """)
        else:
            raise NotImplementedError(f"No immutability trigger for dialect {dialect}")


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    for table, _column, _statuses, _message in RULES:
        name = f"{table}_immutable"
        op.execute(
            f"DROP TRIGGER IF EXISTS {name} ON {table}"
            if dialect == "postgresql"
            else f"DROP TRIGGER IF EXISTS {name}"
        )
        if dialect == "postgresql":
            op.execute(f"DROP FUNCTION IF EXISTS {name}()")
