// Personal workspace state is loaded from the API for the signed-in account.
let catalogInfo = null;
let savedProgress = null;
let currentView = 'dashboard';
let activeSubjectId = null;
let workspaceReady = false;
let activityEvents = [];
let activityQueue = [];
let captureClicks = true;
let activityTimer;
let activityFlight = null;
let activeQuizCourse = null;
let quizAnswers = [];
let quizAttemptId = null;
let activeSessionRecord = null;
let syncSequence = 0;

function selectStudyTopic() { /* Selection is recorded by the delegated change listener. */ }

function runSessionClock() {
  clearInterval(studyTimerInterval);
  isStudyActive = activeSessionRecord.state === 'active';
  document.getElementById('study-course-select').disabled = true;
  document.getElementById('study-topic-select').disabled = true;
  document.getElementById('study-btn-start').classList.add('hidden');
  document.getElementById('study-btn-pause').classList.remove('hidden');
  document.getElementById('study-btn-finish').classList.remove('hidden');
  document.getElementById('session-badge').textContent = isStudyActive ? 'ACTIVE' : 'PAUSED';
  document.getElementById('session-badge').className = 'text-xs font-bold px-3 py-1 rounded-xl bg-emerald-950 text-emerald-300 border border-emerald-800';
  document.getElementById('study-btn-pause').innerHTML = isStudyActive ? 'Pause' : 'Resume';
  document.getElementById('study-btn-pause').onclick = isStudyActive ? pauseStudySession : resumeStudySession;
  const tick = () => {
    const stopAt = activeSessionRecord.state === 'paused' ? Date.parse(activeSessionRecord.paused_at) : Date.now();
    const elapsed = Math.max(0, Math.floor((stopAt - Date.parse(activeSessionRecord.started_at)) / 1000) - Number(activeSessionRecord.paused_seconds || 0));
    timerTotalSeconds = Math.max(0, Number(activeSessionRecord.target_seconds || activeDurationMins * 60) - elapsed);
    updateClockDisplay();
    if (!timerTotalSeconds && isStudyActive) { clearInterval(studyTimerInterval); void openSessionReflection(); }
  };
  if (isStudyActive) studyTimerInterval = setInterval(tick, 1000);
  tick();
}

async function restoreActiveSession() {
  const session = await fluxApi.request('/sessions/active');
  if (!session) return;
  activeBackendSessionId = session.id; activeSessionRecord = session;
  activeDurationMins = Math.round(Number(session.target_seconds) / 60);
  const course = coursesData.find(c => c.code === session.course_code);
  if (course) { document.getElementById('study-course-select').value = course.id; populateStudyTopics(); }
  const topicSelect = document.getElementById('study-topic-select');
  const option = [...topicSelect.options].find(option => option.text === session.topic);
  if (option) topicSelect.value = option.value;
  document.getElementById('study-clock-desc').textContent = activeDurationMins + '-minute focus session';
  runSessionClock();
}

function showAppError(message) {
  const el = document.getElementById('workspace-error');
  el.textContent = message;
  el.classList.remove('hidden');
  clearTimeout(showAppError.timer);
  showAppError.timer = setTimeout(() => el.classList.add('hidden'), 9000);
}

function setSyncStatus(text) {
  document.getElementById('workspace-sync-status').textContent = text;
}

async function retrySync() {
  const loader = document.getElementById('workspace-loader');
  workspaceReady = false;
  loader.classList.remove('hidden');
  document.getElementById('workspace-load-message').textContent = 'Loading your class and saved work…';
  try {
    await loadLiveData(true);
    if (!currentUser) return;
    workspaceReady = true;
    loader.classList.add('hidden');
    initStudyEngine();
    await restoreActiveSession();
    setTimetableDay(defaultTimetableDay());
    switchView('dashboard');
    if (!getStudentProfile()) openStudentProfileModal();
  } catch (error) {
    document.getElementById('workspace-load-message').textContent = error.message;
    setSyncStatus('Connection needs attention');
  }
}

async function loadLiveData(initial = false) {
  const userId = currentUser?.id;
  if (!userId) return;
  const sequence = ++syncSequence;
  setSyncStatus('Syncing your workspace…');
  const [profile, catalog, progress, remoteAssignments, remoteNotes, remoteSessions, preferences] = await Promise.all([
    fluxApi.getProfile(), initial || !catalogInfo ? fluxApi.getCatalog() : catalogInfo,
    fluxApi.getProgress(), fluxApi.getAssignments(), fluxApi.getNotes(), fluxApi.getSessionHistory(),
    fluxApi.request('/activity/preferences')
  ]);
  if (currentUser?.id !== userId || sequence !== syncSequence) return;
  if (!catalog || !Array.isArray(catalog.courses) || !Array.isArray(catalog.timetable)) {
    coursesData = []; rawData = [];
    throw new Error('Academic catalog is temporarily unavailable. Please retry in a moment.');
  }
  const progressCourses = Array.isArray(progress?.courses) ? progress.courses : [];
  currentUser = profile; catalogInfo = catalog; savedProgress = progress; captureClicks = preferences.capture_clicks;
  coursesData = catalog.courses.map(course => ({ ...course, units: Array.isArray(course.units) ? course.units : [], progress: progressCourses.find(item => item.course_id === course.id)?.percent || 0 }));
  academicMilestones = Array.isArray(catalog.milestones) ? catalog.milestones : [];
  rawData = catalog.timetable;
  quizBank = catalog.quizzes && typeof catalog.quizzes === 'object' ? catalog.quizzes : {};
  const courseIdFor = code => coursesData.find(course => course.code === code || course.name === code)?.id || null;
  const displayDate = (value, fallback = 'Not scheduled') => value ? new Date(value).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : fallback;
  assignments = remoteAssignments.map(a => ({ ...a, courseId: courseIdFor(a.course_code), topic: a.topic || 'General', due: displayDate(a.due_at), done: a.status === 'completed', remote: true }));
  notesList = remoteNotes.map(n => ({ ...n, courseId: courseIdFor(n.course_code), date: displayDate(n.created_at), remote: true }));
  studySessions = remoteSessions.filter(s => s.state === 'completed').map(s => ({
    course: coursesData.find(c => c.code === s.course_code)?.name || s.course_code,
    topic: s.topic, duration: Math.round(Number(s.duration_seconds || 0) / 60), rating: Number(s.focus_rating || 0),
    reflection: s.reflection || '', time: displayDate(s.completed_at)
  }));
  applyUserProfile(currentUser);
  renderDashboard(); renderSubjectsOverview(); renderAssignmentsFull(); renderNotes(); renderStudyHistory();
  renderAcademicBrain(); renderSavedProgress(); renderCalendarData();
  if (activeSubjectId && currentView === 'subjects' && !document.getElementById('subject-workspace-container').classList.contains('hidden')) openSubjectWorkspace(activeSubjectId);
  document.getElementById('class-data-summary').textContent = `${catalog.class_name} · ${coursesData.length} subjects · ${rawData.length} weekly slots`;
  setSyncStatus('Saved work synced · ' + new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
  // Roster and activity are independent panels; a panel error must not hide saved work.
  await Promise.all([
    loadClassRoster().catch(() => { document.getElementById('roster-import-status').textContent = 'Roster could not load. Please refresh.'; }),
    loadActivityEvents()
  ]);
}

function renderSavedProgress() {
  const stats = savedProgress?.stats;
  if (!stats) return;
  document.getElementById('dash-focus-mins').textContent = stats.total_study_minutes + 'm';
  document.getElementById('dash-streak-days').textContent = stats.streak_days;
  document.getElementById('dash-streak-detail').textContent = `${stats.active_days_this_week} active days in the last 7 days`;
  document.getElementById('dash-syllabus-cov').textContent = stats.topic_coverage + '%';
  document.getElementById('dash-brain-pct').textContent = stats.topic_coverage + '%';
  document.getElementById('brain-overall').textContent = stats.topic_coverage + '%';
  for (const key of ['consistency', 'focus_quality', 'topic_coverage', 'assignment_completion']) {
    document.getElementById('brain-' + key).textContent = stats[key] + '%';
    document.getElementById('brain-bar-' + key).style.width = stats[key] + '%';
  }
  document.getElementById('brain-evidence').textContent = `${stats.completed_sessions} completed sessions · ${savedProgress.quizzes.length} saved quizzes`;
  document.getElementById('brain-next-step').textContent = stats.completed_sessions ? 'Continue a practice topic or review your latest notes.' : 'Start a session in one of your class subjects.';
  document.getElementById('quiz-history-list').innerHTML = savedProgress.quizzes.length
    ? savedProgress.quizzes.slice(0, 12).map(quiz => `<div class="flex justify-between gap-3 p-3 rounded-xl bg-slate-950/50 border border-slate-800"><div><div class="font-semibold text-white">${escapeRosterHtml(coursesData.find(c => c.id === quiz.course_id)?.name || quiz.course_id)}</div><div class="text-[10px] text-slate-500 mt-1">${escapeRosterHtml(new Date(quiz.created_at).toLocaleString())}</div></div><span class="font-bold text-cyan-300">${quiz.score}/${quiz.total}</span></div>`).join('')
    : '<p class="text-slate-500 py-3">Complete a practice quiz to save your first result.</p>';
}

function topicIsComplete(courseId, unit, topic) {
  return Boolean(savedProgress?.topics.some(item => item.course_id === courseId && item.unit_index === unit && item.topic_index === topic && item.completed));
}

async function toggleTopic(courseId, unit, topic, completed) {
  try {
    await fluxApi.request('/progress/topics', 'PUT', { course_id: courseId, unit_index: unit, topic_index: topic, completed });
    await loadLiveData();
  } finally { openSubjectWorkspace(courseId); }
}

function renderCalendarData() {
  if (!catalogInfo) return;
  const format = date => new Date(date + 'T00:00:00').toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' });
  document.getElementById('calendar-milestones').innerHTML = catalogInfo.milestones.map(item => `<li class="py-2 border-b border-slate-800 last:border-0"><div class="text-slate-200">${escapeRosterHtml(item.title)}</div><div class="text-cyan-300 mt-1">${format(item.start)}${item.end !== item.start ? ' – ' + format(item.end) : ''}</div></li>`).join('');
  document.getElementById('calendar-holidays').innerHTML = catalogInfo.holidays.map(item => `<li class="py-1">${format(item.date)} · ${escapeRosterHtml(item.title)}</li>`).join('');
}

function openAssignmentModal() {
  document.getElementById('assignment-form').reset();
  document.getElementById('assignment-course').innerHTML = coursesData.map(course => `<option value="${course.code}">${escapeRosterHtml(course.name)}</option>`).join('');
  document.getElementById('assignment-modal').classList.remove('hidden');
  document.getElementById('assignment-modal').classList.add('flex');
}
function closeAssignmentModal() {
  document.getElementById('assignment-modal').classList.add('hidden');
  document.getElementById('assignment-modal').classList.remove('flex');
}
async function saveAssignment(event) {
  event.preventDefault();
  const due = document.getElementById('assignment-due').value;
  await fluxApi.createAssignment({
    course_code: document.getElementById('assignment-course').value,
    title: document.getElementById('assignment-title').value.trim(),
    due_at: due ? new Date(due + 'T23:59:00').toISOString() : null,
    priority: document.getElementById('assignment-priority').value
  });
  closeAssignmentModal();
  await loadLiveData();
}

function trackActivity(eventType, target) {
  if (!currentUser || !workspaceReady || !captureClicks) return;
  if (eventType !== 'view' && !catalogInfo?.client_actions.includes(target)) return;
  activityQueue.push({ event_type: eventType, view: currentView, target });
  if (activityQueue.length > 200) activityQueue.shift();
  clearTimeout(activityTimer);
  activityTimer = setTimeout(() => void flushActivity(), 1000);
}

async function flushActivity() {
  if (activityFlight) return activityFlight;
  const token = localStorage.getItem('flux_access_token');
  if (!token || !activityQueue.length) return;
  const batch = activityQueue.splice(0, 50);
  activityFlight = (async () => {
    try {
      const response = await fetch(API_BASE + '/activity/events', {
        method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ events: batch }), keepalive: true, signal: AbortSignal.timeout(10000)
      });
      if (!response.ok) throw new Error('Activity could not sync');
    } catch {
      if (token === localStorage.getItem('flux_access_token')) {
        activityQueue = [...batch, ...activityQueue].slice(-200);
        document.getElementById('activity-count').textContent = 'Some activity is waiting to sync';
      }
    } finally {
      activityFlight = null;
      if (activityQueue.length && token === localStorage.getItem('flux_access_token')) activityTimer = setTimeout(() => void flushActivity(), 5000);
    }
  })();
  return activityFlight;
}

async function loadActivityEvents() {
  const userId = currentUser?.id;
  if (!userId) return;
  try {
    await flushActivity();
    const events = await fluxApi.request('/activity/events');
    if (currentUser?.id !== userId) return;
    activityEvents = events;
    document.getElementById('activity-count').textContent = `${events.length} recent events${activityQueue.length ? ' · sync pending' : ''}`;
    document.getElementById('activity-capture-button').textContent = captureClicks ? 'Pause click recording' : 'Resume click recording';
    document.getElementById('activity-capture-state').textContent = captureClicks ? 'Navigation and action clicks are being recorded for your account.' : 'Click recording paused. Saved work continues to appear in your history.';
    document.getElementById('activity-events-list').innerHTML = events.length ? events.map(event => {
      const labels = { switchView: 'Navigate to a section', handleQuizAnswer: 'Select quiz answer', loadActivityEvents: 'Refresh history', toggleActivityCapture: 'Change click recording', saveCompletedStudySession: 'Save study reflection', openSessionReflection: 'Open study reflection', saveNewNote: 'Save note', openNewNoteModal: 'Open note editor', launchQuiz: 'Start practice quiz', generateFlightBriefing: 'Generate AI flight briefing', generateAiQuiz: 'Generate AI quiz', toggleTopic: 'Change topic completion', populateStudyTopics: 'Choose study subject', selectStudyTopic: 'Choose practice topic', renderTimetableFull: 'Change timetable batch' };
      const label = labels[event.target] || event.target?.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/-/g, ' ') || event.event_type;
      const saved = event.metadata?.source === 'server';
      return `<div class="flex items-start gap-3 p-3.5 rounded-2xl bg-slate-950/60 border border-slate-800"><span class="mt-1 h-2 w-2 rounded-full shrink-0 ${saved ? 'bg-emerald-400' : 'bg-cyan-400'}"></span><div class="min-w-0 flex-1"><div class="capitalize font-semibold text-slate-100">${escapeRosterHtml(label)}</div><div class="text-[10px] text-slate-500 mt-1">${saved ? 'Saved action' : 'App interaction'}${event.view ? ' · ' + escapeRosterHtml(event.view) : ''}</div></div><time class="shrink-0 text-[10px] text-slate-400 text-right">${escapeRosterHtml(new Date(event.created_at).toLocaleDateString())}<br>${escapeRosterHtml(new Date(event.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }))}</time></div>`;
    }).join('') : '<p class="py-5 text-slate-500">Your saved work and app actions will appear here.</p>';
  } catch {
    if (currentUser?.id === userId) document.getElementById('activity-count').textContent = 'Activity unavailable — retry with Refresh';
  }
}

async function toggleActivityCapture() {
  await flushActivity();
  const preferences = await fluxApi.request('/activity/preferences', 'PUT', { capture_clicks: !captureClicks });
  captureClicks = preferences.capture_clicks;
  if (!captureClicks) activityQueue = [];
  await loadActivityEvents();
}

for (const eventType of ['click', 'change']) {
  document.addEventListener(eventType, event => {
    if (!(event.target instanceof Element)) return;
    const control = event.target.closest(eventType === 'click' ? '[onclick],button,[role="button"]' : '[onchange],select');
    if (!control || control.closest('#auth-view')) return;
    const selections = { 'assignment-course': 'selectAssignmentCourse', 'assignment-priority': 'selectAssignmentPriority', 'profile-batch': 'selectProfileBatch' };
    const handler = control.getAttribute(eventType === 'click' ? 'onclick' : 'onchange') || (eventType === 'click' ? control.closest('form')?.getAttribute('onsubmit') : '') || '';
    const action = (eventType === 'change' ? selections[control.id] : null) || handler.match(/^\s*([A-Za-z]\w*)\s*\(/)?.[1];
    if (action) trackActivity(eventType, action);
  }, true);
}
document.addEventListener('visibilitychange', () => { if (document.visibilityState === 'hidden') void flushActivity(); });
window.addEventListener('pagehide', () => void flushActivity());

// Keep save failures visible and block repeated submissions while a save is in flight.
for (const name of ['saveStudentProfile', 'saveNewNote', 'deleteNote', 'toggleAssignment', 'toggleTopic', 'saveAssignment', 'nextQuizQuestion', 'toggleActivityCapture', 'startStudySession', 'pauseStudySession', 'resumeStudySession', 'openSessionReflection', 'saveCompletedStudySession', 'generateFlightBriefing', 'generateAiQuiz']) {
  const action = window[name];
  let busy = false;
  window[name] = async function (...args) {
    if (busy) { args[0]?.preventDefault?.(); return; }
    busy = true;
    try { return await action(...args); }
    catch (error) { showAppError(error.message || 'Could not save. Please retry.'); }
    finally { busy = false; }
  };
}

checkAuthAndInit();
