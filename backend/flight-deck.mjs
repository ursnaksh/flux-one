// backend/flight-deck.mjs - The Today Command Center Engine for FLUX ONE

function parseTimeRange(timeStr) {
  const parts = String(timeStr || '').split('-').map(s => s.trim());
  if (parts.length !== 2) return null;
  
  const endMatch = parts.match(/(AM|PM)/i);
  const endPeriod = endMatch ? endMatch.toUpperCase() : 'PM';
  const startMatch = parts[0].match(/(AM|PM)/i);
  let startPeriod = startMatch ? startMatch.toUpperCase() : null;
  
  const parseHourMin = (str, period) => {
    const clean = str.replace(/(AM|PM)/i, '').trim();
    let [h, m] = clean.split(':').map(Number);
    if (period === 'PM' && h < 12) h += 12;
    if (period === 'AM' && h === 12) h = 0;
    return h * 60 + (m || 0);
  };

  if (!startPeriod) {
    const rawStartH = parseInt(parts[0].split(':')[0]);
    if (endPeriod === 'PM' && (rawStartH === 11 || rawStartH === 10 || rawStartH === 9 || rawStartH === 8)) {
      startPeriod = 'AM';
    } else {
      startPeriod = endPeriod;
    }
  }

  return {
    startMinutes: parseHourMin(parts[0], startPeriod),
    endMinutes: parseHourMin(parts, endPeriod)
  };
}

export function buildTopicId(courseId, unitIndex, topicIndex) {
  return `${String(courseId).toLowerCase()}-u${Number(unitIndex)}-t${Number(topicIndex)}`;
}

export async function getFlightDeckToday({ db, catalog, user, now = new Date() }) {
  // Convert to Indian Standard Time (IST: UTC +05:30)
  const istOffset = 5.5 * 60 * 60 * 1000;
  const istDate = new Date(now.getTime() + istOffset);
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const todayStr = days[istDate.getUTCDay()];
  const currentMinutes = istDate.getUTCHours() * 60 + istDate.getUTCMinutes();

  const userBatch = String(user?.batch || 'ALL').trim().toUpperCase();

  // Parse today's timetable entries for this student
  const rawTimetable = Array.isArray(catalog?.timetable) ? catalog.timetable : [];
  const todaySchedule = [];

  for (const line of rawTimetable) {
    const parts = line.split('|').map(s => s.trim());
    if (parts.length < 8) continue;
    
    const [day, timeStr, type, subjectTitle, faculty, room, batch, courseId, uIdxStr, tIdxStr] = parts;
    if (day.toLowerCase() !== todayStr.toLowerCase()) continue;
    
    // Batch filter: match ALL or student's specific batch (B1/B2/B3)
    if (batch !== 'ALL' && userBatch !== 'ALL' && batch !== userBatch) continue;

    const parsedTime = parseTimeRange(timeStr);
    if (!parsedTime) continue;

    const uIdx = Number(uIdxStr || 0);
    const tIdx = Number(tIdxStr || 0);
    const course = catalog.courses?.find(c => c.id === courseId);
    const unit = course?.units?.[uIdx];
    const topic = unit?.topics?.[tIdx] || null;
    const topicId = buildTopicId(courseId, uIdx, tIdx);

    todaySchedule.push({
      day,
      timeStr,
      startMinutes: parsedTime.startMinutes,
      endMinutes: parsedTime.endMinutes,
      type,
      subjectTitle,
      faculty,
      room,
      batch,
      courseId,
      courseCode: course?.code || '',
      courseName: course?.name || subjectTitle,
      unitName: unit?.name || '',
      topicName: topic,
      topicId
    });
  }

  // Sort chronologically
  todaySchedule.sort((a, b) => a.startMinutes - b.startMinutes);

  // Categorize lecture states
  const inSession = todaySchedule.filter(s => s.startMinutes <= currentMinutes && currentMinutes < s.endMinutes);
  const upcoming = todaySchedule.filter(s => currentMinutes < s.startMinutes);
  const completedToday = todaySchedule.filter(s => s.endMinutes <= currentMinutes);

  // Determine Singular Priority Action (The "One Thing To Do Right Now")
  let priorityAction = null;

  if (inSession.length > 0) {
    const cur = inSession[0];
    priorityAction = {
      type: 'in_class',
      urgency: 'normal',
      headline: `Currently in ${cur.courseName}`,
      detail: `Room ${cur.room} · with ${cur.faculty} (${cur.type})`,
      actionLabel: 'Open Class Workspace',
      target: { view: 'subjects', courseId: cur.courseId, topic: cur.topicName, topicId: cur.topicId },
      statusBadge: 'IN SESSION'
    };
  } else if (upcoming.length > 0 && (upcoming[0].startMinutes - currentMinutes) <= 45) {
    const next = upcoming[0];
    const minsLeft = next.startMinutes - currentMinutes;
    priorityAction = {
      type: 'pre_class_briefing',
      urgency: 'high',
      headline: `${next.courseName} starts in ${minsLeft}m`,
      detail: `Today's Topic: ${next.topicName || next.unitName} (Room ${next.room})`,
      actionLabel: '🚀 Pre-Class Flight Briefing (3 min)',
      target: { view: 'briefing', courseId: next.courseId, topic: next.topicName, topicId: next.topicId },
      statusBadge: 'PRE-CLASS URGENT'
    };
  } else if (completedToday.length > 0 && (currentMinutes - completedToday[completedToday.length - 1].endMinutes) <= 60) {
    const recent = completedToday[completedToday.length - 1];
    priorityAction = {
      type: 'post_lecture_check',
      urgency: 'high',
      headline: `${recent.courseName} concluded`,
      detail: `Test your retention on today's topic: ${recent.topicName || 'lecture concepts'}`,
      actionLabel: '🎯 3-Question Retention Check',
      target: { view: 'debrief', courseId: recent.courseId, topic: recent.topicName, topicId: recent.topicId },
      statusBadge: 'POST-LECTURE'
    };
  } else if (upcoming.length > 0) {
    const next = upcoming[0];
    const hours = Math.floor((next.startMinutes - currentMinutes) / 60);
    const mins = (next.startMinutes - currentMinutes) % 60;
    const timeText = hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
    priorityAction = {
      type: 'prepare_ahead',
      urgency: 'normal',
      headline: `Next Lecture in ${timeText}`,
      detail: `${next.courseName} at ${next.timeStr} (Room ${next.room})`,
      actionLabel: 'Prepare Ahead',
      target: { view: 'briefing', courseId: next.courseId, topic: next.topicName, topicId: next.topicId },
      statusBadge: 'UPCOMING'
    };
  } else {
    priorityAction = {
      type: 'evening_study',
      urgency: 'normal',
      headline: "Lectures completed for today",
      detail: "Strengthen your topic mastery before tomorrow's sessions.",
      actionLabel: '⚡ Launch Adaptive Review',
      target: { view: 'subjects' },
      statusBadge: 'STUDY TIME'
    };
  }

  // Calculate Real Exam Readiness per Course
  const courseReadiness = [];
  const courses = catalog.courses || [];

  for (const course of courses) {
    let totalTopics = 0;
    course.units?.forEach(u => { totalTopics += (u.topics?.length || 0); });

    let completedCount = 0;
    try {
      const prog = await db.prepare('SELECT COUNT(*) as cnt FROM topic_progress WHERE user_id = ? AND course_id = ? AND completed = 1').get(user.id, course.id);
      completedCount = Number(prog?.cnt || 0);
    } catch {}

    let avgQuizScore = 0;
    try {
      const q = await db.prepare('SELECT AVG(score_percent) as avg_score FROM quiz_attempts WHERE user_id = ? AND course_id = ?').get(user.id, course.id);
      if (q && q.avg_score != null) avgQuizScore = Math.round(Number(q.avg_score));
    } catch {}

    const coveragePercent = totalTopics > 0 ? Math.round((completedCount / totalTopics) * 100) : 0;
    const readinessScore = Math.min(100, Math.round(0.6 * coveragePercent + 0.4 * avgQuizScore));

    courseReadiness.push({
      courseId: course.id,
      code: course.code,
      name: course.name,
      totalTopics,
      completedTopics: completedCount,
      coveragePercent,
      avgQuizScore,
      readinessScore
    });
  }

  const overallReadiness = courseReadiness.length > 0 
    ? Math.round(courseReadiness.reduce((acc, c) => acc + c.readinessScore, 0) / courseReadiness.length)
    : 0;

  // Exam Countdown (VIT Pune Mid-Semester Exam: Oct 12, 2026)
  const insemDate = new Date('2026-10-12T09:00:00+05:30');
  const daysToInsem = Math.max(0, Math.ceil((insemDate.getTime() - istDate.getTime()) / (1000 * 60 * 60 * 24)));

  return {
    today: todayStr,
    currentTimeIST: `${String(istDate.getUTCHours()).padStart(2, '0')}:${String(istDate.getUTCMinutes()).padStart(2, '0')}`,
    userBatch,
    todaySchedule,
    inSession,
    nextClass: upcoming[0] || null,
    priorityAction,
    courseReadiness,
    overallReadiness,
    examCountdown: {
      exam: 'Mid-Semester Exam (Insem / MSE)',
      date: '12 Oct 2026',
      daysRemaining: daysToInsem
    }
  };
}
