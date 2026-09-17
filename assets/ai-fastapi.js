(() => {
  let activeAiQuizAttempt = null;

  function escapeFluxAi(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[char]));
  }

  function resolveAiSubject(courseId) {
    const course = coursesData.find(item => item.id === courseId);
    if (!course) throw new Error('This subject is not available.');
    const enrolled = currentUser?.enrolled_subjects?.find(item => item.code === course.code);
    if (!enrolled?.id) {
      throw new Error('This subject is not linked to your active enrollment yet.');
    }
    return { course, subjectId: enrolled.id };
  }

  async function aiRequest(path, data) {
    const token = localStorage.getItem('flux_access_token');
    if (!token) throw new Error('Please sign in before using AI.');

    let response;
    try {
      response = await fetch(`${API_BASE}${path}`, {
        method: data === undefined ? 'GET' : 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: data === undefined ? undefined : JSON.stringify(data),
        signal: AbortSignal.timeout(30000)
      });
    } catch (error) {
      if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
        throw new Error('AI took too long to respond. Please retry.');
      }
      throw new Error('Could not reach the FLUX ONE AI service.');
    }

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.message || payload.detail || `AI request failed (${response.status}).`);
    }
    return payload;
  }

  function aiPanelMarkup(courseId) {
    return `
      <div id="flux-ai-subject-panel" class="glass-card p-5 rounded-3xl border border-cyan-500/25 bg-gradient-to-r from-cyan-950/20 via-slate-900 to-indigo-950/20">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div class="text-[10px] uppercase tracking-[0.18em] text-cyan-300 font-bold">FLUX AI · Gemini</div>
            <div class="text-sm font-bold text-white mt-1">Academic Copilot</div>
            <div class="text-[11px] text-slate-400 mt-1">Uses your verified enrolled subject. It will not guess the current lecture topic.</div>
          </div>
          <div class="flex flex-wrap gap-2">
            <button onclick="generateFluxAiBriefing('${courseId}')" class="px-4 py-2.5 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-200 border border-cyan-800 text-xs font-bold flex items-center gap-2">
              <i data-lucide="sparkles" class="w-4 h-4"></i> AI Briefing
            </button>
            <button onclick="generateFluxAiQuiz('${courseId}')" class="px-4 py-2.5 rounded-xl bg-indigo-950 hover:bg-indigo-900 text-indigo-200 border border-indigo-800 text-xs font-bold flex items-center gap-2">
              <i data-lucide="brain-circuit" class="w-4 h-4"></i> AI Quiz
            </button>
          </div>
        </div>
        <div id="flux-ai-subject-output" class="hidden mt-4"></div>
      </div>`;
  }

  function aiLauncherMarkup() {
    const options = coursesData.map(course =>
      `<option value="${escapeFluxAi(course.id)}">${escapeFluxAi(course.code)} · ${escapeFluxAi(course.name)}</option>`
    ).join('');

    return `
      <div id="flux-ai-list-panel" class="glass-card p-5 rounded-3xl border border-cyan-500/25 bg-gradient-to-r from-cyan-950/20 via-slate-900 to-indigo-950/20 mb-5">
        <div class="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-2">
              <div class="text-[10px] uppercase tracking-[0.18em] text-cyan-300 font-bold">FLUX AI · Gemini</div>
              <span id="flux-ai-status-badge" class="text-[9px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700">Checking…</span>
            </div>
            <div class="text-base font-black text-white mt-1">Academic Copilot</div>
            <div class="text-[11px] text-slate-400 mt-1">Choose a subject, then generate a verified briefing or a 5-question AI quiz.</div>
            <select id="flux-ai-course-select" class="mt-3 w-full max-w-xl bg-slate-950 border border-slate-700 focus:border-cyan-400 rounded-xl px-3 py-2.5 text-xs text-white focus:outline-none">
              ${options}
            </select>
          </div>
          <div class="flex flex-wrap gap-2 shrink-0">
            <button onclick="generateFluxAiBriefing(document.getElementById('flux-ai-course-select').value)" class="px-4 py-2.5 rounded-xl bg-cyan-950 hover:bg-cyan-900 text-cyan-200 border border-cyan-800 text-xs font-bold flex items-center gap-2">
              <i data-lucide="sparkles" class="w-4 h-4"></i> AI Briefing
            </button>
            <button onclick="generateFluxAiQuiz(document.getElementById('flux-ai-course-select').value)" class="px-4 py-2.5 rounded-xl bg-indigo-950 hover:bg-indigo-900 text-indigo-200 border border-indigo-800 text-xs font-bold flex items-center gap-2">
              <i data-lucide="brain-circuit" class="w-4 h-4"></i> AI Quiz
            </button>
          </div>
        </div>
        <div id="flux-ai-list-output" class="hidden mt-4"></div>
      </div>`;
  }

  function injectSubjectsAiLauncher() {
    const container = document.getElementById('subjects-list-container');
    if (!container || document.getElementById('flux-ai-list-panel')) return;

    const header = container.querySelector('.flex.items-center.justify-between.mb-5');
    if (header) header.insertAdjacentHTML('afterend', aiLauncherMarkup());
    else container.insertAdjacentHTML('afterbegin', aiLauncherMarkup());

    if (window.lucide) lucide.createIcons();
    void hydrateAiStatus();
  }

  function injectSubjectAiControls(courseId) {
    const workspace = document.getElementById('subject-workspace-container');
    if (!workspace || workspace.classList.contains('hidden')) return;
    document.getElementById('flux-ai-subject-panel')?.remove();
    const hero = workspace.querySelector('.glass-card');
    if (!hero) return;
    hero.insertAdjacentHTML('afterend', aiPanelMarkup(courseId));
    if (window.lucide) lucide.createIcons();
  }

  function currentAiOutput() {
    const workspace = document.getElementById('subject-workspace-container');
    if (workspace && !workspace.classList.contains('hidden')) {
      return document.getElementById('flux-ai-subject-output');
    }
    return document.getElementById('flux-ai-list-output') || document.getElementById('flux-ai-subject-output');
  }

  function setAiOutput(html, tone = 'normal') {
    const output = currentAiOutput();
    if (!output) return;
    output.classList.remove('hidden');
    output.className = tone === 'error'
      ? 'mt-4 p-4 rounded-2xl bg-rose-950/40 border border-rose-800 text-xs text-rose-200'
      : 'mt-4 p-4 rounded-2xl bg-slate-950/60 border border-slate-800 text-xs text-slate-200';
    output.innerHTML = html;
  }

  async function hydrateAiStatus() {
    const badge = document.getElementById('flux-ai-status-badge');
    if (!badge) return;
    if (!localStorage.getItem('flux_access_token')) {
      badge.textContent = 'Sign in required';
      badge.className = 'text-[9px] px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800';
      return;
    }

    try {
      const status = await aiRequest('/ai/status');
      if (status.configured) {
        badge.textContent = 'AI ready';
        badge.className = 'text-[9px] px-2 py-0.5 rounded-full bg-emerald-950 text-emerald-300 border border-emerald-800';
      } else {
        badge.textContent = 'Gemini key required';
        badge.className = 'text-[9px] px-2 py-0.5 rounded-full bg-amber-950 text-amber-300 border border-amber-800';
      }
    } catch (error) {
      badge.textContent = 'AI unavailable';
      badge.className = 'text-[9px] px-2 py-0.5 rounded-full bg-rose-950 text-rose-300 border border-rose-800';
    }
  }

  window.generateFluxAiBriefing = async function generateFluxAiBriefing(courseId) {
    try {
      const { subjectId } = resolveAiSubject(courseId);
      setAiOutput('<div class="text-cyan-300 font-semibold"><span class="animate-pulse">●</span> Preparing your briefing…</div>');
      const result = await aiRequest('/ai/flight-briefing', { subject_id: subjectId });
      setAiOutput(`
        <div class="flex items-start justify-between gap-3">
          <div>
            <div class="text-[10px] uppercase tracking-wider text-cyan-300 font-bold">${result.cached ? 'Cached' : 'Fresh'} · ${escapeFluxAi(result.model)}</div>
            <h3 class="text-base font-black text-white mt-1">${escapeFluxAi(result.title)}</h3>
            <p class="text-slate-300 mt-2 leading-relaxed">${escapeFluxAi(result.hook)}</p>
          </div>
          <button onclick="this.closest('[id$=output]').classList.add('hidden')" class="text-slate-500 hover:text-white">✕</button>
        </div>
        <div class="mt-4 grid grid-cols-1 md:grid-cols-2 gap-2">
          ${result.concepts.map((concept, index) => `<div class="p-3 rounded-xl bg-slate-900 border border-slate-800"><span class="text-cyan-400 font-bold mr-1">${index + 1}.</span>${escapeFluxAi(concept)}</div>`).join('')}
        </div>
        <div class="mt-3 p-3 rounded-xl bg-indigo-950/40 border border-indigo-800 text-indigo-100"><strong>Check yourself:</strong> ${escapeFluxAi(result.check_question)}</div>
        <div class="mt-3 text-[10px] text-slate-500">${result.recommended_minutes} min · ${escapeFluxAi(result.subject_code)}${result.topic ? ` · ${escapeFluxAi(result.topic)}` : ' · subject-level briefing'}</div>
      `);
    } catch (error) {
      setAiOutput(escapeFluxAi(error.message || 'The AI briefing could not be generated.'), 'error');
    }
  };

  window.generateFluxAiQuiz = async function generateFluxAiQuiz(courseId) {
    try {
      const { course, subjectId } = resolveAiSubject(courseId);
      setAiOutput('<div class="text-indigo-300 font-semibold"><span class="animate-pulse">●</span> Generating a fresh 5-question quiz…</div>');
      const result = await aiRequest('/ai/quiz', {
        subject_id: subjectId,
        difficulty: 'mixed',
        count: 5
      });

      activeAiQuizAttempt = {
        id: crypto.randomUUID(),
        cacheKey: result.cache_key,
        answers: [],
        subjectId: result.subject_id
      };
      activeQuizQuestions = result.questions.map(question => ({
        q: question.question,
        options: question.options,
        ans: question.answer_index,
        exp: question.explanation
      }));
      quizIdx = 0;
      quizPoints = 0;
      quizOptionLocked = false;

      document.getElementById('quiz-course-title').textContent = `${course.name} · AI Quiz`;
      document.getElementById('quiz-modal').classList.remove('hidden');
      document.getElementById('quiz-modal').classList.add('flex');
      document.getElementById('quiz-result-box').classList.add('hidden');
      document.getElementById('quiz-question-box').classList.remove('hidden');
      document.getElementById('quiz-footer').classList.remove('hidden');
      document.getElementById('quiz-next-btn').textContent = 'Next Question →';
      renderQuizStep();

      setAiOutput(`<div class="text-emerald-300 font-semibold">AI quiz ready · ${escapeFluxAi(result.cached ? 'cached question set' : 'fresh question set')}.</div>`);
    } catch (error) {
      activeAiQuizAttempt = null;
      setAiOutput(escapeFluxAi(error.message || 'The AI quiz could not be generated.'), 'error');
    }
  };

  const originalOpenSubjectWorkspace = window.openSubjectWorkspace;
  if (typeof originalOpenSubjectWorkspace === 'function') {
    window.openSubjectWorkspace = function patchedOpenSubjectWorkspace(courseId) {
      const result = originalOpenSubjectWorkspace(courseId);
      queueMicrotask(() => injectSubjectAiControls(courseId));
      return result;
    };
  }

  const originalSwitchView = window.switchView;
  if (typeof originalSwitchView === 'function') {
    window.switchView = function patchedSwitchView(target) {
      const result = originalSwitchView(target);
      if (target === 'subjects') queueMicrotask(injectSubjectsAiLauncher);
      return result;
    };
  }

  const originalLaunchQuiz = window.launchQuiz;
  if (typeof originalLaunchQuiz === 'function') {
    window.launchQuiz = function patchedLaunchQuiz(courseId) {
      activeAiQuizAttempt = null;
      return originalLaunchQuiz(courseId);
    };
  }

  const originalHandleQuizAnswer = window.handleQuizAnswer;
  if (typeof originalHandleQuizAnswer === 'function') {
    window.handleQuizAnswer = function patchedHandleQuizAnswer(optionIndex) {
      if (activeAiQuizAttempt && !quizOptionLocked) {
        activeAiQuizAttempt.answers[quizIdx] = optionIndex;
      }
      return originalHandleQuizAnswer(optionIndex);
    };
  }

  const originalNextQuizQuestion = window.nextQuizQuestion;
  if (typeof originalNextQuizQuestion === 'function') {
    window.nextQuizQuestion = function patchedNextQuizQuestion() {
      if (activeAiQuizAttempt && !quizOptionLocked) return;
      const finishingAiQuiz = Boolean(
        activeAiQuizAttempt && quizIdx >= activeQuizQuestions.length - 1
      );
      const result = originalNextQuizQuestion();
      if (finishingAiQuiz) {
        const attempt = activeAiQuizAttempt;
        activeAiQuizAttempt = null;
        const summary = document.getElementById('quiz-result-summary');
        if (summary) summary.textContent = 'Saving your AI quiz result…';
        void aiRequest('/ai/quiz-attempts', {
          id: attempt.id,
          cache_key: attempt.cacheKey,
          answers: attempt.answers
        }).then(saved => {
          if (summary) summary.textContent = `You scored ${saved.score} out of ${saved.total}. Saved to your FLUX ONE account.`;
        }).catch(error => {
          if (summary) summary.textContent = `You scored ${quizPoints} out of ${activeQuizQuestions.length}. Save failed: ${error.message}`;
        });
      }
      return result;
    };
  }

  injectSubjectsAiLauncher();
})();