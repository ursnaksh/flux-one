// backend/flight-deck.mjs - Advanced Academic OS Flight Deck Engine for FLUX ONE

// ==========================================
// 1. TIME & UTILITY HELPERS
// ==========================================

function parseTimeSlot(timeStr) {
  const parts = String(timeStr || '').split('-').map(s => s.trim());
  if (parts.length !== 2) return null;

  const endMatch = parts.match(/(AM|PM)/i);
  const endPeriod = endMatch ? endMatch.toUpperCase() : 'PM';
  const startMatch = parts[0].match(/(AM|PM)/i);
  let startPeriod = startMatch ? startMatch.toUpperCase() : null;

  const toMins = (str, period) => {
    const clean = str.replace(/(AM|PM)/i, '').trim();
    let [h, m] = clean.split(':').map(Number);
    if (period === 'PM' && h < 12) h += 12;
    if (period === 'AM' && h === 12) h = 0;
    return h * 60 + (m || 0);
  };

  if (!startPeriod) {
    const rawH = parseInt(parts[0].split(':')[0]);
    startPeriod = (endPeriod === 'PM' && (rawH >= 8 && rawH <= 11)) ? 'AM' : endPeriod;
  }

  return {
    startMinutes: toMins(parts[0], startPeriod),
    endMinutes: toMins(parts, endPeriod)
  };
}

export function buildTopicSlug(courseId, uIdx, tIdx) {
  return `${String(courseId).toLowerCase()}-u${Number(uIdx)}-t${Number(tIdx)}`;
}

function formatMinutesToTime(totalMinutes) {
  let h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;
  const period = h >= 12 ? 'PM' : 'AM';
  if (h > 12) h -= 12;
  if (h === 0) h = 12;
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')} ${period}`;
}

// ==========================================
// 2. OFFICIAL VIT PUNE ACADEMIC CALENDAR
// ==========================================

const VIT_SEMESTER_CONFIG = {
  semesterName: 'AY 2026-27 • Semester 1 (SEDA)',
  startDate: new Date('2026-08-24T00:00:00+05:30'),
  endDate: new Date('2026-12-12T23:59:59+05:30'),
  totalWeeks: 16,
  midSemExamDate: new Date('2026-10-26T00:00:00+05:30'),
  endSemExamDate: new Date('2026-12-14T00:00:00+05:30'),
  officialHolidays: [
    { date: '2026-09-14', name: 'Shri Ganesh Chaturthi' },
    { date: '2026-09-18', name: 'Gauri Pujan' },
    { date: '2026-09-25', name: 'Anant Chaturdashi' },
    { date: '2026-10-02', name: 'Mahatma Gandhi Jayanti' },
    { date: '2026-10-20', name: 'Dussehra (Vijayadashami)' },
    { date: '2026-11-08', name: 'Diwali Break' },
    { date: '2026-11-09', name: 'Diwali Break' },
    { date: '2026-11-10', name: 'Diwali Break' },
    { date: '2026-11-11', name: 'Diwali Break' },
    { date: '2026-11-12', name: 'Diwali Break' }
  ]
};

// ==========================================
// 3. CORE FLIGHT DECK COMPUTE ENGINE
// ==========================================

export async function computeFlightDeck({ db, catalog, userBatch = 'ALL', userId = 'default_student', simulatedDate = null }) {
  // 1. Current Indian Standard Time (IST)
  const baseNow = simulatedDate ? new Date(simulatedDate) : new Date();
  const istNow = new Date(baseNow.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const todayDay = days[istNow.getDay()];
  const currentMinutes = istNow.getHours() * 60 + istNow.getMinutes();
  const dateISO = istNow.toISOString().split('T')[0];

  // 2. Academic Calendar Telemetry
  const semStart = VIT_SEMESTER_CONFIG.startDate;
  const semEnd = VIT_SEMESTER_CONFIG.endDate;
  const daysElapsed = Math.max(0, Math.floor((istNow - semStart) / (1000 * 60 * 60 * 24)));
  const totalSemDays = Math.floor((semEnd - semStart) / (1000 * 60 * 60 * 24));
  const currentWeek = Math.min(VIT_SEMESTER_CONFIG.totalWeeks, Math.floor(daysElapsed / 7) + 1);
  const semesterProgressPct = Math.min(100, Math.round((daysElapsed / totalSemDays) * 100));

  // Determine active syllabus unit based on 16-week timeline (Weeks 1-4 = Unit 1)
  const currentUnitIndex = Math.min(3, Math.floor((currentWeek - 1) / 4));

  // Check Holiday Status
  const holidayMatch = VIT_SEMESTER_CONFIG.officialHolidays.find(h => h.date === dateISO);
  const isHoliday = !!holidayMatch;
  const holidayName = holidayMatch ? holidayMatch.name : null;

  // Next Upcoming Holiday
  const upcomingHolidays = VIT_SEMESTER_CONFIG.officialHolidays
    .filter(h => h.date > dateISO)
    .map(h => {
      const hDate = new Date(h.date + 'T00:00:00+05:30');
      const diffDays = Math.ceil((hDate - istNow) / (1000 * 60 * 60 * 24));
      return { ...h, daysRemaining: diffDays };
    });
  const nextHoliday = upcomingHolidays[0] || null;

  // 3. Parse Today's Timetable Schedule Matching Batch
  const timetable = Array.isArray(catalog?.timetable) ? catalog.timetable : [];
  const todaySlots = [];

  for (const line of timetable) {
    const [day, timeStr, type, subjectTitle, faculty, room, rawBatch, courseId, uIdxStr, tIdxStr] = line.split('|').map(s => s.trim());
    if (day !== todayDay) continue;

    let batch = rawBatch;
    if (batch === 'B4') batch = 'B1';
    if (batch === 'B5') batch = 'B2';
    if (batch === 'B6') batch = 'B3';

    if (batch !== 'ALL' && userBatch !== 'ALL' && batch !== userBatch) continue;

    const times = parseTimeSlot(timeStr);
    if (!times) continue;

    const course = catalog.courses?.find(c => c.id === courseId);
    const assignedUnitIdx = (uIdxStr !== undefined && uIdxStr !== '') ? Number(uIdxStr) : currentUnitIndex;
    const unit = course?.units?.[assignedUnitIdx] || course?.units?.[0];
    const assignedTopicIdx = (tIdxStr !== undefined && tIdxStr !== '') ? Number(tIdxStr) : 0;
    const topic = unit?.topics?.[assignedTopicIdx] || (unit?.topics ? unit.topics[0] : null);

    todaySlots.push({
      timeStr,
      startMinutes: times.startMinutes,
      endMinutes: times.endMinutes,
      type,
      subjectTitle,
      faculty,
      room,
      batch,
      courseId,
      courseName: course?.name || subjectTitle,
      unitIndex: assignedUnitIdx,
      unitName: unit?.name || `Unit ${assignedUnitIdx + 1}`,
      topicIndex: assignedTopicIdx,
      topicName: topic,
      topicSlug: buildTopicSlug(courseId, assignedUnitIdx, assignedTopicIdx)
    });
  }

  todaySlots.sort((a, b) => a.startMinutes - b.startMinutes);

  const inSession = todaySlots.filter(s => s.startMinutes <= currentMinutes && currentMinutes < s.endMinutes);
  const upcoming = todaySlots.filter(s => currentMinutes < s.startMinutes);
  const completedToday = todaySlots.filter(s => s.endMinutes <= currentMinutes);

  // 4. Smart Free Study Window Detection
  let currentStudyWindow = null;
  if (!isHoliday && inSession.length === 0) {
    if (completedToday.length > 0 && upcoming.length > 0) {
      const prevClass = completedToday[completedToday.length - 1];
      const nextClass = upcoming[0];
      const gapDuration = nextClass.startMinutes - prevClass.endMinutes;
      if (gapDuration >= 30 && currentMinutes >= prevClass.endMinutes && currentMinutes < nextClass.startMinutes) {
        const remainingGap = nextClass.startMinutes - currentMinutes;
        currentStudyWindow = {
          isActive: true,
          totalDurationMinutes: gapDuration,
          remainingMinutes: remainingGap,
          windowLabel: `${formatMinutesToTime(prevClass.endMinutes)} – ${formatMinutesToTime(nextClass.startMinutes)}`,
          recommendedFocus: remainingGap >= 45 ? 'Deep Focus Session' : 'Quick Retention Check & Coffee'
        };
      }
    }
  }

  // 5. Spaced-Repetition: Fetch Real Decaying Topic with Ebbinghaus Curve
  let decayingTopic = null;
  if (db && typeof db.get === 'function') {
    try {
      const rawDecaying = await db.get(
        `SELECT * FROM topic_progress 
         WHERE user_id = ? 
         ORDER BY 
           CASE status WHEN 'decaying' THEN 1 WHEN 'learning' THEN 2 ELSE 3 END,
           mastery_score ASC, 
           last_reviewed_at ASC 
         LIMIT 1`,
        [userId]
      );

      if (rawDecaying) {
        const lastDate = rawDecaying.last_reviewed_at ? new Date(rawDecaying.last_reviewed_at) : semStart;
        const daysSinceReview = Math.max(0, Math.floor((istNow - lastDate) / (1000 * 60 * 60 * 24)));
        const stability = Math.max(2, Math.min(21, (rawDecaying.review_count || 1) * 3));
        const estimatedRetention = Math.max(15, Math.min(100, Math.round(Math.exp(-daysSinceReview / stability) * 100)));

        decayingTopic = {
          ...rawDecaying,
          daysSinceReview,
          estimatedRetention,
          isUrgent: estimatedRetention < 50
        };
      }
    } catch (e) {}
  }

  // 6. Singular Priority Action Logic (Context-Aware Flight Director)
  let priorityAction = null;

  if (isHoliday) {
    priorityAction = {
      actionType: 'HOLIDAY_SPRINT',
      urgency: 'calm',
      title: `🎉 ${holidayName} (Official Holiday)`,
      subtitle: 'No lectures scheduled today. Excellent window for mid-sem prep & lab revisions.',
      cta: '⚡ Launch 45m Deep Work Sprint',
      target: { view: 'study', courseId: 'sat', unitIndex: currentUnitIndex },
      badge: 'OFFICIAL HOLIDAY'
    };
  } else if (inSession.length > 0) {
    const cur = inSession[0];
    priorityAction = {
      actionType: 'IN_SESSION',
      urgency: 'live',
      title: `Currently in ${cur.courseName}`,
      subtitle: `Room ${cur.room} • with ${cur.faculty} (${cur.type})`,
      cta: '📖 Open Live Class Deck',
      target: { view: 'subjects', courseId: cur.courseId, topic: cur.topicName, topicSlug: cur.topicSlug },
      badge: 'LIVE CLASS'
    };
  } else if (upcoming.length > 0 && (upcoming[0].startMinutes - currentMinutes) <= 45) {
    const next = upcoming[0];
    const minsUntil = next.startMinutes - currentMinutes;
    const isLab = next.type.toLowerCase().includes('lab');

    priorityAction = {
      actionType: isLab ? 'LAB_PRE_CHECK' : 'PRE_CLASS_BRIEFING',
      urgency: 'critical',
      title: `${next.courseName} starts in ${minsUntil} mins`,
      subtitle: isLab
        ? `Practical in Room ${next.room}: Verify experiment circuit & code templates`
        : `Today's Focus: ${next.topicName || next.unitName} (Room ${next.room})`,
      cta: isLab ? '🔬 Pre-Lab Readiness Check (3 min)' : '🚀 3-Min Pre-Class Flight Briefing',
      target: { view: 'briefing', courseId: next.courseId, topic: next.topicName, topicSlug: next.topicSlug },
      badge: isLab ? 'LAB PREP' : 'STARTING SOON'
    };
  } else if (completedToday.length > 0 && (currentMinutes - completedToday[completedToday.length - 1].endMinutes) <= 60) {
    const lastClass = completedToday[completedToday.length - 1];
    priorityAction = {
      actionType: 'RETENTION_CHECK',
      urgency: 'high',
      title: `${lastClass.courseName} just concluded`,
      subtitle: `Lock in key concepts: ${lastClass.topicName || "today's lecture"}`,
      cta: '🎯 Quick 3-Question Retention Check',
      target: { view: 'debrief', courseId: lastClass.courseId, topic: lastClass.topicName, topicSlug: lastClass.topicSlug },
      badge: 'POST-CLASS'
    };
  } else if (currentStudyWindow) {
    priorityAction = {
      actionType: 'STUDY_WINDOW',
      urgency: 'normal',
      title: `${currentStudyWindow.remainingMinutes}m Study Window Available`,
      subtitle: `Free slot (${currentStudyWindow.windowLabel}) before ${upcoming[0]?.courseName || 'next lecture'}`,
      cta: `⚡ Launch ${currentStudyWindow.remainingMinutes >= 45 ? '35m' : '20m'} Focus Block`,
      target: { view: 'study' },
      badge: 'FREE WINDOW'
    };
  } else if (decayingTopic) {
    priorityAction = {
      actionType: 'ADAPTIVE_REVISION',
      urgency: decayingTopic.isUrgent ? 'high' : 'normal',
      title: upcoming.length > 0 ? `Next Class: ${upcoming[0].timeStr}` : 'All lectures concluded for today',
      subtitle: `⚡ Review Decaying Topic: ${decayingTopic.topic_id} (Est. Retention: ${decayingTopic.estimatedRetention}%)`,
      cta: '⚡ Launch Spaced Review',
      target: { view: 'study', courseId: decayingTopic.course_id, topicSlug: decayingTopic.topic_id },
      badge: 'SPACED REPETITION'
    };
  } else {
    priorityAction = {
      actionType: 'STUDY_SPRINT',
      urgency: 'normal',
      title: upcoming.length > 0 ? `Next Lecture at ${upcoming[0].timeStr}` : 'Lectures concluded for today',
      subtitle: `Week ${currentWeek} Focus: Unit ${currentUnitIndex + 1} core engineering competencies`,
      cta: '⚡ Launch 25m Focus Sprint',
      target: { view: 'study' },
      badge: 'SELF STUDY'
    };
  }

  // 7. Calculate Real Exam Readiness per Course
  const courseReadiness = [];
  const courses = catalog.courses || [];

  for (const course of courses) {
    let totalTopics = 0;
    course.units?.forEach(u => { totalTopics += (u.topics?.length || 0); });

    let completedCount = 0;
    let avgMastery = 0;

    if (db && typeof db.get === 'function') {
      try {
        const prog = await db.get(
          `SELECT COUNT(*) as cnt, AVG(mastery_score) as avg_mastery 
           FROM topic_progress 
           WHERE user_id = ? AND course_id = ? AND (status = 'mastered' OR status = 'learning')`,
          [userId, course.id]
        );
        completedCount = Number(prog?.cnt || 0);
        avgMastery = Math.round(Number(prog?.avg_mastery || 0));
      } catch (e) {}
    }

    const coveragePercent = totalTopics > 0 ? Math.round((completedCount / totalTopics) * 100) : 0;
    const readinessScore = Math.min(100, Math.round(0.6 * coveragePercent + 0.4 * avgMastery));

    courseReadiness.push({
      courseId: course.id,
      code: course.code,
      name: course.name,
      totalTopics,
      completedTopics: completedCount,
      coveragePercent,
      avgMastery,
      readinessScore
    });
  }

  const overallReadiness = courseReadiness.length > 0
    ? Math.round(courseReadiness.reduce((acc, c) => acc + c.readinessScore, 0) / courseReadiness.length)
    : 0;

  // 8. Official Examination Milestones
  const mseDate = VIT_SEMESTER_CONFIG.midSemExamDate;
  const eseDate = VIT_SEMESTER_CONFIG.endSemExamDate;
  const daysToMSE = Math.max(0, Math.ceil((mseDate - istNow) / (1000 * 60 * 60 * 24)));
  const daysToESE = Math.max(0, Math.ceil((eseDate - istNow) / (1000 * 60 * 60 * 24)));

  return {
    today: todayDay,
    dateISO,
    timeIST: `${String(istNow.getHours()).padStart(2, '0')}:${String(istNow.getMinutes()).padStart(2, '0')}`,
    academicCalendar: {
      semester: VIT_SEMESTER_CONFIG.semesterName,
      currentWeek,
      totalWeeks: VIT_SEMESTER_CONFIG.totalWeeks,
      activeUnitIndex: currentUnitIndex,
      activeUnitLabel: `Unit ${currentUnitIndex + 1}`,
      semesterProgressPct,
      isHoliday,
      holidayName,
      nextHoliday
    },
    batch: userBatch,
    currentClass: inSession[0] || null,
    nextClass: upcoming[0] || null,
    currentStudyWindow,
    priorityAction,
    decayingTopic,
    courseReadiness,
    overallReadiness,
    todaySchedule: isHoliday ? [] : todaySlots,
    allSlotsToday: todaySlots,
    examCountdown: {
      midSem: {
        exam: 'Mid-Sem Examination (MSE)',
        date: '26 Oct 2026',
        daysRemaining: daysToMSE
      },
      endSem: {
        exam: 'End-Sem Examination (ESE)',
        date: '14 Dec 2026',
        daysRemaining: daysToESE
      }
    }
  };
}