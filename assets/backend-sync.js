(() => {
  function escapeFluxSync(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({
      '&': '&amp;',
      '<': '&lt;',
      '>': '&gt;',
      '"': '&quot;',
      "'": '&#39;'
    }[char]));
  }

  function isSignedIn() {
    return Boolean(localStorage.getItem('flux_access_token'));
  }

  function apiErrorMessage(payload, status) {
    return payload?.message || payload?.detail || `Request failed (${status}).`;
  }

  function enrolledSubjectIdForCourse(courseId) {
    const course = coursesData.find(item => item.id === courseId);
    if (!course) throw new Error('Selected course is not available.');
    const enrolled = currentUser?.enrolled_subjects?.find(item => item.code === course.code);
    if (!enrolled?.id) {
      throw new Error(`${course.code} is not linked to your backend enrollment.`);
    }
    return Number(enrolled.id);
  }

  async function authenticatedFetch(path, options = {}) {
    const token = localStorage.getItem('flux_access_token');
    if (!token) throw new Error('Please sign in to sync this activity.');
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers || {})
      }
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(apiErrorMessage(payload, response.status));
    return payload;
  }

  // Replace the stale 1..7 subject mapping with the real enrolled subject IDs returned by /auth/me.
  fluxApi.startSession = async function startSyncedSession(courseId, targetDurationMins) {
    if (!isSignedIn()) return { local_only: true };
    const subjectId = enrolledSubjectIdForCourse(courseId);
    const data = await authenticatedFetch('/sessions/start', {
      method: 'POST',
      body: JSON.stringify({
        subject_id: subjectId,
        topic_id: null,
        target_duration_minutes: Number(targetDurationMins) || 45,
        source: 'MANUAL'
      })
    });
    activeBackendSessionId = data.id;
    return data;
  };

  fluxApi.getActiveSession = async function getActiveSession() {
    if (!isSignedIn()) return null;
    return authenticatedFetch('/sessions/active');
  };

  fluxApi.getSessionHistory = async function getSessionHistory(limit = 20) {
    if (!isSignedIn()) return [];
    return authenticatedFetch(`/sessions/history?limit=${encodeURIComponent(limit)}`);
  };

  fluxApi.sendHeartbeat = async function sendSyncedHeartbeat() {
    if (!isSignedIn() || !activeBackendSessionId) return null;
    return authenticatedFetch(`/sessions/${activeBackendSessionId}/heartbeat`, {
      method: 'POST',
      body: JSON.stringify({})
    });
  };

  fluxApi.pauseSession = async function pauseSyncedSession() {
    if (!isSignedIn() || !activeBackendSessionId) return null;
    return authenticatedFetch(`/sessions/${activeBackendSessionId}/pause`, { method: 'POST' });
  };

  fluxApi.resumeSession = async function resumeSyncedSession() {
    if (!isSignedIn() || !activeBackendSessionId) return null;
    return authenticatedFetch(`/sessions/${activeBackendSessionId}/resume`, { method: 'POST' });
  };

  fluxApi.completeSession = async function completeSyncedSession(focusRating, reflectionNote) {
    if (!isSignedIn()) return { local_only: true };
    if (!activeBackendSessionId) throw new Error('No backend study session is active.');
    const sessionId = activeBackendSessionId;
    const data = await authenticatedFetch(`/sessions/${sessionId}/complete`, {
      method: 'POST',
      body: JSON.stringify({
        focus_rating: Math.max(1, Math.min(5, Number(focusRating) || 5)),
        reflection_note: reflectionNote || 'Completed structured study session.'
      })
    });
    activeBackendSessionId = null;
    return data;
  };

  function setSessionBadge(text, className) {
    const badge = document.getElementById('session-badge');
    if (!badge) return;
    badge.textContent = text;
    badge.className = className;
  }

  function beginLocalTimer() {
    clearInterval(studyTimerInterval);
    isStudyActive = true;
    setSessionBadge(
      'ACTIVE',
      'text-xs font-bold px-3 py-1 rounded-xl bg-emerald-950 text-emerald-300 border border-emerald-800'
    );
    document.getElementById('study-btn-start')?.classList.add('hidden');
    document.getElementById('study-btn-pause')?.classList.remove('hidden');
    document.getElementById('study-btn-finish')?.classList.remove('hidden');

    studyTimerInterval = setInterval(() => {
      if (timerTotalSeconds > 0) {
        timerTotalSeconds--;
        updateClockDisplay();
        if (timerTotalSeconds % 30 === 0 && isSignedIn()) {
          fluxApi.sendHeartbeat().catch(error => console.warn('Heartbeat sync failed:', error));
        }
      } else {
        openSessionReflection();
      }
    }, 1000);
  }

  window.startStudySession = async function startStudySessionSynced() {
    if (isStudyActive) return;
    const courseId = document.getElementById('study-course-select')?.value || 'sat';

    if (isSignedIn()) {
      setSessionBadge(
        'SYNCING',
        'text-xs font-bold px-3 py-1 rounded-xl bg-cyan-950 text-cyan-300 border border-cyan-800'
      );
      try {
        await fluxApi.startSession(courseId, activeDurationMins);
      } catch (error) {
        setSessionBadge(
          'SYNC ERROR',
          'text-xs font-bold px-3 py-1 rounded-xl bg-rose-950 text-rose-300 border border-rose-800'
        );
        alert(`Session was not started because backend sync failed: ${error.message}`);
        return;
      }
    }

    beginLocalTimer();
  };

  window.pauseStudySession = function pauseStudySessionSynced() {
    if (!isStudyActive) return;
    isStudyActive = false;
    clearInterval(studyTimerInterval);
    setSessionBadge(
      'PAUSED',
      'text-xs font-bold px-3 py-1 rounded-xl bg-amber-950 text-amber-300 border border-amber-800'
    );
    const pauseButton = document.getElementById('study-btn-pause');
    if (pauseButton) {
      pauseButton.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> Resume';
      pauseButton.onclick = resumeStudySession;
    }
    if (window.lucide) lucide.createIcons();

    if (isSignedIn() && activeBackendSessionId) {
      fluxApi.pauseSession().catch(error => {
        console.warn('Pause sync failed:', error);
        setSessionBadge(
          'PAUSED · SYNC ERROR',
          'text-xs font-bold px-3 py-1 rounded-xl bg-rose-950 text-rose-300 border border-rose-800'
        );
      });
    }
  };

  window.resumeStudySession = async function resumeStudySessionSynced() {
    if (isStudyActive) return;
    if (isSignedIn()) {
      try {
        await fluxApi.resumeSession();
      } catch (error) {
        setSessionBadge(
          'SYNC ERROR',
          'text-xs font-bold px-3 py-1 rounded-xl bg-rose-950 text-rose-300 border border-rose-800'
        );
        alert(`Session could not resume: ${error.message}`);
        return;
      }
    }
    const pauseButton = document.getElementById('study-btn-pause');
    if (pauseButton) {
      pauseButton.innerHTML = '<i data-lucide="pause" class="w-4 h-4"></i> Pause';
      pauseButton.onclick = pauseStudySession;
    }
    if (window.lucide) lucide.createIcons();
    beginLocalTimer();
  };

  async function hydrateSessionHistory() {
    if (!isSignedIn()) return;
    try {
      const history = await fluxApi.getSessionHistory(30);
      studySessions = history.map(session => ({
        course: `${session.subject_code || 'Course'}: ${session.subject_name || 'Study Session'}`,
        topic: session.topic_title || 'General subject study',
        duration: session.duration_minutes,
        rating: session.focus_rating || 0,
        reflection: session.reflection_note || (session.status === 'COMPLETED' ? 'Completed session.' : `Status: ${session.status}`),
        time: new Date(session.start_time).toLocaleString()
      }));
      localStorage.setItem('flux_sessions', JSON.stringify(studySessions));
      renderStudyHistory();
    } catch (error) {
      console.warn('Session history sync failed:', error);
    }
  }

  async function hydrateDashboardMetrics() {
    if (!isSignedIn()) return;
    try {
      const overview = await fluxApi.getDashboard();
      if (!overview) return;
      const focus = document.getElementById('dash-focus-mins');
      if (focus) focus.textContent = `${overview.study_time_today_minutes || 0}m`;
      const brain = document.getElementById('dash-brain-pct');
      if (brain && Number.isFinite(Number(overview.consistency_score))) {
        brain.textContent = `${Math.round(Number(overview.consistency_score))}%`;
      }
    } catch (error) {
      console.warn('Dashboard metric sync failed:', error);
    }
  }

  async function recoverActiveSession() {
    if (!isSignedIn()) return;
    try {
      const active = await fluxApi.getActiveSession();
      if (!active) return;
      activeBackendSessionId = active.id;
      const course = coursesData.find(item => item.code === active.subject_code);
      if (course) {
        const select = document.getElementById('study-course-select');
        if (select) {
          select.value = course.id;
          populateStudyTopics();
        }
      }
      if (active.status === 'PAUSED') {
        isStudyActive = false;
        setSessionBadge(
          'PAUSED · RESTORED',
          'text-xs font-bold px-3 py-1 rounded-xl bg-amber-950 text-amber-300 border border-amber-800'
        );
        document.getElementById('study-btn-start')?.classList.add('hidden');
        document.getElementById('study-btn-pause')?.classList.remove('hidden');
        document.getElementById('study-btn-finish')?.classList.remove('hidden');
        const pauseButton = document.getElementById('study-btn-pause');
        if (pauseButton) {
          pauseButton.innerHTML = '<i data-lucide="play" class="w-4 h-4"></i> Resume';
          pauseButton.onclick = resumeStudySession;
        }
      } else {
        isStudyActive = false;
        beginLocalTimer();
      }
      if (window.lucide) lucide.createIcons();
    } catch (error) {
      console.warn('Active session recovery failed:', error);
    }
  }

  window.saveCompletedStudySession = async function saveCompletedStudySessionSynced() {
    const topicSelect = document.getElementById('study-topic-select');
    const fullTopicText = topicSelect?.options[topicSelect.selectedIndex]?.text || 'Study Session';
    const courseId = document.getElementById('study-course-select')?.value;
    const course = coursesData.find(item => item.id === courseId);
    const reflection = document.getElementById('refl-text-input')?.value.trim() || 'Completed structured study session.';

    let backendSession = null;
    if (isSignedIn()) {
      try {
        backendSession = await fluxApi.completeSession(activeStudyRating, reflection);
      } catch (error) {
        alert(`Session was not saved to FLUX ONE: ${error.message}`);
        return;
      }
    }

    if (!isSignedIn()) {
      studySessions.unshift({
        course: course ? `${course.code}: ${course.name}` : 'Course',
        topic: fullTopicText,
        duration: activeDurationMins,
        rating: activeStudyRating,
        reflection,
        time: 'Just now'
      });
      localStorage.setItem('flux_sessions', JSON.stringify(studySessions));
    }

    closeSessionReflection();
    if (backendSession) {
      await hydrateSessionHistory();
      await hydrateDashboardMetrics();
    } else {
      renderStudyHistory();
      renderDashboard();
    }
  };

  const originalShowAppView = window.showAppView;
  if (typeof originalShowAppView === 'function') {
    window.showAppView = function showAppViewWithBackendSync(user) {
      const result = originalShowAppView(user);
      queueMicrotask(() => {
        hydrateSessionHistory();
        hydrateDashboardMetrics();
        recoverActiveSession();
      });
      return result;
    };
  }

  // Covers the race where authentication completed before this external script loaded.
  setTimeout(() => {
    if (typeof currentUser !== 'undefined' && currentUser && isSignedIn()) {
      hydrateSessionHistory();
      hydrateDashboardMetrics();
      recoverActiveSession();
    }
  }, 500);

  window.__fluxBackendSync = {
    hydrateSessionHistory,
    hydrateDashboardMetrics,
    recoverActiveSession,
    escapeFluxSync
  };
})();
