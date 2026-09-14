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
// ==========================================
// TOPIC MASTERY & RETENTION TRACKER SCHEMA
// ==========================================

export async function initTopicProgressTable(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS topic_progress (
      user_id TEXT NOT NULL,
      course_id TEXT NOT NULL,
      topic_id TEXT NOT NULL,
      mastery_score INTEGER NOT NULL DEFAULT 0,
      last_reviewed_at TEXT,
      review_count INTEGER NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'unseen',
      PRIMARY KEY (user_id, course_id, topic_id)
    );

    CREATE INDEX IF NOT EXISTS idx_topic_progress_lookup 
      ON topic_progress(user_id, course_id);
    CREATE INDEX IF NOT EXISTS idx_topic_progress_status 
      ON topic_progress(user_id, status);
  `);
}

// Helper: Upsert topic review and calculate decay/mastery status
export async function updateTopicReview(db, { userId, courseId, topicId, quizAccuracy = null }) {
  const existing = await db.get(
    `SELECT * FROM topic_progress WHERE user_id = ? AND course_id = ? AND topic_id = ?`,
    [userId, courseId, topicId]
  );

  const now = new Date().toISOString();
  let reviewCount = (existing?.review_count || 0) + 1;
  let mastery = existing?.mastery_score || 0;

  if (quizAccuracy !== null) {
    // Weighted moving average: 60% historical + 40% latest check
    mastery = existing 
      ? Math.round(mastery * 0.6 + quizAccuracy * 0.4)
      : Math.round(quizAccuracy);
  } else {
    // Passive review bonus
    mastery = Math.min(100, mastery + 10);
  }

  let status = 'learning';
  if (mastery >= 85) status = 'mastered';
  else if (mastery >= 40) status = 'learning';

  await db.run(
    `INSERT INTO topic_progress (user_id, course_id, topic_id, mastery_score, last_reviewed_at, review_count, status)
     VALUES (?, ?, ?, ?, ?, ?, ?)
     ON CONFLICT(user_id, course_id, topic_id) DO UPDATE SET
       mastery_score = excluded.mastery_score,
       last_reviewed_at = excluded.last_reviewed_at,
       review_count = excluded.review_count,
       status = excluded.status`,
    [userId, courseId, topicId, mastery, now, reviewCount, status]
  );

  return { topicId, mastery, status, reviewCount };
}

// Helper: Find decaying or priority review topics
export async function getPriorityDecayingTopic(db, userId) {
  // Topics reviewed over 4 days ago with mastery < 80, or lowest score
  return await db.get(
    `SELECT * FROM topic_progress 
     WHERE user_id = ? 
     ORDER BY 
       CASE status WHEN 'decaying' THEN 1 WHEN 'learning' THEN 2 ELSE 3 END,
       mastery_score ASC, 
       last_reviewed_at ASC 
     LIMIT 1`,
    [userId]
  );
}