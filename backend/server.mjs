import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createHmac, randomBytes, randomUUID, scryptSync, timingSafeEqual } from 'node:crypto';
import { openDatabase } from './database.mjs';
import { initializeStudentData, handleStudentData, getProgress, recordActivity } from './student-data.mjs';

const root = dirname(fileURLToPath(import.meta.url));
const dataDir = join(root, 'data');
const frontendFile = resolve(root, '..', 'index.html');
let db;
let secret;
try {
  db = await openDatabase(join(dataDir, 'flux-one.db'));
  await db.exec(`
  CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
    password_hash TEXT NOT NULL, password_salt TEXT NOT NULL,
    prn TEXT, roll_number TEXT, batch TEXT CHECK(batch IN ('B1', 'B2', 'B3')), created_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS study_sessions (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL, topic TEXT NOT NULL, state TEXT NOT NULL, started_at TEXT NOT NULL,
    last_heartbeat_at TEXT, paused_at TEXT, paused_seconds INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT, duration_seconds INTEGER, focus_rating INTEGER, reflection TEXT
  );
  CREATE TABLE IF NOT EXISTS assignments (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL, topic TEXT, title TEXT NOT NULL, due_at TEXT, priority TEXT NOT NULL DEFAULT 'med',
    status TEXT NOT NULL DEFAULT 'pending', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL, topic TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS enrollments (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL, course_name TEXT NOT NULL, term TEXT, created_at TEXT NOT NULL,
    UNIQUE(user_id, course_code)
  );
  CREATE TABLE IF NOT EXISTS class_roster (
    id TEXT PRIMARY KEY, pnr TEXT UNIQUE NOT NULL, display_name TEXT NOT NULL,
    email TEXT, roll_number TEXT, batch TEXT CHECK(batch IN ('B1', 'B2', 'B3')),
    created_at TEXT NOT NULL, updated_at TEXT NOT NULL
  );
  CREATE TABLE IF NOT EXISTS activity_events (
    id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, view_name TEXT, target TEXT, metadata TEXT,
    created_at TEXT NOT NULL
  );
  CREATE INDEX IF NOT EXISTS idx_activity_events_user_created
    ON activity_events(user_id, created_at DESC);
`);

  await initializeStudentData(db);
  await db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING').run('jwt_secret', randomBytes(48).toString('base64url'));
  secret = (await db.prepare('SELECT value FROM settings WHERE key = ?').get('jwt_secret')).value;
} catch {
  console.error('Database initialization failed. Check DATABASE_URL and database availability.');
  await db?.close().catch(() => {});
  process.exit(1);
}

const now = () => new Date().toISOString();
const send = (res, status, body) => { res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' }); res.end(JSON.stringify(body)); };
const fail = (res, status, detail) => send(res, status, { detail });
const encode = value => Buffer.from(typeof value === 'string' ? value : JSON.stringify(value)).toString('base64url');
const sign = value => createHmac('sha256', secret).update(value).digest('base64url');

function userView(user) {
  return { id: user.id, email: user.email, display_name: user.display_name, created_at: user.created_at, prn: user.prn, roll_number: user.roll_number, batch: user.batch };
}
function tokenFor(user) {
  const header = encode({ alg: 'HS256', typ: 'JWT' });
  const payload = encode({ sub: user.id, exp: Math.floor(Date.now() / 1000) + 604800 });
  return `${header}.${payload}.${sign(`${header}.${payload}`)}`;
}
async function authenticatedUser(req) {
  const token = req.headers.authorization?.replace(/^Bearer\s+/i, '');
  if (!token) return null;
  const [header, payload, signature] = token.split('.');
  if (!header || !payload || !signature) return null;
  const expected = sign(`${header}.${payload}`);
  if (expected.length !== signature.length || !timingSafeEqual(Buffer.from(expected), Buffer.from(signature))) return null;
  let claims;
  try { claims = JSON.parse(Buffer.from(payload, 'base64url').toString()); } catch { return null; }
  return claims && typeof claims.sub === 'string' && claims.exp >= Math.floor(Date.now() / 1000)
    ? await db.prepare('SELECT * FROM users WHERE id = ?').get(claims.sub) : null;
}
async function requireUser(req, res) {
  const user = await authenticatedUser(req);
  if (!user) { fail(res, 401, 'Authentication is required.'); return null; }
  return user;
}
async function requireClassRosterOwner(res, user, { claim = false } = {}) {
  // The first authenticated importer claims ownership atomically. This keeps
  // the roster private without requiring another account or admin dashboard.
  if (claim) await db.prepare('INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO NOTHING').run('class_roster_owner_id', user.id);
  const owner = await db.prepare('SELECT value FROM settings WHERE key = ?').get('class_roster_owner_id');
  if (!owner || owner.value !== user.id) {
    fail(res, 403, 'Only the class roster owner can import or view roster records.');
    return false;
  }
  return true;
}
function normalizeRosterRow(row, index) {
  const pnr = String(row?.pnr || '').trim();
  const displayName = String(row?.display_name || row?.displayName || '').trim();
  const email = String(row?.email || '').trim().toLowerCase();
  const rollNumber = String(row?.roll_number || row?.rollNumber || '').trim();
  const batch = String(row?.batch || '').trim().toUpperCase();
  const errors = [];
  if (!pnr || pnr.length > 64) errors.push('PNR is required and must be at most 64 characters.');
  if (!displayName || displayName.length > 200) errors.push('Display name is required and must be at most 200 characters.');
  if (email && (!email.includes('@') || email.length > 254)) errors.push('Email must be valid when provided.');
  if (batch && !['B1', 'B2', 'B3'].includes(batch)) errors.push('Batch must be B1, B2, or B3 when provided.');
  return { row: { pnr, display_name: displayName, email: email || null, roll_number: rollNumber || null, batch: batch || null }, errors: errors.map(detail => ({ row: index + 1, detail })) };
}
function rosterSummary(rows, owner = false, claimed = owner) {
  const batches = { B1: 0, B2: 0, B3: 0, unknown: 0 };
  for (const row of rows) {
    const batch = ['B1', 'B2', 'B3'].includes(row.batch) ? row.batch : 'unknown';
    batches[batch] += 1;
  }
  return { total: rows.length, batches, owner, claimed };
}
function body(req) {
  return new Promise((resolve, reject) => {
    let size = 0; const chunks = [];
    req.on('data', part => { size += part.length; if (size > 1048576) reject(new Error('Body too large')); else chunks.push(part); });
    req.on('end', () => { try { resolve(chunks.length ? JSON.parse(Buffer.concat(chunks).toString()) : {}); } catch { reject(new Error('Invalid JSON')); } });
    req.on('error', reject);
  });
}
function sessionView(row) {
  return { ...row, paused_seconds: Number(row.paused_seconds || 0), duration_seconds: row.duration_seconds === null ? null : Number(row.duration_seconds), focus_rating: row.focus_rating === null ? null : Number(row.focus_rating) };
}

const server = createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', req.headers.origin || 'http://127.0.0.1:3000');
  res.setHeader('Access-Control-Allow-Headers', 'Authorization, Content-Type');
  res.setHeader('Access-Control-Allow-Methods', 'DELETE, GET, HEAD, OPTIONS, PATCH, POST, PUT');
  if (req.method === 'OPTIONS') return res.writeHead(204).end();
  const url = new URL(req.url, 'http://127.0.0.1'); const route = url.pathname;
  try {
    if (req.method === 'GET' && route === '/') {
      const frontend = await readFile(frontendFile);
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' });
      return res.end(frontend);
    }
    if (req.method === 'GET' && route === '/assets/workspace.js') {
      const script = await readFile(resolve(root, '..', 'assets', 'workspace.js'));
      res.writeHead(200, { 'Content-Type': 'text/javascript; charset=utf-8', 'Cache-Control': 'no-cache' });
      return res.end(script);
    }
    if (req.method === 'GET' && route === '/health') {
      try {
        await db.prepare('SELECT 1 AS ok').get();
        return send(res, 200, { status: 'ok', database: db.kind, version: 'class-data-v1' });
      } catch { return send(res, 503, { status: 'unavailable', database: db.kind }); }
    }

    if (req.method === 'POST' && route === '/api/v1/auth/register') {
      const data = await body(req); const email = String(data.email || '').trim().toLowerCase(); const displayName = String(data.display_name || '').trim(); const password = String(data.password || '');
      if (!email || !displayName || password.length < 8) return fail(res, 422, 'Email, display name, and a password of at least 8 characters are required.');
      const user = { id: randomUUID(), email, display_name: displayName, password_salt: randomBytes(16).toString('hex'), created_at: now() };
      user.password_hash = scryptSync(password, user.password_salt, 64).toString('hex');
      const inserted = await db.prepare('INSERT INTO users (id, email, display_name, password_hash, password_salt, created_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(email) DO NOTHING').run(user.id, user.email, user.display_name, user.password_hash, user.password_salt, user.created_at);
      if (!inserted.changes) return fail(res, 409, 'An account with this email already exists.');
      await recordActivity(db, user.id, 'account_create', 'Account created', null, { source: 'server' });
      return send(res, 201, userView(user));
    }
    if (req.method === 'POST' && route === '/api/v1/auth/login') {
      const data = await body(req); const user = await db.prepare('SELECT * FROM users WHERE email = ?').get(String(data.email || '').trim().toLowerCase());
      if (!user) return fail(res, 401, 'Invalid email or password.');
      const candidate = scryptSync(String(data.password || ''), user.password_salt, 64).toString('hex');
      if (!timingSafeEqual(Buffer.from(candidate), Buffer.from(user.password_hash))) return fail(res, 401, 'Invalid email or password.');
      await recordActivity(db, user.id, 'login', 'Signed in', null, { source: 'server' });
      return send(res, 200, { access_token: tokenFor(user), token_type: 'bearer' });
    }
    if (req.method === 'GET' && route === '/api/v1/auth/me') { const user = await requireUser(req, res); if (user) send(res, 200, userView(user)); return; }
    if (route === '/api/v1/profile') {
      const user = await requireUser(req, res); if (!user) return;
      if (req.method === 'GET') return send(res, 200, userView(user));
      if (req.method === 'PUT') {
        const data = await body(req); const displayName = String(data.display_name || user.display_name).trim(); const prn = String(data.prn || '').trim(); const roll = String(data.roll_number || '').trim(); const batch = String(data.batch || '').trim();
        if (!displayName || !prn || !roll || !['B1', 'B2', 'B3'].includes(batch)) return fail(res, 422, 'Display name, PRN, roll number, and batch B1, B2, or B3 are required.');
        await db.prepare('UPDATE users SET display_name = ?, prn = ?, roll_number = ?, batch = ? WHERE id = ?').run(displayName, prn, roll, batch, user.id);
        await recordActivity(db, user.id, 'profile_update', 'Student profile saved', null, { source: 'server' });
        return send(res, 200, userView(await db.prepare('SELECT * FROM users WHERE id = ?').get(user.id)));
      }
    }
    if (['/api/v1/catalog', '/api/v1/progress', '/api/v1/progress/topics', '/api/v1/quizzes/attempts', '/api/v1/activity/preferences', '/api/v1/activity/events'].includes(route)) {
      const user = await requireUser(req, res); if (!user) return;
      return await handleStudentData({ req, res, url, user, db, body, send, fail });
    }
    if (req.method === 'GET' && route === '/api/v1/dashboard/overview') {
      const user = await requireUser(req, res); if (!user) return;
      return send(res, 200, { stats: (await getProgress(db, user.id)).stats });
    }
    if (req.method === 'GET' && route === '/api/v1/sessions/active') {
      const user = await requireUser(req, res); if (!user) return;
      const session = await db.prepare("SELECT s.*, COALESCE(p.target_seconds,2700) target_seconds FROM study_sessions s LEFT JOIN study_session_plans p ON s.id = p.session_id WHERE s.user_id = ? AND s.state IN ('active','paused') ORDER BY s.started_at DESC LIMIT 1").get(user.id);
      return send(res, 200, session ? sessionView(session) : null);
    }
    if (req.method === 'POST' && route === '/api/v1/sessions/start') {
      const user = await requireUser(req, res); if (!user) return; const data = await body(req); const course = String(data.course_code || '').trim(); const topic = String(data.topic || '').trim();
      if (!course || !topic) return fail(res, 422, 'Course code and topic are required.');
      const targetSeconds = Number(data.target_seconds ?? 2700);
      if (!Number.isInteger(targetSeconds) || targetSeconds < 60 || targetSeconds > 14400) return fail(res, 422, 'Study duration must be between 1 minute and 4 hours.');
      const session = { id: randomUUID(), user_id: user.id, course_code: course, topic, state: 'active', started_at: now(), last_heartbeat_at: now(), paused_seconds: 0, paused_at: null, completed_at: null, duration_seconds: null, focus_rating: null, reflection: null };
      await db.prepare('INSERT INTO study_sessions (id, user_id, course_code, topic, state, started_at, last_heartbeat_at, paused_seconds) VALUES (?, ?, ?, ?, ?, ?, ?, ?)').run(session.id, session.user_id, session.course_code, session.topic, session.state, session.started_at, session.last_heartbeat_at, 0);
      await db.prepare('INSERT INTO study_session_plans (session_id,target_seconds) VALUES (?,?)').run(session.id, targetSeconds);
      session.target_seconds = targetSeconds;
      await recordActivity(db, user.id, 'study_start', 'Study session started', 'study', { source: 'server' });
      return send(res, 201, sessionView(session));
    }
    const sessionAction = route.match(/^\/api\/v1\/sessions\/([^/]+)\/(heartbeat|pause|resume|complete)$/);
    if (req.method === 'POST' && sessionAction) {
      const user = await requireUser(req, res); if (!user) return; const [, id, action] = sessionAction; const session = await db.prepare('SELECT * FROM study_sessions WHERE id = ? AND user_id = ?').get(id, user.id);
      if (!session) return fail(res, 404, 'Study session not found.');
      if (session.state === 'completed') return action === 'complete' ? send(res, 200, sessionView(session)) : fail(res, 409, 'This study session is already completed.');
      const timestamp = now();
      if (action === 'heartbeat') await db.prepare('UPDATE study_sessions SET last_heartbeat_at = ? WHERE id = ?').run(timestamp, id);
      if (action === 'pause' && session.state === 'active') await db.prepare("UPDATE study_sessions SET state = 'paused', paused_at = ? WHERE id = ?").run(timestamp, id);
      if (action === 'resume' && session.state === 'paused') { const seconds = Math.max(0, Math.round((Date.now() - Date.parse(session.paused_at)) / 1000)); await db.prepare("UPDATE study_sessions SET state = 'active', paused_at = NULL, paused_seconds = paused_seconds + ? WHERE id = ? AND user_id = ? AND state = 'paused'").run(seconds, id, user.id); }
      if (action === 'complete') { const data = await body(req); const rating = Number(data.focus_rating); if (!Number.isInteger(rating) || rating < 1 || rating > 5) return fail(res, 422, 'Focus rating must be 1 to 5.'); const currentPause = session.state === 'paused' ? Math.max(0, Math.round((Date.now() - Date.parse(session.paused_at)) / 1000)) : 0; const paused = Number(session.paused_seconds) + currentPause; const duration = Math.max(0, Math.round((Date.now() - Date.parse(session.started_at)) / 1000) - paused); await db.prepare("UPDATE study_sessions SET state = 'completed', paused_at = NULL, paused_seconds = ?, completed_at = ?, duration_seconds = ?, focus_rating = ?, reflection = ? WHERE id = ?").run(paused, timestamp, duration, rating, String(data.reflection || '').trim() || null, id); }
      if (action !== 'heartbeat') await recordActivity(db, user.id, 'study_' + action, 'Study session ' + ({ pause: 'paused', resume: 'resumed', complete: 'completed' }[action]), 'study', { source: 'server' });
      return send(res, 200, sessionView(await db.prepare('SELECT * FROM study_sessions WHERE id = ?').get(id)));
    }
    if (req.method === 'GET' && route === '/api/v1/sessions/history') { const user = await requireUser(req, res); if (user) send(res, 200, (await db.prepare('SELECT * FROM study_sessions WHERE user_id = ? ORDER BY started_at DESC').all(user.id)).map(sessionView)); return; }
    if (route === '/api/v1/assignments') {
      const user = await requireUser(req, res); if (!user) return;
      if (req.method === 'GET') return send(res, 200, await db.prepare('SELECT * FROM assignments WHERE user_id = ? ORDER BY created_at DESC').all(user.id));
      if (req.method === 'POST') { const data = await body(req); const course = String(data.course_code || '').trim(); const title = String(data.title || '').trim(); if (!course || !title) return fail(res, 422, 'Course code and title are required.'); const assignment = { id: randomUUID(), user_id: user.id, course_code: course, topic: data.topic || null, title, due_at: data.due_at || null, priority: data.priority || 'med', status: 'pending', created_at: now(), updated_at: now() }; await db.prepare('INSERT INTO assignments (id,user_id,course_code,topic,title,due_at,priority,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)').run(assignment.id, assignment.user_id, assignment.course_code, assignment.topic, assignment.title, assignment.due_at, assignment.priority, assignment.status, assignment.created_at, assignment.updated_at); await recordActivity(db, user.id, 'assignment_create', 'Assignment created', 'assignments', { source: 'server' }); return send(res, 201, assignment); }
    }
    const assignmentAction = route.match(/^\/api\/v1\/assignments\/([^/]+)\/toggle$/);
    if (req.method === 'PATCH' && assignmentAction) {
      const user = await requireUser(req, res); if (!user) return;
      const assignment = await db.prepare("UPDATE assignments SET status = CASE WHEN status = 'completed' THEN 'pending' ELSE 'completed' END, updated_at = ? WHERE id = ? AND user_id = ? RETURNING *").get(now(), assignmentAction[1], user.id);
      if (assignment) await recordActivity(db, user.id, 'assignment_toggle', 'Assignment ' + assignment.status, 'assignments', { source: 'server' });
      return assignment ? send(res, 200, assignment) : fail(res, 404, 'Assignment not found.');
    }
    if (route === '/api/v1/notes') {
      const user = await requireUser(req, res); if (!user) return;
      if (req.method === 'GET') { const code = url.searchParams.get('course_code'); const rows = code ? await db.prepare('SELECT * FROM notes WHERE user_id = ? AND course_code = ? ORDER BY created_at DESC').all(user.id, code) : await db.prepare('SELECT * FROM notes WHERE user_id = ? ORDER BY created_at DESC').all(user.id); return send(res, 200, rows); }
      if (req.method === 'POST') { const data = await body(req); const course = String(data.course_code || '').trim(); const topic = String(data.topic || '').trim(); const title = String(data.title || '').trim(); const content = String(data.content || '').trim(); if (!course || !topic || !title || !content) return fail(res, 422, 'Course code, topic, title, and content are required.'); const note = { id: randomUUID(), user_id: user.id, course_code: course, topic, title, content, created_at: now(), updated_at: now() }; await db.prepare('INSERT INTO notes (id,user_id,course_code,topic,title,content,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)').run(note.id, note.user_id, note.course_code, note.topic, note.title, note.content, note.created_at, note.updated_at); await recordActivity(db, user.id, 'note_create', 'Note saved', 'notes', { source: 'server' }); return send(res, 201, note); }
    }
    const noteMatch = route.match(/^\/api\/v1\/notes\/([^/]+)$/);
    if (req.method === 'DELETE' && noteMatch) { const user = await requireUser(req, res); if (!user) return; const result = await db.prepare('DELETE FROM notes WHERE id = ? AND user_id = ?').run(noteMatch[1], user.id); if (result.changes) await recordActivity(db, user.id, 'note_delete', 'Note deleted', 'notes', { source: 'server' }); return result.changes ? res.writeHead(204).end() : fail(res, 404, 'Note not found.'); }
    if (route === '/api/v1/class-roster/summary' && req.method === 'GET') {
      const user = await requireUser(req, res); if (!user) return;
      const rows = await db.prepare('SELECT batch FROM class_roster').all();
      const owner = await db.prepare('SELECT value FROM settings WHERE key = ?').get('class_roster_owner_id');
      return send(res, 200, rosterSummary(rows, owner?.value === user.id, Boolean(owner?.value)));
    }
    if (route === '/api/v1/class-roster/me' && req.method === 'GET') {
      const user = await requireUser(req, res); if (!user) return;
      let match = user.prn ? await db.prepare('SELECT * FROM class_roster WHERE pnr = ?').get(user.prn) : null;
      if (!match && user.email) match = await db.prepare('SELECT * FROM class_roster WHERE lower(email) = lower(?)').get(user.email);
      return send(res, 200, match || null);
    }
    if (route === '/api/v1/class-roster' && req.method === 'GET') {
      const user = await requireUser(req, res); if (!user) return;
      if (!(await requireClassRosterOwner(res, user))) return;
      return send(res, 200, await db.prepare('SELECT * FROM class_roster ORDER BY roll_number, display_name').all());
    }
    if (route === '/api/v1/class-roster/import' && req.method === 'POST') {
      const user = await requireUser(req, res); if (!user) return;
      const data = await body(req);
      if (!Array.isArray(data.rows) || !data.rows.length || data.rows.length > 100) return fail(res, 422, 'Provide between 1 and 100 roster rows.');
      const normalized = data.rows.map(normalizeRosterRow);
      const errors = normalized.flatMap(item => item.errors);
      const seen = new Set();
      normalized.forEach((item, index) => {
        if (seen.has(item.row.pnr)) errors.push({ row: index + 1, detail: 'Duplicate PNR in the import.' });
        seen.add(item.row.pnr);
      });
      if (errors.length) return send(res, 422, { detail: 'Roster validation failed.', errors });
      if (!(await requireClassRosterOwner(res, user, { claim: true }))) return;
      let imported = 0; let updated = 0;
      for (const { row } of normalized) {
        const existing = await db.prepare('SELECT id FROM class_roster WHERE pnr = ?').get(row.pnr);
        const timestamp = now();
        await db.prepare('INSERT INTO class_roster (id,pnr,display_name,email,roll_number,batch,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?) ON CONFLICT(pnr) DO UPDATE SET display_name = excluded.display_name, email = excluded.email, roll_number = excluded.roll_number, batch = excluded.batch, updated_at = excluded.updated_at').run(randomUUID(), row.pnr, row.display_name, row.email, row.roll_number, row.batch, timestamp, timestamp);
        if (existing) updated += 1; else imported += 1;
      }
      const rows = await db.prepare('SELECT batch FROM class_roster').all();
      await recordActivity(db, user.id, 'roster_import', 'Class roster saved', 'roster', { source: 'server' });
      return send(res, 201, { imported, updated, total: rows.length, summary: rosterSummary(rows, true, true) });
    }
    if (route === '/api/v1/enrollments') { const user = await requireUser(req, res); if (!user) return; if (req.method === 'GET') return send(res, 200, await db.prepare('SELECT * FROM enrollments WHERE user_id = ? ORDER BY course_code').all(user.id)); if (req.method === 'POST') { const data = await body(req); const code = String(data.course_code || '').trim(); const name = String(data.course_name || '').trim(); if (!code || !name) return fail(res, 422, 'Course code and course name are required.'); const record = { id: randomUUID(), user_id: user.id, course_code: code, course_name: name, term: data.term || null, created_at: now() }; await db.prepare('INSERT INTO enrollments (id,user_id,course_code,course_name,term,created_at) VALUES (?,?,?,?,?,?) ON CONFLICT(user_id,course_code) DO UPDATE SET course_name = excluded.course_name, term = excluded.term').run(record.id, record.user_id, record.course_code, record.course_name, record.term, record.created_at); await recordActivity(db, user.id, 'enrollment_update', 'Course enrollment saved', 'subjects', { source: 'server' }); return send(res, 201, record); } }
    return fail(res, 404, 'Route not found.');
  } catch (error) {
    if (['Invalid JSON', 'Body too large'].includes(error.message)) return fail(res, error.message === 'Body too large' ? 413 : 400, error.message);
    console.error('An API request failed.'); return fail(res, 500, 'Internal server error.');
  }
});
const port = Number(process.env.PORT || 8001);
let shuttingDown = false;
async function shutdown(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  const deadline = setTimeout(() => process.exit(1), 20_000);
  deadline.unref();
  await new Promise(resolve => server.close(resolve));
  try { await db.close(); } catch { exitCode = 1; }
  clearTimeout(deadline);
  process.exitCode = exitCode;
}
process.once('SIGTERM', () => { void shutdown(); });
process.once('SIGINT', () => { void shutdown(); });
server.on('error', () => {
  console.error('The HTTP server could not listen on its configured port.');
  void shutdown(1);
});
server.listen(port, '0.0.0.0', () => console.log(`FLUX ONE API listening on 0.0.0.0:${port} (${db.kind})`));
