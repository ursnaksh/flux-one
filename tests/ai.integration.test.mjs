import assert from 'node:assert/strict';
import test from 'node:test';
import { mkdtemp, rm } from 'node:fs/promises';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { openDatabase } from '../backend/database.mjs';
import { initializeStudentData } from '../backend/student-data.mjs';
import { catalogSeed } from '../backend/catalog.mjs';
import { generateDynamicQuiz, generateFlightBriefing, getAiStatus } from '../backend/ai.mjs';

function jsonResponse(value, status = 200) {
  return { ok: status >= 200 && status < 300, status, async json() { return value; } };
}

test('AI generation returns structured curriculum output and caches it', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'flux-one-ai-test-'));
  const db = await openDatabase(join(directory, 'ai.db'));
  await db.exec('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);');
  await initializeStudentData(db);
  const previousKey = process.env.GEMINI_API_KEY;
  const previousEndpoint = process.env.GEMINI_API_ENDPOINT;
  const previousFetch = globalThis.fetch;
  let calls = 0;
  process.env.GEMINI_API_KEY = 'test-key';
  process.env.GEMINI_API_ENDPOINT = 'https://example.test/interactions';
  globalThis.fetch = async (_url, options) => {
    calls += 1;
    const request = JSON.parse(options.body);
    assert.equal(request.model, 'gemini-3.6-flash');
    assert.equal(request.response_format[0].mime_type, 'application/json');
    assert.equal(request.response_format[0].schema.type, 'object');
    return jsonResponse({ steps: [{ type: 'model_output', content: [{ type: 'text', text: JSON.stringify({ title: 'LVDT Primer', hook: 'Connect displacement to differential voltage.', concepts: ['Null position', 'Differential output', 'Core movement'], check_question: 'Why does the null output cancel?', recommended_minutes: 3 }) }] }] });
  };
  try {
    assert.equal(getAiStatus().configured, true);
    const topic = catalogSeed.courses.find(course => course.id === 'sat').units[0].topics.find(value => value.includes('LVDT'));
    const first = await generateFlightBriefing({ db, catalog: catalogSeed, courseId: 'sat', topic });
    assert.equal(first.cached, false);
    const second = await generateFlightBriefing({ db, catalog: catalogSeed, courseId: 'sat', topic });
    assert.equal(second.cached, true);
    assert.equal(calls, 1);
    assert.equal((await db.prepare('SELECT COUNT(*) AS count FROM ai_cache').get()).count, 1);
  } finally {
    if (previousKey === undefined) delete process.env.GEMINI_API_KEY; else process.env.GEMINI_API_KEY = previousKey;
    if (previousEndpoint === undefined) delete process.env.GEMINI_API_ENDPOINT; else process.env.GEMINI_API_ENDPOINT = previousEndpoint;
    globalThis.fetch = previousFetch;
    await db.close();
    await rm(directory, { recursive: true, force: true });
  }
});

test('AI quiz validates inputs and preserves user-independent cache keys', async () => {
  const directory = await mkdtemp(join(tmpdir(), 'flux-one-ai-test-'));
  const db = await openDatabase(join(directory, 'ai.db'));
  await db.exec('CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY);');
  await initializeStudentData(db);
  const previousKey = process.env.GEMINI_API_KEY;
  const previousFetch = globalThis.fetch;
  process.env.GEMINI_API_KEY = 'test-key';
  globalThis.fetch = async () => jsonResponse({ steps: [{ type: 'model_output', content: [{ type: 'text', text: JSON.stringify({ title: '8051 Quiz', questions: [1, 2, 3, 4, 5].map((_, i) => ({ question: `Question ${i + 1}`, options: ['A', 'B', 'C', 'D'], answer_index: i % 4, explanation: 'Curriculum explanation.' })) }) }] }] });
  try {
    const quiz = await generateDynamicQuiz({ db, catalog: catalogSeed, courseId: 'maa', count: 5, difficulty: 'mixed' });
    assert.equal(quiz.questions.length, 5);
    await assert.rejects(() => generateDynamicQuiz({ db, catalog: catalogSeed, courseId: 'not-a-course' }), /valid course/);
    await assert.rejects(() => generateDynamicQuiz({ db, catalog: catalogSeed, courseId: 'maa', count: 2 }), /count/);
  } finally {
    if (previousKey === undefined) delete process.env.GEMINI_API_KEY; else process.env.GEMINI_API_KEY = previousKey;
    globalThis.fetch = previousFetch;
    await db.close();
    await rm(directory, { recursive: true, force: true });
  }
});

test('AI status uses a supported default and replaces known retired or invalid aliases', () => {
  const previousModel = process.env.GEMINI_MODEL;
  try {
    delete process.env.GEMINI_MODEL;
    assert.equal(getAiStatus().model, 'gemini-3.6-flash');
    process.env.GEMINI_MODEL = 'gemini-2.5-flash';
    assert.equal(getAiStatus().model, 'gemini-3.6-flash');
    process.env.GEMINI_MODEL = 'models/gemini-2.5-flash';
    assert.equal(getAiStatus().model, 'gemini-3.6-flash');
  } finally {
    if (previousModel === undefined) delete process.env.GEMINI_MODEL; else process.env.GEMINI_MODEL = previousModel;
  }
});

test('catalog matches every timetable course and identifies title-only syllabus mappings', () => {
  assert.equal(catalogSeed.version, 3);
  assert.equal(catalogSeed.courses.length, 7);
  assert.ok(catalogSeed.sources.syllabus.url.startsWith('https://www.vit.edu/'));
  const courseIds = new Set(catalogSeed.courses.map(course => course.id));
  for (const row of catalogSeed.timetable) assert.ok(courseIds.has(row.split('|')[7]), `Unknown timetable course in ${row}`);
  const designThinking = catalogSeed.courses.find(course => course.id === 'dt');
  assert.equal(designThinking.code, 'IC2311');
  assert.equal(designThinking.syllabus.source_course_code, 'IC2236');
  const microcontroller = catalogSeed.courses.find(course => course.id === 'maa');
  assert.equal(microcontroller.code, 'MM1408');
  assert.equal(microcontroller.syllabus.source_course_code, 'ICM002');
  assert.equal(catalogSeed.courses.some(course => /control systems|control theory/i.test(course.name)), false);
});
