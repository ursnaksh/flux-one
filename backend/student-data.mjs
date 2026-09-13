import { randomUUID } from 'node:crypto';
import { catalogSeed } from './catalog.mjs';

export const clientActions = new Set([
  'start-study', 'switchView', 'openSubjectWorkspace', 'backToSubjectsList', 'startQuickStudy',
  'startStudySession', 'pauseStudySession', 'resumeStudySession', 'setStudyDuration',
  'openSessionReflection', 'closeSessionReflection', 'setReflectionRating', 'saveCompletedStudySession',
  'setAssignmentFilter', 'toggleAssignment', 'openAssignmentModal', 'closeAssignmentModal', 'saveAssignment',
  'openNewNoteModal', 'closeNewNoteModal', 'saveNewNote', 'deleteNote', 'populateModalNoteTopics',
  'populateStudyTopics', 'selectStudyTopic', 'setTimetableDay', 'renderTimetableFull',
  'launchQuiz', 'generateFlightBriefing', 'generateAiQuiz', 'handleQuizAnswer', 'nextQuizQuestion', 'closeQuizModal', 'openCalendarModal', 'closeCalendarModal',
  'openStudentProfileModal', 'closeStudentProfileModal', 'saveStudentProfile', 'handleLogout',
  'handleRosterFile', 'importClassRoster', 'loadActivityEvents', 'toggleActivityCapture', 'toggleTopic', 'retrySync',
  'selectAssignmentCourse', 'selectAssignmentPriority', 'selectProfileBatch'
]);
const views = new Set(['dashboard', 'subjects', 'study', 'assignments', 'notes', 'timetable', 'roster', 'activity', 'brain']);
const isoNow = () => new Date().toISOString();

export async function initializeStudentData(db) {
  await db.exec(`
    CREATE TABLE IF NOT EXISTS academic_catalog (id TEXT PRIMARY KEY, version INTEGER NOT NULL, payload TEXT NOT NULL, updated_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS student_preferences (
      user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
      capture_clicks INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS topic_progress (
      user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      course_id TEXT NOT NULL, unit_index INTEGER NOT NULL, topic_index INTEGER NOT NULL,
      completed INTEGER NOT NULL, updated_at TEXT NOT NULL,
      PRIMARY KEY(user_id, course_id, unit_index, topic_index)
    );
    CREATE TABLE IF NOT EXISTS quiz_attempts (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      course_id TEXT NOT NULL, answers TEXT NOT NULL, score INTEGER NOT NULL,
      total INTEGER NOT NULL, created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_quiz_user_created ON quiz_attempts(user_id, created_at DESC);
    CREATE TABLE IF NOT EXISTS study_session_plans (
      session_id TEXT PRIMARY KEY REFERENCES study_sessions(id) ON DELETE CASCADE,
      target_seconds INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ai_cache (
      cache_key TEXT PRIMARY KEY, kind TEXT NOT NULL, model TEXT NOT NULL,
      response_json TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ai_cache_expiry ON ai_cache(expires_at);
    CREATE TABLE IF NOT EXISTS ai_quiz_attempts (
      id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
      cache_key TEXT NOT NULL, course_id TEXT NOT NULL, answers TEXT NOT NULL,
      score INTEGER NOT NULL, total INTEGER NOT NULL, created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_ai_quiz_user_created ON ai_quiz_attempts(user_id, created_at DESC);
  `);
  await db.prepare(`INSERT INTO academic_catalog (id,version,payload,updated_at) VALUES (?,?,?,?)
    ON CONFLICT(id) DO UPDATE SET version = excluded.version, payload = excluded.payload, updated_at = excluded.updated_at
    WHERE academic_catalog.version < excluded.version`).run(catalogSeed.id, catalogSeed.version, JSON.stringify(catalogSeed), isoNow());
}

export async function getCatalog(db) {
  return JSON.parse((await db.prepare('SELECT payload FROM academic_catalog WHERE id = ?').get(catalogSeed.id)).payload);
}

export async function recordActivity(db, userId, eventType, target, view = null, metadata = {}) {
  const event = { id: randomUUID(), event_type: eventType, view, target, metadata, created_at: isoNow() };
  await db.prepare('INSERT INTO activity_events (id,user_id,event_type,view_name,target,metadata,created_at) VALUES (?,?,?,?,?,?,?)')
    .run(event.id, userId, eventType, view, target, JSON.stringify(metadata), event.created_at);
  // Bound storage per account while keeping its latest history through redeploys.
  await db.prepare(`DELETE FROM activity_events WHERE user_id = ? AND id NOT IN
    (SELECT id FROM activity_events WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT 5000)`).run(userId, userId);
  return event;
}

export async function getProgress(db, userId) {
  const [catalog, topics, quizzes, aiQuizzes, sessions, assignments] = await Promise.all([
    getCatalog(db), db.prepare('SELECT * FROM topic_progress WHERE user_id = ?').all(userId),
    db.prepare('SELECT id,course_id,score,total,created_at FROM quiz_attempts WHERE user_id = ? ORDER BY created_at DESC').all(userId),
    db.prepare('SELECT id,course_id,score,total,created_at FROM ai_quiz_attempts WHERE user_id = ? ORDER BY created_at DESC').all(userId),
    db.prepare("SELECT * FROM study_sessions WHERE user_id = ? AND state = 'completed'").all(userId),
    db.prepare('SELECT status FROM assignments WHERE user_id = ?').all(userId)
  ]);
  const courseProgress = catalog.courses.map(course => {
    const total = course.units.reduce((sum, unit) => sum + unit.topics.length, 0);
    const completed = topics.filter(t => t.course_id === course.id && Number(t.completed) === 1 && course.units[t.unit_index]?.topics[t.topic_index]).length;
    return { course_id: course.id, completed, total, percent: total ? Math.round(completed / total * 100) : 0 };
  });
  const totalTopics = courseProgress.reduce((sum, course) => sum + course.total, 0);
  const completedTopics = courseProgress.reduce((sum, course) => sum + course.completed, 0);
  const dayKey = date => new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit' }).format(date);
  const activeDays = new Set(sessions.map(session => dayKey(new Date(session.completed_at))));
  const today = new Date();
  let streak = 0;
  const cursor = new Date(today);
  if (!activeDays.has(dayKey(cursor))) cursor.setUTCDate(cursor.getUTCDate() - 1);
  while (activeDays.has(dayKey(cursor))) { streak += 1; cursor.setUTCDate(cursor.getUTCDate() - 1); }
  let weekDays = 0;
  for (let i = 0; i < 7; i += 1) { const day = new Date(today); day.setUTCDate(day.getUTCDate() - i); if (activeDays.has(dayKey(day))) weekDays += 1; }
  const coverage = totalTopics ? Math.round(completedTopics / totalTopics * 100) : 0;
  const quizRows = [...quizzes, ...aiQuizzes].sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
  const quizTotal = quizRows.reduce((sum, quiz) => sum + Number(quiz.total), 0);
  return {
    topics: topics.map(topic => ({ course_id: topic.course_id, unit_index: Number(topic.unit_index), topic_index: Number(topic.topic_index), completed: Boolean(Number(topic.completed)) })),
    courses: courseProgress, quizzes: quizRows,
    stats: {
      total_study_minutes: Math.round(sessions.reduce((sum, session) => sum + Number(session.duration_seconds || 0), 0) / 60),
      completed_sessions: sessions.length, streak_days: streak, active_days_this_week: weekDays,
      academic_brain_score: coverage, topic_coverage: coverage, consistency: Math.round(weekDays / 7 * 100),
      focus_quality: sessions.length ? Math.round(sessions.reduce((sum, session) => sum + Number(session.focus_rating || 0), 0) / sessions.length / 5 * 100) : 0,
      assignment_completion: assignments.length ? Math.round(assignments.filter(a => a.status === 'completed').length / assignments.length * 100) : 0,
      quiz_average: quizTotal ? Math.round(quizRows.reduce((sum, quiz) => sum + Number(quiz.score), 0) / quizTotal * 100) : null
    }
  };
}

export async function handleStudentData({ req, res, url, user, db, body, send, fail }) {
  const route = url.pathname;
  if (route === '/api/v1/catalog' && req.method === 'GET') return send(res, 200, { ...await getCatalog(db), client_actions: [...clientActions] });
  if (route === '/api/v1/progress' && req.method === 'GET') return send(res, 200, await getProgress(db, user.id));
  if (route === '/api/v1/progress/topics' && req.method === 'PUT') {
    const data = await body(req); const catalog = await getCatalog(db);
    const course = catalog.courses.find(course => course.id === data.course_id);
    if (!Number.isInteger(data.unit_index) || !Number.isInteger(data.topic_index) || !course?.units[data.unit_index]?.topics[data.topic_index] || typeof data.completed !== 'boolean') return fail(res, 422, 'Choose a valid course topic and completion status.');
    await db.prepare(`INSERT INTO topic_progress (user_id,course_id,unit_index,topic_index,completed,updated_at) VALUES (?,?,?,?,?,?)
      ON CONFLICT(user_id,course_id,unit_index,topic_index) DO UPDATE SET completed = excluded.completed, updated_at = excluded.updated_at`)
      .run(user.id, course.id, data.unit_index, data.topic_index, data.completed ? 1 : 0, isoNow());
    await recordActivity(db, user.id, 'topic_update', data.completed ? 'Topic marked complete' : 'Topic marked incomplete', 'subjects', { source: 'server', course_code: course.code });
    return send(res, 200, await getProgress(db, user.id));
  }
  if (route === '/api/v1/quizzes/attempts' && req.method === 'POST') {
    const data = await body(req); const catalog = await getCatalog(db);
    const questions = catalog.quizzes[data.course_id];
    if (typeof data.id !== 'string' || !/^[0-9a-f-]{36}$/i.test(data.id) || !questions?.length || !Array.isArray(data.answers) || data.answers.length !== questions.length || data.answers.some((answer, index) => !Number.isInteger(answer) || answer < 0 || answer >= questions[index].options.length)) return fail(res, 422, 'Provide one valid answer per question and an attempt ID.');
    const score = data.answers.reduce((sum, answer, index) => sum + (answer === questions[index].ans ? 1 : 0), 0);
    const result = await db.prepare('INSERT INTO quiz_attempts (id,user_id,course_id,answers,score,total,created_at) VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO NOTHING')
      .run(data.id, user.id, data.course_id, JSON.stringify(data.answers), score, questions.length, isoNow());
    const saved = await db.prepare('SELECT id,course_id,score,total,created_at FROM quiz_attempts WHERE id = ? AND user_id = ?').get(data.id, user.id);
    if (!saved || saved.course_id !== data.course_id) return fail(res, 409, 'That attempt ID is already in use.');
    if (result.changes) await recordActivity(db, user.id, 'quiz_complete', 'Practice quiz completed', 'subjects', { source: 'server', course_code: catalog.courses.find(c => c.id === data.course_id)?.code });
    return send(res, result.changes ? 201 : 200, saved);
  }
  if (route === '/api/v1/activity/preferences') {
    if (req.method === 'GET') {
      const saved = await db.prepare('SELECT capture_clicks FROM student_preferences WHERE user_id = ?').get(user.id);
      return send(res, 200, { capture_clicks: saved ? Boolean(Number(saved.capture_clicks)) : true });
    }
    if (req.method === 'PUT') {
      const data = await body(req);
      if (typeof data.capture_clicks !== 'boolean') return fail(res, 422, 'Choose whether to record clicks.');
      await db.prepare('INSERT INTO student_preferences (user_id,capture_clicks) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET capture_clicks = excluded.capture_clicks').run(user.id, data.capture_clicks ? 1 : 0);
      return send(res, 200, { capture_clicks: data.capture_clicks });
    }
  }
  if (route === '/api/v1/activity/events') {
    if (req.method === 'GET') {
      const requested = Number(url.searchParams.get('limit') || 100);
      if (!Number.isInteger(requested) || requested < 1 || requested > 200) return fail(res, 422, 'Limit must be an integer from 1 to 200.');
      const rows = await db.prepare('SELECT * FROM activity_events WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?').all(user.id, requested);
      return send(res, 200, rows.map(row => ({ id: row.id, event_type: row.event_type, view: row.view_name, target: row.target, metadata: row.metadata ? JSON.parse(row.metadata) : null, created_at: row.created_at })));
    }
    if (req.method === 'POST') {
      const data = await body(req); const events = data.events || [data];
      if (!Array.isArray(events) || events.length < 1 || events.length > 50) return fail(res, 422, 'Send between 1 and 50 events.');
      if (events.some(event => !event || !['click', 'view', 'change'].includes(event.event_type) || !views.has(event.view) || !(event.event_type === 'view' ? views.has(event.target) : clientActions.has(event.target)))) return fail(res, 422, 'Unsupported activity event or action.');
      const pref = await db.prepare('SELECT capture_clicks FROM student_preferences WHERE user_id = ?').get(user.id);
      if (pref && !Number(pref.capture_clicks)) return send(res, 200, { accepted: 0 });
      const catalog = await getCatalog(db); const saved = [];
      for (const event of events) {
        const metadata = { source: 'client' };
        if (catalog.courses.some(course => course.code === event.metadata?.course_code)) metadata.course_code = event.metadata.course_code;
        saved.push(await recordActivity(db, user.id, event.event_type, event.target, event.view, metadata));
      }
      return send(res, 201, data.events ? { accepted: saved.length } : saved[0]);
    }
  }
  return fail(res, 405, 'Method not allowed.');
}
