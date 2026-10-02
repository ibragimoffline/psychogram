"""Compare two PostgreSQL databases table by table (row count and content checksum).

Used to verify a restore: run it against the source and the restored database.

    python scripts/compare_databases.py SOURCE_URL TARGET_URL

Exit code 0 means every table in the public schema matches.
"""

from __future__ import annotations

import sys

from sqlalchemy import create_engine, inspect, text


def fingerprint(url: str) -> dict[str, tuple[int, str]]:
    engine = create_engine(url)
    try:
        tables = sorted(inspect(engine).get_table_names(schema="public"))
        result = {}
        with engine.connect() as connection:
            for table in tables:
                # Rows are ordered by their text form so the checksum ignores physical order.
                count, digest = connection.execute(
                    text(
                        f"SELECT count(*), coalesce(md5(string_agg(t::text, '|' ORDER BY t::text)), '') "
                        f'FROM public."{table}" AS t'
                    )
                ).one()
                result[table] = (count, digest)
        return result
    finally:
        engine.dispose()


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    source, target = fingerprint(sys.argv[1]), fingerprint(sys.argv[2])
    mismatches = 0
    for table in sorted(set(source) | set(target)):
        left, right = source.get(table), target.get(table)
        ok = left == right
        mismatches += not ok
        rows = left[0] if left else "missing"
        print(
            f"{'OK  ' if ok else 'DIFF'} {table:32} rows={rows}"
            + ("" if ok else f" target={right}")
        )
    print(f"\n{len(source)} tables, {mismatches} mismatch(es)")
    return 1 if mismatches else 0


if __name__ == "__main__":
    sys.exit(main())
