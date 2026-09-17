(() => {
  function isSignedIn() {
    return Boolean(localStorage.getItem('flux_access_token'));
  }

  function courseIdForSubjectCode(code) {
    return coursesData.find(item => item.code === code)?.id || 'sat';
  }

  function enrolledSubjectIdForCourse(courseId) {
    const course = coursesData.find(item => item.id === courseId);
    if (!course) throw new Error('Selected course is not available.');
    const enrolled = currentUser?.enrolled_subjects?.find(item => item.code === course.code);
    if (!enrolled?.id) throw new Error(`${course.code} is not linked to your backend enrollment.`);
    return Number(enrolled.id);
  }

  async function request(path, options = {}) {
    const token = localStorage.getItem('flux_access_token');
    if (!token) throw new Error('Please sign in to sync student data.');
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        Authorization: `Bearer ${token}`,
        ...(options.headers || {})
      }
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.message || payload?.detail || `Request failed (${response.status}).`);
    }
    return payload;
  }

  function assignmentPayload(item) {
    return {
      client_id: String(item.id),
      subject_id: enrolledSubjectIdForCourse(item.courseId),
      topic: item.topic || null,
      title: item.title,
      due_text: item.due || null,
      priority: item.priority || 'med',
      is_done: Boolean(item.done)
    };
  }

  function notePayload(item) {
    return {
      client_id: String(item.id),
      subject_id: enrolledSubjectIdForCourse(item.courseId),
      topic: item.topic || null,
      title: item.title,
      content: item.content || ''
    };
  }

  function mapAssignments(rows) {
    return rows.map(row => ({
      id: row.client_id,
      courseId: courseIdForSubjectCode(row.subject_code),
      topic: row.topic || '',
      title: row.title,
      due: row.due_text || '',
      priority: row.priority || 'med',
      done: Boolean(row.is_done)
    }));
  }

  function mapNotes(rows) {
    return rows.map(row => ({
      id: row.client_id,
      courseId: courseIdForSubjectCode(row.subject_code),
      topic: row.topic || '',
      title: row.title,
      content: row.content,
      date: new Date(row.updated_at).toLocaleDateString()
    }));
  }

  async function hydrateStudentContent() {
    if (!isSignedIn() || !currentUser?.enrolled_subjects?.length) return;
    try {
      const assignmentItems = assignments.map(assignmentPayload);
      const noteItems = notesList
        .filter(item => String(item.content || '').trim())
        .map(notePayload);

      const [backendAssignments, backendNotes] = await Promise.all([
        request('/student-data/assignments/sync', {
          method: 'POST',
          body: JSON.stringify({ items: assignmentItems })
        }),
        request('/student-data/notes/sync', {
          method: 'POST',
          body: JSON.stringify({ items: noteItems })
        })
      ]);

      assignments = mapAssignments(backendAssignments);
      notesList = mapNotes(backendNotes);
      localStorage.setItem('flux_assignments', JSON.stringify(assignments));
      localStorage.setItem('flux_notes_v2', JSON.stringify(notesList));
      renderAssignmentsFull();
      renderNotes();
      renderDashboard();
    } catch (error) {
      console.warn('Student content sync failed:', error);
    }
  }

  window.toggleAssignment = async function toggleAssignmentSynced(id) {
    const assignment = assignments.find(item => item.id === id);
    if (!assignment) return;
    const nextDone = !assignment.done;

    if (!isSignedIn()) {
      assignment.done = nextDone;
      localStorage.setItem('flux_assignments', JSON.stringify(assignments));
      renderAssignmentsFull();
      renderDashboard();
      return;
    }

    try {
      const saved = await request(`/student-data/assignments/${encodeURIComponent(id)}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_done: nextDone })
      });
      assignment.done = Boolean(saved.is_done);
      localStorage.setItem('flux_assignments', JSON.stringify(assignments));
      renderAssignmentsFull();
      renderDashboard();
    } catch (error) {
      alert(`Assignment was not synced: ${error.message}`);
      renderAssignmentsFull();
    }
  };

  window.saveNewNote = async function saveNewNoteSynced() {
    const courseId = document.getElementById('modal-note-course')?.value;
    const topic = document.getElementById('modal-note-topic')?.value || '';
    const title = document.getElementById('modal-note-title')?.value.trim() || 'Untitled Note';
    const content = document.getElementById('modal-note-content')?.value.trim() || '';
    if (!content) {
      alert('Write something in the note before saving.');
      return;
    }

    const localNote = {
      id: `n_${Date.now()}`,
      courseId,
      topic,
      title,
      content,
      date: 'Today'
    };

    if (!isSignedIn()) {
      notesList.unshift(localNote);
      localStorage.setItem('flux_notes_v2', JSON.stringify(notesList));
      closeNewNoteModal();
      renderNotes();
      return;
    }

    try {
      const saved = await request('/student-data/notes', {
        method: 'POST',
        body: JSON.stringify(notePayload(localNote))
      });
      notesList.unshift(mapNotes([saved])[0]);
      localStorage.setItem('flux_notes_v2', JSON.stringify(notesList));
      closeNewNoteModal();
      renderNotes();
      renderDashboard();
    } catch (error) {
      alert(`Note was not saved to FLUX ONE: ${error.message}`);
    }
  };

  window.deleteNote = async function deleteNoteSynced(id) {
    if (!confirm('Delete this note?')) return;

    if (isSignedIn()) {
      try {
        await request(`/student-data/notes/${encodeURIComponent(id)}`, { method: 'DELETE' });
      } catch (error) {
        alert(`Note was not deleted: ${error.message}`);
        return;
      }
    }

    notesList = notesList.filter(note => note.id !== id);
    localStorage.setItem('flux_notes_v2', JSON.stringify(notesList));
    renderNotes();
    renderDashboard();
  };

  const originalShowAppView = window.showAppView;
  if (typeof originalShowAppView === 'function') {
    window.showAppView = function showAppViewWithContentSync(user) {
      const result = originalShowAppView(user);
      queueMicrotask(hydrateStudentContent);
      return result;
    };
  }

  setTimeout(() => {
    if (typeof currentUser !== 'undefined' && currentUser && isSignedIn()) {
      hydrateStudentContent();
    }
  }, 800);

  window.__fluxContentSync = { hydrateStudentContent };
})();
