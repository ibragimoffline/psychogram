from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_alembic(database: Path, target: str) -> None:
    environment = os.environ.copy()
    environment["PSYCHOGRAM_DATABASE_URL"] = (
        "sqlite:///" + database.resolve().as_posix()
    )
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )


def columns(database: Path, table: str) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}


def revision(database: Path) -> str:
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT version_num FROM alembic_version").fetchone()[
            0
        ]


def test_fresh_database_upgrade_head(tmp_path: Path):
    database = tmp_path / "fresh.sqlite"
    run_alembic(database, "head")
    assert revision(database) == "0003_immutability_triggers"
    assert {
        "nonce",
        "algorithm",
        "key_version",
        "field_names",
        "updated_at",
        "updated_by",
    } <= columns(database, "participant_pii")
    assert "use_type" in columns(database, "researches")


def test_existing_0001_database_upgrades_through_0002(tmp_path: Path):
    database = tmp_path / "upgrade.sqlite"
    run_alembic(database, "0001_initial")
    assert revision(database) == "0001_initial"
    assert "nonce" not in columns(database, "participant_pii")
    run_alembic(database, "head")
    assert revision(database) == "0003_immutability_triggers"
    assert "nonce" in columns(database, "participant_pii")
    assert "use_type" in columns(database, "researches")


def test_triggers_freeze_validated_revisions_and_published_versions(tmp_path: Path):
    database = tmp_path / "triggers.sqlite"
    run_alembic(database, "head")
    revision_columns = (
        "id, created_at, tenant_id, research_id, response_id, revision_number, answers, "
        "answer_payload_hash, status, validation_summary, source_type, created_by"
    )
    version_columns = (
        "id, created_at, methodology_id, version_code, schema_version, default_locale, "
        "supported_locales, target_population, estimated_minutes, lifecycle_status, "
        "engine_contract_version, disclaimer_i18n, snapshot, template_id, created_by"
    )
    with sqlite3.connect(database) as connection:
        for number, (row_id, status) in enumerate(
            (("draft", "draft"), ("done", "validated")), 1
        ):
            connection.execute(
                f"INSERT INTO response_revisions ({revision_columns}) "
                "VALUES (?, '2026-01-01', 't', 'r', 'resp', ?, '{}', 'h', ?, '{}', 'manual', "
                "'u')",
                (row_id, number, status),
            )
        for row_id, status in (("draft", "draft"), ("live", "published")):
            connection.execute(
                f"INSERT INTO methodology_versions ({version_columns}) VALUES "
                "(?, '2026-01-01', 'm', ?, 's', 'uz-Latn', '[]', '{}', 5, ?, 'e', "
                "'{}', '{}', 't', 'u')",
                (row_id, row_id, status),
            )
        connection.execute(
            "UPDATE response_revisions SET status = 'validated' WHERE id = 'draft'"
        )
        connection.execute(
            "UPDATE methodology_versions SET lifecycle_status = 'published' WHERE id = 'draft'"
        )
        for statement in (
            "UPDATE response_revisions SET answers = '{\"q1\": 9}' WHERE id = 'done'",
            "UPDATE methodology_versions SET snapshot = '{}' WHERE id = 'live'",
        ):
            try:
                connection.execute(statement)
            except sqlite3.IntegrityError as error:
                assert "immutable" in str(error)
            else:
                raise AssertionError(f"Trigger did not block: {statement}")
