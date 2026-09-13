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
  process.env.GEMINI_API_ENDPOINT = 'https://example.test/models/{model}:generateContent';
  globalThis.fetch = async (_url, options) => {
    calls += 1;
    const request = JSON.parse(options.body);
    assert.equal(request.generationConfig.responseMimeType, 'application/json');
    assert.equal(request.generationConfig.responseSchema.type, 'object');
    return jsonResponse({ candidates: [{ content: { parts: [{ text: JSON.stringify({ title: 'LVDT Primer', hook: 'Connect displacement to differential voltage.', concepts: ['Null position', 'Differential output', 'Core movement'], check_question: 'Why does the null output cancel?', recommended_minutes: 3 }) }] } }] });
  };
  try {
    assert.equal(getAiStatus().configured, true);
    const first = await generateFlightBriefing({ db, catalog: catalogSeed, courseId: 'sat', topic: 'LVDT Operating Principle & Characteristics' });
    assert.equal(first.cached, false);
    const second = await generateFlightBriefing({ db, catalog: catalogSeed, courseId: 'sat', topic: 'LVDT Operating Principle & Characteristics' });
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
  globalThis.fetch = async () => jsonResponse({ candidates: [{ content: { parts: [{ text: JSON.stringify({ title: '8051 Quiz', questions: [1, 2, 3, 4, 5].map((_, i) => ({ question: `Question ${i + 1}`, options: ['A', 'B', 'C', 'D'], answer_index: i % 4, explanation: 'Curriculum explanation.' })) }) }] } }] });
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
