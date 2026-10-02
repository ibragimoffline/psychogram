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
    assert revision(database) == "0002_pii_aes_gcm"
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
    assert revision(database) == "0002_pii_aes_gcm"
    assert "nonce" in columns(database, "participant_pii")
    assert "use_type" in columns(database, "researches")
