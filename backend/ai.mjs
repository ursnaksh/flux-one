import { createHash } from 'node:crypto';

const DEFAULT_MODEL = 'gemini-2.5-flash-lite';
const DEFAULT_ENDPOINT = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent';
const MAX_PROMPT_LENGTH = 12000;
const INVALID_MODEL_ALIASES = new Set([
  'gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-2.0-flash',
  // This name was accidentally deployed even though it is not a Gemini API model.
  'gemini-3.6-flash'
]);

export class AiInputError extends Error { constructor(message) { super(message); this.name = 'AiInputError'; } }
export class AiConfigurationError extends Error { constructor(message) { super(message); this.name = 'AiConfigurationError'; } }
export class AiProviderError extends Error { constructor(message) { super(message); this.name = 'AiProviderError'; } }
export class AiOutputError extends Error { constructor(message) { super(message); this.name = 'AiOutputError'; } }

function modelName() {
  const configured = String(process.env.GEMINI_MODEL || '').trim().replace(/^models\//, '');
  if (!configured || INVALID_MODEL_ALIASES.has(configured)) return DEFAULT_MODEL;
  return configured;
}

const apiKey = () => String(process.env.GEMINI_API_KEY || '').trim();

export function getAiStatus() {
  return {
    provider: 'Google Gemini',
    model: modelName(),
    configured: Boolean(apiKey()),
    cache: 'database'
  };
}

function slug(value) {
  return String(value || '').trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 100) || 'general';
}

function courseContext(catalog, courseId, topic) {
  const course = catalog.courses.find(item => item.id === courseId);
  if (!course) throw new AiInputError('Choose a valid course from the academic catalog.');
  const allTopics = course.units.flatMap((unit, unitIndex) => unit.topics.map((name, topicIndex) => ({ name, unit: unit.name, unitIndex, topicIndex })));
  const selected = topic ? allTopics.find(item => item.name.toLowerCase() === String(topic).trim().toLowerCase()) : null;
  if (topic && !selected) throw new AiInputError('Choose a valid topic from that course.');
  return { course, allTopics, selected };
}

function semesterWeek() {
  const semesterStart = Date.parse('2026-08-24T00:00:00+05:30');
  const current = Date.now();
  return Math.max(1, Math.floor((current - semesterStart) / (7 * 24 * 60 * 60 * 1000)) + 1);
}

function schemaFor(kind) {
  if (kind === 'flight_briefing') return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      hook: { type: 'string' },
      concepts: { type: 'array', items: { type: 'string' }, minItems: 3, maxItems: 6 },
      check_question: { type: 'string' },
      recommended_minutes: { type: 'integer', minimum: 2, maximum: 5 }
    },
    required: ['title', 'hook', 'concepts', 'check_question', 'recommended_minutes']
  };
  if (kind === 'topic_explain') return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      mode: { type: 'string' },
      overview: { type: 'string' },
      key_points: { type: 'array', items: { type: 'string' }, minItems: 3, maxItems: 6 },
      engineering_application: { type: 'string' },
      exam_tip: { type: 'string' },
      check_question: { type: 'string' }
    },
    required: ['title', 'mode', 'overview', 'key_points', 'engineering_application', 'exam_tip', 'check_question']
  };
  if (kind === 'post_lecture') return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      recap: { type: 'string' },
      core_takeaways: { type: 'array', items: { type: 'string' }, minItems: 3, maxItems: 5 },
      check_questions: {
        type: 'array', minItems: 2, maxItems: 3,
        items: {
          type: 'object',
          properties: {
            question: { type: 'string' },
            expected_answer: { type: 'string' },
            why_important: { type: 'string' }
          },
          required: ['question', 'expected_answer', 'why_important']
        }
      }
    },
    required: ['title', 'recap', 'core_takeaways', 'check_questions']
  };
  if (kind === 'viva_mock') return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      lab_context: { type: 'string' },
      questions: {
        type: 'array', minItems: 3, maxItems: 4,
        items: {
          type: 'object',
          properties: {
            question: { type: 'string' },
            model_answer: { type: 'string' },
            examiner_tip: { type: 'string' }
          },
          required: ['question', 'model_answer', 'examiner_tip']
        }
      }
    },
    required: ['title', 'lab_context', 'questions']
  };
  return {
    type: 'object',
    properties: {
      title: { type: 'string' },
      questions: {
        type: 'array', minItems: 3, maxItems: 8,
        items: {
          type: 'object',
          properties: {
            question: { type: 'string' },
            options: { type: 'array', items: { type: 'string' }, minItems: 4, maxItems: 4 },
            answer_index: { type: 'integer', minimum: 0, maximum: 3 },
            explanation: { type: 'string' }
          },
          required: ['question', 'options', 'answer_index', 'explanation']
        }
      }
    },
    required: ['title', 'questions']
  };
}

function normalizeJsonText(text) {
  const trimmed = String(text || '').trim();
  const fenced = trimmed.match(/^```(?:json)?\s*([\s\S]*?)\s*```$/i);
  return (fenced ? fenced[1] : trimmed).trim();
}

function assertString(value, label, max = 1500) {
  if (typeof value !== 'string' || !value.trim() || value.length > max) throw new AiOutputError(`Gemini returned an invalid ${label}.`);
  return value.trim();
}

function validateOutput(kind, value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new AiOutputError('Gemini returned an invalid JSON object.');
  
  if (kind === 'flight_briefing') {
    const concepts = value.concepts;
    if (!Array.isArray(concepts) || concepts.length < 3 || concepts.length > 6) throw new AiOutputError('Gemini returned an invalid concept list.');
    return {
      title: assertString(value.title, 'briefing title', 180),
      hook: assertString(value.hook, 'briefing hook', 1200),
      concepts: concepts.map(concept => assertString(concept, 'briefing concept', 350)),
      check_question: assertString(value.check_question, 'check question', 600),
      recommended_minutes: Number.isInteger(value.recommended_minutes) ? Math.min(5, Math.max(2, value.recommended_minutes)) : 3
    };
  }

  if (kind === 'topic_explain') {
    const pts = value.key_points;
    if (!Array.isArray(pts) || pts.length < 3 || pts.length > 6) throw new AiOutputError('Gemini returned invalid explanation points.');
    return {
      title: assertString(value.title, 'topic title', 180),
      mode: String(value.mode || 'deep'),
      overview: assertString(value.overview, 'overview', 1500),
      key_points: pts.map(p => assertString(p, 'key point', 400)),
      engineering_application: assertString(value.engineering_application, 'application', 1000),
      exam_tip: assertString(value.exam_tip, 'exam tip', 800),
      check_question: assertString(value.check_question, 'check question', 600)
    };
  }

  if (kind === 'post_lecture') {
    const takeaways = value.core_takeaways;
    if (!Array.isArray(takeaways) || takeaways.length < 3) throw new AiOutputError('Gemini returned invalid takeaways.');
    const qList = value.check_questions;
    if (!Array.isArray(qList) || qList.length < 2) throw new AiOutputError('Gemini returned invalid check questions.');
    return {
      title: assertString(value.title, 'debrief title', 180),
      recap: assertString(value.recap, 'recap', 1200),
      core_takeaways: takeaways.map(t => assertString(t, 'takeaway', 350)),
      check_questions: qList.map(q => ({
        question: assertString(q.question, 'question', 400),
        expected_answer: assertString(q.expected_answer, 'answer', 500),
        why_important: assertString(q.why_important, 'importance', 400)
      }))
    };
  }

  if (kind === 'viva_mock') {
    const qList = value.questions;
    if (!Array.isArray(qList) || qList.length < 3) throw new AiOutputError('Gemini returned invalid viva questions.');
    return {
      title: assertString(value.title, 'viva title', 180),
      lab_context: assertString(value.lab_context, 'lab context', 1000),
      questions: qList.map(q => ({
        question: assertString(q.question, 'viva question', 400),
        model_answer: assertString(q.model_answer, 'viva answer', 600),
        examiner_tip: assertString(q.examiner_tip, 'examiner tip', 400)
      }))
    };
  }

  if (!Array.isArray(value.questions) || value.questions.length < 3 || value.questions.length > 8) throw new AiOutputError('Gemini returned an invalid quiz.');
  return {
    title: assertString(value.title, 'quiz title', 160),
    questions: value.questions.map(question => {
      if (!question || !Array.isArray(question.options) || question.options.length !== 4 || !Number.isInteger(question.answer_index) || question.answer_index < 0 || question.answer_index > 3) throw new AiOutputError('Gemini returned an invalid quiz question.');
      const options = question.options.map(option => assertString(option, 'quiz option', 240));
      if (new Set(options.map(option => option.toLowerCase())).size !== 4) throw new AiOutputError('Gemini returned duplicate quiz options.');
      return {
        question: assertString(question.question, 'quiz question', 600),
        options,
        answer_index: question.answer_index,
        explanation: assertString(question.explanation, 'quiz explanation', 600)
      };
    })
  };
}

async function callGemini({ prompt, kind }) {
  const key = apiKey();
  if (!key) throw new AiConfigurationError('AI is not configured yet. Add GEMINI_API_KEY to the server environment.');
  if (prompt.length > MAX_PROMPT_LENGTH) throw new AiInputError('The selected academic context is too large.');
  
  const targetModel = modelName();
  const endpointTemplate = String(process.env.GEMINI_API_ENDPOINT || DEFAULT_ENDPOINT).trim() || DEFAULT_ENDPOINT;
  const endpoint = endpointTemplate.replace('{model}', encodeURIComponent(targetModel));
  
  let response;
  try {
    response = await fetch(endpoint, {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'x-goog-api-key': key 
      },
      body: JSON.stringify({
        contents: [{ role: 'user', parts: [{ text: prompt }] }],
        generationConfig: {
          temperature: 0.25,
          responseMimeType: 'application/json',
          responseSchema: schemaFor(kind)
        }
      }),
      signal: AbortSignal.timeout(25000)
    });
  } catch (error) {
    if (error?.name === 'TimeoutError' || error?.name === 'AbortError') throw new AiProviderError('Gemini took too long to respond. Please retry.');
    throw new AiProviderError('Gemini could not be reached. Please retry.');
  }

  if (!response.ok) {
    const status = response.status;
    const errText = await response.text().catch(() => '');
    let providerMessage = '';
    try { providerMessage = JSON.parse(errText)?.error?.message || ''; } catch { /* Provider returned plain text. */ }
    console.error(`Gemini API error (${status}) on model [${targetModel}]: ${providerMessage || 'No provider detail'}`);

    if (status === 401 || status === 403) throw new AiConfigurationError('Gemini rejected the server key. Check GEMINI_API_KEY in Render.');
    if (status === 429) throw new AiProviderError('Gemini rate limit reached. Try again in a moment.');
    if (status === 404) throw new AiConfigurationError(`Gemini model ${targetModel} is unavailable. Remove an outdated GEMINI_MODEL setting in Render.`);
    throw new AiProviderError(`Gemini returned an upstream error (${status}).${providerMessage ? ` ${providerMessage}` : ''}`);
  }

  let payload;
  try { payload = await response.json(); } catch { throw new AiProviderError('Gemini returned an unreadable response.'); }
  const text = payload?.candidates?.[0]?.content?.parts?.map(part => part.text || '').join('').trim();
  if (!text) throw new AiOutputError('Gemini returned no generated content.');
  try { return validateOutput(kind, JSON.parse(normalizeJsonText(text))); }
  catch (error) { if (error instanceof AiOutputError) throw error; throw new AiOutputError('Gemini returned malformed JSON.'); }
}

async function fromCache(db, cacheKey, kind) {
  const row = await db.prepare('SELECT response_json, model, created_at, expires_at FROM ai_cache WHERE cache_key = ? AND kind = ? AND model = ? AND expires_at > ?').get(cacheKey, kind, modelName(), new Date().toISOString());
  if (!row) return null;
  try {
    return { ...validateOutput(kind, JSON.parse(row.response_json)), cache_key: cacheKey, model: row.model, generated_at: row.created_at, cached: true };
  } catch { return null; }
}

async function generateCached({ db, kind, cacheKey, prompt, ttlHours }) {
  const cached = await fromCache(db, cacheKey, kind);
  if (cached) return cached;
  const value = await callGemini({ prompt, kind });
  const createdAt = new Date().toISOString();
  const expiresAt = new Date(Date.now() + ttlHours * 60 * 60 * 1000).toISOString();
  await db.prepare('DELETE FROM ai_cache WHERE expires_at <= ?').run(createdAt);
  await db.prepare(`INSERT INTO ai_cache (cache_key,kind,model,response_json,created_at,expires_at) VALUES (?,?,?,?,?,?)
    ON CONFLICT(cache_key) DO UPDATE SET kind = excluded.kind, model = excluded.model, response_json = excluded.response_json, created_at = excluded.created_at, expires_at = excluded.expires_at`)
    .run(cacheKey, kind, modelName(), JSON.stringify(value), createdAt, expiresAt);
  return { ...value, cache_key: cacheKey, model: modelName(), generated_at: createdAt, cached: false };
}

export async function generateFlightBriefing({ db, catalog, courseId, topic, scheduledAt }) {
  const { course, allTopics, selected } = courseContext(catalog, courseId, topic);
  const focus = selected || allTopics[0];
  const week = semesterWeek();
  const schedule = catalog.timetable.filter(line => line.split('|')[7] === course.id || line.split('|')[0] === course.id).slice(0, 4).map(line => line.split('|').slice(0, 7).join(' | '));
  const when = scheduledAt ? new Date(scheduledAt) : null;
  if (scheduledAt && (!when || Number.isNaN(when.getTime()))) throw new AiInputError('scheduled_at must be a valid date.');
  const cacheKey = `ai:${catalog.id}:v${catalog.version}:flight:${slug(course.id)}:${slug(focus.name)}:w${week}`;
  const prompt = [
    'You are FLUX ONE, a concise academic copilot for engineering students at VIT Pune.',
    `Create a 3-minute pre-class briefing for ${course.name} (${course.code}).`,
    `Semester week: ${week}. Focus topic: ${focus.name}. Unit: ${focus.unit}.`,
    `Official curriculum topics: ${allTopics.map(item => item.name).join('; ')}.`,
    schedule.length ? `Known timetable context: ${schedule.join(' || ')}.` : '',
    when ? `Scheduled lecture time: ${when.toISOString()}.` : '',
    'Provide high-yield conceptual points covering principles, formulas, and industrial applications. Return JSON matching the requested schema. Keep the hook practical and the check question directly answerable.'
  ].filter(Boolean).join('\n');
  return generateCached({ db, kind: 'flight_briefing', cacheKey, prompt, ttlHours: 24 });
}

export async function generateTopicExplanation({ db, catalog, courseId, topic, mode = 'deep' }) {
  const { course, allTopics, selected } = courseContext(catalog, courseId, topic);
  const focus = selected || allTopics[0];
  const isDeep = mode === 'deep';
  const cacheKey = `ai:${catalog.id}:v${catalog.version}:topic:${slug(course.id)}:${slug(focus.name)}:${isDeep ? 'deep' : 'summary'}`;
  const prompt = [
    `You are FLUX ONE, an expert engineering faculty tutor for ${course.name} (${course.code}) at VIT Pune.`,
    `Deliver a ${isDeep ? 'comprehensive, structured Deep Dive' : 'rapid 5-point revision summary & formula sheet'} for the topic: "${focus.name}".`,
    `Syllabus Unit: ${focus.unit}.`,
    isDeep 
      ? 'In the overview, explain the core physics/algorithmic mechanics clearly. In key_points, give 4-5 rigorous engineering steps/principles with formulas where appropriate. Include industrial relevance (e.g. Forbes Marshall, Emerson, automotive, IoT) in engineering_application, common exam traps in exam_tip, and 1 conceptual check question.'
      : 'In overview, provide a 2-sentence executive summary. In key_points, provide 4-5 high-yield bullets with essential equations, definitions, and operating limits. Highlight the primary exam takeaway in exam_tip.',
    'Return strictly JSON matching the response schema.'
  ].join('\n');
  return generateCached({ db, kind: 'topic_explain', cacheKey, prompt, ttlHours: 30 * 24 });
}

export async function generatePostLectureDebrief({ db, catalog, courseId, topic, scheduledAt }) {
  const { course, allTopics, selected } = courseContext(catalog, courseId, topic);
  const focus = selected || allTopics[0];
  const when = scheduledAt ? new Date(scheduledAt) : new Date();
  const cacheKey = `ai:${catalog.id}:v${catalog.version}:debrief:${slug(course.id)}:${slug(focus.name)}`;
  const prompt = [
    'You are FLUX ONE, reviewing today’s completed engineering lecture.',
    `Course: ${course.name} (${course.code}). Topic covered: "${focus.name}" in ${focus.unit}.`,
    'Create an immediate post-lecture retention debrief.',
    '1. recap: A 2-sentence summary of what students should now understand from today’s class.',
    '2. core_takeaways: 3 to 4 essential concepts students must remember for exams.',
    '3. check_questions: 2 targeted conceptual check questions with expected_answer and why_important to verify if students truly grasped the lecture.',
    'Return JSON adhering to schema.'
  ].join('\n');
  return generateCached({ db, kind: 'post_lecture', cacheKey, prompt, ttlHours: 48 });
}

export async function generateVivaQuestions({ db, catalog, courseId, topic }) {
  const { course, allTopics, selected } = courseContext(catalog, courseId, topic);
  const focus = selected || allTopics[0];
  const cacheKey = `ai:${catalog.id}:v${catalog.version}:viva:${slug(course.id)}:${slug(focus.name)}`;
  const prompt = [
    `You are an external Comprehensive Viva Voce (CVV) examiner for ${course.name} (${course.code}) at VIT Pune.`,
    `Conduct a mock lab viva evaluation on the laboratory/theory topic: "${focus.name}".`,
    'Generate 3 top-tier viva questions commonly asked in practical exams.',
    'For each question, provide: question, model_answer (concise, precise answer that impresses the examiner), and examiner_tip (what pitfall to avoid or key keyword to say).',
    'Return valid JSON matching schema.'
  ].join('\n');
  return generateCached({ db, kind: 'viva_mock', cacheKey, prompt, ttlHours: 30 * 24 });
}

export async function generateDynamicQuiz({ db, catalog, courseId, topic, difficulty = 'mixed', count = 5 }) {
  const { course, allTopics, selected } = courseContext(catalog, courseId, topic);
  const amount = Number(count);
  if (!Number.isInteger(amount) || amount < 3 || amount > 8) throw new AiInputError('Quiz count must be an integer from 3 to 8.');
  const level = String(difficulty || 'mixed').trim().toLowerCase();
  if (!['easy', 'mixed', 'hard'].includes(level)) throw new AiInputError('Quiz difficulty must be easy, mixed, or hard.');
  const focusTopics = selected ? [selected] : allTopics.slice(0, 8);
  const cacheKey = `ai:${catalog.id}:v${catalog.version}:quiz:${slug(course.id)}:${slug(selected?.name || 'all')}:${level}:${amount}`;
  const prompt = [
    'You are FLUX ONE, an engineering-course quiz author at VIT Pune.',
    `Create ${amount} multiple-choice questions for ${course.name} (${course.code}).`,
    `Difficulty: ${level}. Focus topics: ${focusTopics.map(item => `${item.unit} — ${item.name}`).join('; ')}.`,
    'Each question must have exactly four distinct options, one unambiguous correct answer, and a short explanation. Use only the supplied curriculum and avoid topics from other courses. Return JSON matching the requested schema. Do not include markdown.'
  ].join('\n');
  return generateCached({ db, kind: 'quiz', cacheKey, prompt, ttlHours: 7 * 24 });
}

export function cacheKeyDigest(cacheKey) {
  return createHash('sha256').update(cacheKey).digest('hex');
}
