"""One-time migration utility for legacy FLUX ONE account credentials.

Reads account password hashes from the legacy Render Postgres database and updates
matching users in the current Neon/Postgres database by PRN. The script never
prints password hashes or database URLs.

Required environment variables:
    LEGACY_DATABASE_URL  - old Render Postgres connection string
    DATABASE_URL         - current Neon Postgres connection string

Run from the repository root:
    python backend/scripts/migrate_legacy_auth.py
"""

from __future__ import annotations

import asyncio
import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import asyncpg


def _prepare_dsn(raw: str) -> tuple[str, bool]:
    """Return an asyncpg-safe DSN and whether SSL should be required."""
    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    ssl_required = query.pop("sslmode", "") == "require" or query.pop("ssl", "") == "require"
    query.pop("channel_binding", None)
    clean = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return clean, ssl_required


async def _connect(raw: str) -> asyncpg.Connection:
    dsn, ssl_required = _prepare_dsn(raw)
    return await asyncpg.connect(dsn, ssl="require" if ssl_required else None)


async def main() -> None:
    legacy_url = os.environ.get("LEGACY_DATABASE_URL")
    current_url = os.environ.get("DATABASE_URL")

    if not legacy_url or not current_url:
        raise SystemExit("Set LEGACY_DATABASE_URL and DATABASE_URL before running this script.")

    legacy = await _connect(legacy_url)
    current = await _connect(current_url)

    try:
        legacy_rows = await legacy.fetch(
            """
            SELECT prn, password_salt, password_hash
            FROM users
            WHERE prn IS NOT NULL
              AND password_salt IS NOT NULL
              AND password_hash IS NOT NULL
            """
        )

        matched = 0
        missing = 0

        async with current.transaction():
            for row in legacy_rows:
                legacy_hash = (
                    f"legacy_scrypt${row['password_salt']}${row['password_hash']}"
                )
                result = await current.execute(
                    """
                    UPDATE user_identities AS ui
                    SET password_hash = $1,
                        updated_at = NOW()
                    FROM users AS u
                    WHERE ui.user_id = u.id
                      AND u.prn_number = $2
                    """,
                    legacy_hash,
                    row["prn"],
                )

                if result == "UPDATE 1":
                    matched += 1
                else:
                    missing += 1

        print(f"Legacy credential migration complete: {matched} account(s) updated, {missing} not matched.")
        print("No password hashes or database credentials were printed.")

    finally:
        await legacy.close()
        await current.close()


if __name__ == "__main__":
    asyncio.run(main())
