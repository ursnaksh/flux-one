import { mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

// Both drivers expose the same asynchronous statement interface to the API.
export async function openDatabase(defaultSqlitePath) {
  const databaseUrl = process.env.DATABASE_URL?.trim();
  if (!databaseUrl && process.env.RENDER === 'true') {
    throw new Error('DATABASE_URL is required on Render. Connect a PostgreSQL database before deploying.');
  }

  if (databaseUrl) {
    let protocol;
    try { protocol = new URL(databaseUrl).protocol; } catch { /* Report configuration without exposing credentials. */ }
    if (!['postgres:', 'postgresql:'].includes(protocol)) {
      throw new Error('DATABASE_URL must be a PostgreSQL connection URL.');
    }
    const { Pool } = await import('pg');
    const pool = new Pool({
      connectionString: databaseUrl,
      max: 10,
      connectionTimeoutMillis: 10_000,
      idleTimeoutMillis: 30_000,
    });
    // An idle connection can fail independently of a request. Keep the process
    // alive so the pool can replace it, without logging connection credentials.
    pool.on('error', () => console.error('An idle PostgreSQL connection failed.'));
    const query = (sql, parameters = []) => {
      let index = 0;
      // Statements are application-owned SQL; question marks are placeholders.
      return pool.query(sql.replace(/\?/g, () => `$${++index}`), parameters);
    };
    return {
      kind: 'PostgreSQL',
      exec: sql => pool.query(sql),
      prepare: sql => ({
        get: async (...parameters) => (await query(sql, parameters)).rows[0],
        all: async (...parameters) => (await query(sql, parameters)).rows,
        run: async (...parameters) => ({ changes: (await query(sql, parameters)).rowCount }),
      }),
      close: () => pool.end(),
    };
  }

  const { DatabaseSync } = await import('node:sqlite');
  const sqlitePath = process.env.SQLITE_PATH === ':memory:'
    ? ':memory:'
    : resolve(process.env.SQLITE_PATH || defaultSqlitePath);
  if (sqlitePath !== ':memory:') mkdirSync(dirname(sqlitePath), { recursive: true });
  const sqlite = new DatabaseSync(sqlitePath);
  sqlite.exec('PRAGMA foreign_keys = ON; PRAGMA busy_timeout = 5000;');
  return {
    kind: 'SQLite',
    exec: async sql => sqlite.exec(sql),
    prepare: sql => ({
      get: async (...parameters) => sqlite.prepare(sql).get(...parameters),
      all: async (...parameters) => sqlite.prepare(sql).all(...parameters),
      run: async (...parameters) => sqlite.prepare(sql).run(...parameters),
    }),
    close: async () => sqlite.close(),
  };
}
