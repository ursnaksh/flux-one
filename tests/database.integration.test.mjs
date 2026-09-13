import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { setTimeout as delay } from 'node:timers/promises';
import { catalogSeed } from '../backend/catalog.mjs';

const repository = resolve(dirname(fileURLToPath(import.meta.url)), '..');

async function unusedPort() {
  const listener = createServer();
  await new Promise((resolve, reject) => {
    listener.once('error', reject);
    listener.listen(0, '127.0.0.1', resolve);
  });
  const { port } = listener.address();
  await new Promise((resolve, reject) => listener.close(error => error ? reject(error) : resolve()));
  return port;
}

function launchServer(environment) {
  const env = { ...process.env, NODE_ENV: 'test' };
  delete env.DATABASE_URL;
  delete env.RENDER;
  delete env.SQLITE_PATH;
  const child = spawn(process.execPath, ['backend/server.mjs'], {
    cwd: repository,
    env: { ...env, ...environment },
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  });
  let output = '';
  child.stdout.on('data', data => { output += data.toString(); });
  child.stderr.on('data', data => { output += data.toString(); });
  let result;
  const exited = new Promise(resolve => {
    child.once('error', error => { result = { error }; resolve(result); });
    child.once('exit', (code, signal) => { result = { code, signal }; resolve(result); });
  });
  return {
    child, exited,
    get output() { return output; },
    get result() { return result; },
    async stop() {
      if (!result) child.kill();
      await Promise.race([
        exited,
        delay(3000).then(() => { throw new Error('Test server did not stop.'); }),
      ]);
    },
  };
}

async function startServer(sqlitePath) {
  const port = await unusedPort();
  const server = launchServer({ SQLITE_PATH: sqlitePath, PORT: String(port) });
  server.url = `http://127.0.0.1:${port}`;
  const deadline = Date.now() + 7000;
  while (Date.now() < deadline) {
    if (server.result) throw new Error(`Test server exited at startup: ${server.output}`);
    try {
      const response = await fetch(`${server.url}/health`, { signal: AbortSignal.timeout(350) });
      if (response.ok) return server;
    } catch { /* The server may still be initializing its schema. */ }
    await delay(75);
  }
  await server.stop();
  throw new Error(`Test server did not become healthy: ${server.output}`);
}

test('accounts and all student data persist and remain isolated across server restarts', { timeout: 20000 }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'flux-one-database-test-'));
  const sqlitePath = join(directory, 'isolated.db');
  let server;
  t.after(async () => {
    if (server) await server.stop();
    await rm(directory, { recursive: true, force: true });
  });
  server = await startServer(sqlitePath);

  async function request(path, { method = 'GET', token, data, status = 200 } = {}) {
    const response = await fetch(`${server.url}${path}`, {
      method,
      headers: {
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(data !== undefined ? { 'Content-Type': 'application/json' } : {}),
      },
      body: data !== undefined ? JSON.stringify(data) : undefined,
      signal: AbortSignal.timeout(3000),
    });
    const body = response.status === 204 ? null : await response.json();
    assert.equal(response.status, status, `${method} ${path}: ${JSON.stringify(body)}`);
    return body;
  }

  const alice = { email: 'alice.integration@example.test', display_name: 'Alice', password: 'Correct-test-password-123!' };
  const bob = { email: 'bob.integration@example.test', display_name: 'Bob', password: 'Different-test-password-456!' };
  let aliceId, token, bobToken, noteId, assignmentId, sessionId;

  await t.test('registration, login and profile including PRN, roll number and batch', async () => {
    assert.equal((await request('/health')).database, 'SQLite');
    await request('/api/v1/auth/me', { status: 401 });
    const created = await request('/api/v1/auth/register', { method: 'POST', data: alice, status: 201 });
    aliceId = created.id;
    assert.ok(aliceId);
    assert.equal(created.email, alice.email);
    assert.equal(created.password_hash, undefined);
    await request('/api/v1/auth/register', { method: 'POST', data: alice, status: 409 });
    await request('/api/v1/auth/login', { method: 'POST', data: { ...alice, password: 'incorrect' }, status: 401 });
    token = (await request('/api/v1/auth/login', { method: 'POST', data: { ...alice, email: alice.email.toUpperCase() } })).access_token;
    assert.ok(token);
    assert.equal((await request('/api/v1/auth/me', { token })).id, aliceId);
    const profile = { display_name: 'Alice Student', prn: '20260001001', roll_number: '042', batch: 'B2' };
    await request('/api/v1/profile', { method: 'PUT', token, data: { ...profile, batch: 'B4' }, status: 422 });
    const updated = await request('/api/v1/profile', { method: 'PUT', token, data: profile });
    for (const [key, value] of Object.entries(profile)) assert.equal(updated[key], value);
    assert.equal((await request('/api/v1/profile', { token })).batch, 'B2');
    await request('/api/v1/auth/register', { method: 'POST', data: bob, status: 201 });
    bobToken = (await request('/api/v1/auth/login', { method: 'POST', data: bob })).access_token;
  });

  await t.test('class roster import is private, updatable and batch-aware', async () => {
    const imported = await request('/api/v1/class-roster/import', {
      method: 'POST', token, status: 201,
      data: { rows: [
        { pnr: '20260001001', display_name: 'Alice Student', email: alice.email, roll_number: '042', batch: 'B2' },
        { pnr: '20260001002', display_name: 'Bob Student', email: bob.email, roll_number: '043', batch: 'B2' },
        { pnr: '20260001003', display_name: 'Charlie Student', roll_number: '044', batch: 'B1' },
      ] },
    });
    assert.equal(imported.imported, 3);
    assert.equal(imported.updated, 0);
    assert.equal(imported.accounts_created, 1);
    assert.equal(imported.accounts_updated, 2);
    assert.ok((await request('/api/v1/auth/login', { method: 'POST', data: { identifier: '20260001003', password: '20260001003' } })).access_token);
    assert.deepEqual(imported.summary.batches, { B1: 1, B2: 2, B3: 0, unknown: 0 });
    const summary = await request('/api/v1/class-roster/summary', { token });
    assert.equal(summary.total, 3);
    assert.equal(summary.owner, true);
    const roster = await request('/api/v1/class-roster', { token });
    assert.equal(roster.length, 3);
    assert.equal(roster[0].pnr, '20260001001');

    const updated = await request('/api/v1/class-roster/import', {
      method: 'POST', token, status: 201,
      data: { rows: [{ pnr: '20260001003', display_name: 'Charlie Updated', roll_number: '044', batch: 'B3' }] },
    });
    assert.equal(updated.imported, 0);
    assert.equal(updated.updated, 1);
    assert.equal((await request('/api/v1/class-roster/summary', { token })).batches.B3, 1);

    await request('/api/v1/class-roster/import', {
      method: 'POST', token, status: 422,
      data: { rows: [{ pnr: '20260001004', display_name: '' }, { pnr: '20260001004', display_name: 'Duplicate' }] },
    });
    assert.equal((await request('/api/v1/class-roster/summary', { token })).total, 3);

    await request('/api/v1/profile', { method: 'PUT', token: bobToken, data: { display_name: 'Bob Student', prn: '20260001002', roll_number: '043', batch: 'B2' } });
    assert.ok((await request('/api/v1/auth/login', { method: 'POST', data: { identifier: '20260001002', password: bob.password } })).access_token);
    const bobMatch = await request('/api/v1/class-roster/me', { token: bobToken });
    assert.equal(bobMatch.display_name, 'Bob Student');
    assert.equal(bobMatch.pnr, '20260001002');
    await request('/api/v1/class-roster', { token: bobToken, status: 403 });
    assert.equal((await request('/api/v1/class-roster/summary', { token: bobToken })).owner, false);
  });

  await t.test('activity events are recorded safely and remain private', async () => {
    const created = await request('/api/v1/activity/events', {
      method: 'POST', token, status: 201,
      data: { event_type: 'click', view: 'dashboard', target: 'start-study', metadata: { course_code: 'IC2301', secret: 'do-not-store' } },
    });
    assert.equal(created.event_type, 'click');
    assert.equal(created.target, 'start-study');
    assert.deepEqual(created.metadata, { course_code: 'IC2301', source: 'client' });
    await request('/api/v1/activity/events', {
      method: 'POST', token, data: { event_type: 'not-supported', target: 'x' }, status: 422,
    });
    const events = await request('/api/v1/activity/events', { token });
    assert.ok(events.length > 1);
    assert.equal(events[0].id, created.id);
    assert.ok(!(await request('/api/v1/activity/events', { token: bobToken })).some(event => event.id === created.id));
    await request('/api/v1/activity/events?limit=NaN', { token, status: 422 });
    await request('/api/v1/activity/events?limit=1.5', { token, status: 422 });
    await request('/api/v1/activity/events', { method: 'POST', token, status: 422, data: { event_type: 'click', view: 'notes', target: 'secret@example.test' } });
    await request('/api/v1/activity/events', { method: 'POST', token, status: 422, data: { event_type: 'note_create', view: 'notes', target: 'saveNewNote' } });
    await request('/api/v1/activity/preferences', { method: 'PUT', token, data: { capture_clicks: false } });
    assert.equal((await request('/api/v1/activity/events', { method: 'POST', token, data: { event_type: 'click', view: 'notes', target: 'saveNewNote' } })).accepted, 0);
    assert.equal((await request('/api/v1/activity/preferences', { token: bobToken })).capture_clicks, true);
    await request('/api/v1/activity/preferences', { method: 'PUT', token, data: { capture_clicks: true } });
  });

  await t.test('class catalog, topic completion and server-graded quiz results persist privately', async () => {
    await request('/api/v1/catalog', { status: 401 });
    const catalog = await request('/api/v1/catalog', { token });
    assert.equal(catalog.courses.length, 7);
    assert.equal(catalog.timetable.length, catalogSeed.timetable.length);
    assert.equal(catalog.milestones.length, 6);
    assert.ok(!catalog.courses.some(course => /control systems/i.test(course.name)));
    assert.deepEqual(catalog, await request('/api/v1/catalog', { token: bobToken }));
    assert.equal((await request('/api/v1/progress', { token })).stats.topic_coverage, 0);
    await request('/api/v1/progress/topics', { method: 'PUT', token, status: 422, data: { course_id: 'sat', unit_index: 999, topic_index: 0, completed: true } });
    const progress = await request('/api/v1/progress/topics', { method: 'PUT', token, data: { course_id: 'sat', unit_index: 0, topic_index: 0, completed: true } });
    assert.equal(progress.courses.find(course => course.course_id === 'sat').completed, 1);
    assert.equal((await request('/api/v1/progress', { token: bobToken })).topics.length, 0);
    const quiz = { id: 'abc12300-0000-4000-8000-000000000001', course_id: 'sat', answers: [1, 0], score: 999 };
    const saved = await request('/api/v1/quizzes/attempts', { method: 'POST', token, status: 201, data: quiz });
    assert.equal(saved.score, 2);
    assert.equal(saved.total, 2);
    await request('/api/v1/quizzes/attempts', { method: 'POST', token, data: quiz });
    assert.equal((await request('/api/v1/progress', { token })).quizzes.length, 1);
    await request('/api/v1/quizzes/attempts', { method: 'POST', token: bobToken, status: 409, data: quiz });
    assert.equal((await request('/api/v1/progress', { token: bobToken })).quizzes.length, 0);
    await request('/api/v1/quizzes/attempts', { method: 'POST', token, status: 422, data: { ...quiz, answers: [42] } });
  });

  await t.test('notes can be saved, filtered and deleted', async () => {
    const note = await request('/api/v1/notes', {
      method: 'POST', token, status: 201,
      data: { course_code: 'TEST101', topic: 'Database persistence', title: "What's next?", content: 'Keep this note after restart.' },
    });
    noteId = note.id;
    assert.equal((await request('/api/v1/notes?course_code=TEST101', { token }))[0].title, "What's next?");
    assert.deepEqual(await request('/api/v1/notes?course_code=OTHER', { token }), []);
    const temporary = await request('/api/v1/notes', {
      method: 'POST', token, status: 201,
      data: { course_code: 'TEMP', topic: 'Temporary', title: 'Delete me', content: 'Test fixture only.' },
    });
    await request(`/api/v1/notes/${temporary.id}`, { method: 'DELETE', token, status: 204 });
    await request(`/api/v1/notes/${temporary.id}`, { method: 'DELETE', token, status: 404 });
    assert.equal((await request('/api/v1/notes', { token })).length, 1);
  });

  await t.test('assignments can be created and toggled in both directions', async () => {
    const assignment = await request('/api/v1/assignments', {
      method: 'POST', token, status: 201,
      data: { course_code: 'TEST101', title: 'Verify persistence', priority: 'high', due_at: '2026-10-01T12:00:00.000Z' },
    });
    assignmentId = assignment.id;
    assert.equal(assignment.status, 'pending');
    assert.equal((await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token })).status, 'completed');
    assert.equal((await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token })).status, 'pending');
    assert.equal((await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token })).status, 'completed');
  });

  await t.test('two concurrent assignment toggles both take effect', async () => {
    // Begin pending so exactly two toggles must restore pending, even when the
    // database processes the requests concurrently.
    assert.equal((await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token })).status, 'pending');
    const results = await Promise.all([
      request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token }),
      request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token }),
    ]);
    assert.deepEqual(results.map(result => result.status).sort(), ['completed', 'pending']);
    assert.equal((await request('/api/v1/assignments', { token }))[0].status, 'pending');
    await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token: bobToken, status: 404 });
    assert.equal((await request('/api/v1/assignments', { token }))[0].status, 'pending');
    assert.equal((await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token })).status, 'completed');
  });

  await t.test('study session heartbeat, pause, resume, completion and history', async () => {
    const session = await request('/api/v1/sessions/start', {
      method: 'POST', token, status: 201, data: { course_code: 'TEST101', topic: 'Transactions' },
    });
    sessionId = session.id;
    assert.equal(session.state, 'active');
    assert.equal((await request('/api/v1/sessions/active', { token })).id, session.id);
    assert.equal((await request('/api/v1/sessions/active', { token })).target_seconds, 2700);
    assert.equal(await request('/api/v1/sessions/active', { token: bobToken }), null);
    assert.ok((await request(`/api/v1/sessions/${sessionId}/heartbeat`, { method: 'POST', token })).last_heartbeat_at);
    assert.equal((await request(`/api/v1/sessions/${sessionId}/pause`, { method: 'POST', token })).state, 'paused');
    assert.equal((await request(`/api/v1/sessions/${sessionId}/resume`, { method: 'POST', token })).state, 'active');
    await request(`/api/v1/sessions/${sessionId}/complete`, { method: 'POST', token, data: { focus_rating: 6 }, status: 422 });
    const completed = await request(`/api/v1/sessions/${sessionId}/complete`, {
      method: 'POST', token, data: { focus_rating: 4, reflection: 'I understand persistence.' },
    });
    assert.equal(completed.state, 'completed');
    assert.equal(completed.focus_rating, 4);
    assert.equal(completed.reflection, 'I understand persistence.');
    assert.equal(typeof completed.duration_seconds, 'number');
    assert.ok(completed.duration_seconds >= 0);
    const retried = await request(`/api/v1/sessions/${sessionId}/complete`, { method: 'POST', token, data: { focus_rating: 1 } });
    assert.equal(retried.focus_rating, 4);
    assert.equal(await request('/api/v1/sessions/active', { token }), null);
    assert.equal((await request('/api/v1/sessions/history', { token }))[0].id, sessionId);
    assert.equal(typeof (await request('/api/v1/dashboard/overview', { token })).stats.total_study_minutes, 'number');
  });

  await t.test('course enrollments update without duplicate records', async () => {
    await request('/api/v1/enrollments', {
      method: 'POST', token, status: 201, data: { course_code: 'TEST101', course_name: 'Original name', term: '2026-I' },
    });
    await request('/api/v1/enrollments', {
      method: 'POST', token, status: 201, data: { course_code: 'TEST101', course_name: 'Database Systems', term: '2026-I' },
    });
    const rows = await request('/api/v1/enrollments', { token });
    assert.equal(rows.length, 1);
    assert.equal(rows[0].course_name, 'Database Systems');
  });

  await t.test('a second account cannot read or change the first account data', async () => {
    for (const route of ['/notes', '/assignments', '/sessions/history', '/enrollments']) {
      assert.deepEqual(await request(`/api/v1${route}`, { token: bobToken }), []);
    }
    assert.notEqual((await request('/api/v1/auth/me', { token: bobToken })).id, aliceId);
    await request(`/api/v1/notes/${noteId}`, { method: 'DELETE', token: bobToken, status: 404 });
    await request(`/api/v1/assignments/${assignmentId}/toggle`, { method: 'PATCH', token: bobToken, status: 404 });
    await request(`/api/v1/sessions/${sessionId}/complete`, { method: 'POST', token: bobToken, data: { focus_rating: 1 }, status: 404 });
  });

  await t.test('saved data and existing bearer tokens survive process restart', async () => {
    await server.stop();
    server = await startServer(sqlitePath);
    const profile = await request('/api/v1/auth/me', { token });
    assert.equal(profile.id, aliceId);
    assert.equal(profile.prn, '20260001001');
    assert.equal(profile.roll_number, '042');
    assert.equal(profile.batch, 'B2');
    assert.equal((await request('/api/v1/notes', { token }))[0].id, noteId);
    assert.equal((await request('/api/v1/assignments', { token }))[0].status, 'completed');
    const session = (await request('/api/v1/sessions/history', { token }))[0];
    assert.equal(session.id, sessionId);
    assert.equal(session.reflection, 'I understand persistence.');
    assert.equal((await request('/api/v1/enrollments', { token }))[0].course_name, 'Database Systems');
    assert.ok((await request('/api/v1/activity/events', { token })).some(event => event.event_type === 'click'));
    assert.equal((await request('/api/v1/catalog', { token })).timetable.length, catalogSeed.timetable.length);
    const progress = await request('/api/v1/progress', { token });
    assert.equal(progress.courses.find(course => course.course_id === 'sat').completed, 1);
    assert.equal(progress.quizzes[0].score, 2);
    assert.equal(progress.stats.completed_sessions, 1);
    assert.deepEqual(await request('/api/v1/notes', { token: bobToken }), []);
    assert.ok((await request('/api/v1/auth/login', { method: 'POST', data: alice })).access_token);
  });
});

test('Render refuses startup without a PostgreSQL DATABASE_URL', { timeout: 5000 }, async t => {
  const directory = await mkdtemp(join(tmpdir(), 'flux-one-render-guard-test-'));
  const server = launchServer({ RENDER: 'true', PORT: '0', SQLITE_PATH: join(directory, 'must-not-use.db') });
  t.after(async () => {
    await server.stop();
    await rm(directory, { recursive: true, force: true });
  });
  const result = await Promise.race([
    server.exited,
    delay(3000).then(() => { throw new Error('Render unexpectedly started without DATABASE_URL.'); }),
  ]);
  assert.equal(result.error, undefined);
  assert.notEqual(result.code, 0);
  assert.match(server.output, /DATABASE_URL/);
});
