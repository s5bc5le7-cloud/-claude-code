(() => {
  'use strict';

  const STORAGE_KEY = 'reminder.tasks.v1';

  /** @typedef {{id:string, title:string, done:boolean, dueAt:string|null, createdAt:number}} Task */

  /** @type {Task[]} */
  let tasks = loadTasks();
  let currentFilter = 'active'; // 'active' | 'all' | 'done'

  // --- DOM refs ---
  const taskListEl = document.getElementById('taskList');
  const emptyStateEl = document.getElementById('emptyState');
  const addFormEl = document.getElementById('addForm');
  const taskInputEl = document.getElementById('taskInput');
  const dueToggleBtn = document.getElementById('dueToggleBtn');
  const dueRowEl = document.getElementById('dueRow');
  const dueDateEl = document.getElementById('dueDate');
  const dueTimeEl = document.getElementById('dueTime');
  const dueClearBtn = document.getElementById('dueClearBtn');
  const clearDoneBtn = document.getElementById('clearDoneBtn');
  const todayLabelEl = document.getElementById('todayLabel');
  const segBtns = Array.from(document.querySelectorAll('.seg-btn'));

  // --- storage ---
  function loadTasks() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function saveTasks() {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(tasks));
  }

  function uid() {
    return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
  }

  // --- mutations ---
  function addTask(title, dueAt) {
    const trimmed = title.trim();
    if (!trimmed) return;
    tasks.push({
      id: uid(),
      title: trimmed,
      done: false,
      dueAt: dueAt || null,
      createdAt: Date.now(),
    });
    saveTasks();
    render();
  }

  function toggleDone(id) {
    const t = tasks.find((x) => x.id === id);
    if (!t) return;
    t.done = !t.done;
    saveTasks();
    render();
  }

  function deleteTask(id) {
    tasks = tasks.filter((x) => x.id !== id);
    saveTasks();
    render();
  }

  function clearDone() {
    tasks = tasks.filter((x) => !x.done);
    saveTasks();
    render();
  }

  // --- helpers ---
  function formatDue(iso) {
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) return '';
    const today = new Date();
    const isToday = d.toDateString() === today.toDateString();
    const dateStr = isToday
      ? '今日'
      : d.toLocaleDateString('ja-JP', { month: 'short', day: 'numeric', weekday: 'short' });
    const hasTime = iso.includes('T') && (d.getHours() !== 0 || d.getMinutes() !== 0);
    const timeStr = hasTime ? d.toLocaleTimeString('ja-JP', { hour: '2-digit', minute: '2-digit' }) : '';
    return timeStr ? `${dateStr} ${timeStr}` : dateStr;
  }

  function isOverdue(task) {
    if (!task.dueAt || task.done) return false;
    return new Date(task.dueAt).getTime() < Date.now();
  }

  function getFiltered() {
    let list = tasks;
    if (currentFilter === 'active') list = tasks.filter((t) => !t.done);
    else if (currentFilter === 'done') list = tasks.filter((t) => t.done);

    return [...list].sort((a, b) => {
      if (!!a.dueAt !== !!b.dueAt) return a.dueAt ? -1 : 1;
      if (a.dueAt && b.dueAt) return new Date(a.dueAt) - new Date(b.dueAt);
      return b.createdAt - a.createdAt;
    });
  }

  // --- rendering ---
  function render() {
    const filtered = getFiltered();
    taskListEl.innerHTML = '';

    for (const task of filtered) {
      taskListEl.appendChild(renderTaskItem(task));
    }

    emptyStateEl.hidden = filtered.length !== 0;
  }

  function renderTaskItem(task) {
    const li = document.createElement('li');
    li.className = 'task-item' + (task.done ? ' done' : '');
    li.dataset.id = task.id;

    const checkBtn = document.createElement('button');
    checkBtn.type = 'button';
    checkBtn.className = 'check-btn';
    checkBtn.setAttribute('aria-label', task.done ? '未完了に戻す' : '完了にする');
    checkBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M9 16.2 4.8 12l-1.4 1.4L9 19 20.6 7.4 19.2 6z"/></svg>';
    checkBtn.addEventListener('click', () => toggleDone(task.id));

    const body = document.createElement('div');
    body.className = 'task-body';

    const title = document.createElement('div');
    title.className = 'task-title';
    title.textContent = task.title;
    body.appendChild(title);

    if (task.dueAt) {
      const due = document.createElement('div');
      due.className = 'task-due' + (isOverdue(task) ? ' overdue' : '');
      due.textContent = formatDue(task.dueAt);
      body.appendChild(due);
    }

    const delBtn = document.createElement('button');
    delBtn.type = 'button';
    delBtn.className = 'delete-btn';
    delBtn.setAttribute('aria-label', '削除');
    delBtn.innerHTML = '<svg viewBox="0 0 24 24"><path d="M12 10.6 6.7 5.3 5.3 6.7 10.6 12l-5.3 5.3 1.4 1.4L12 13.4l5.3 5.3 1.4-1.4L13.4 12l5.3-5.3-1.4-1.4z"/></svg>';
    delBtn.addEventListener('click', () => deleteTask(task.id));

    li.append(checkBtn, body, delBtn);
    return li;
  }

  function renderTodayLabel() {
    const now = new Date();
    todayLabelEl.textContent = now.toLocaleDateString('ja-JP', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      weekday: 'short',
    });
  }

  // --- events ---
  addFormEl.addEventListener('submit', (e) => {
    e.preventDefault();
    let dueAt = null;
    if (!dueRowEl.hidden && dueDateEl.value) {
      dueAt = dueTimeEl.value
        ? `${dueDateEl.value}T${dueTimeEl.value}`
        : `${dueDateEl.value}T00:00`;
    }
    addTask(taskInputEl.value, dueAt);
    taskInputEl.value = '';
    dueDateEl.value = '';
    dueTimeEl.value = '';
    dueRowEl.hidden = true;
    taskInputEl.focus();
  });

  dueToggleBtn.addEventListener('click', () => {
    dueRowEl.hidden = !dueRowEl.hidden;
  });

  dueClearBtn.addEventListener('click', () => {
    dueDateEl.value = '';
    dueTimeEl.value = '';
    dueRowEl.hidden = true;
  });

  clearDoneBtn.addEventListener('click', () => {
    if (tasks.some((t) => t.done)) clearDone();
  });

  segBtns.forEach((btn) => {
    btn.addEventListener('click', () => {
      segBtns.forEach((b) => {
        b.classList.remove('active');
        b.setAttribute('aria-selected', 'false');
      });
      btn.classList.add('active');
      btn.setAttribute('aria-selected', 'true');
      currentFilter = btn.dataset.filter;
      render();
    });
  });

  // --- init ---
  renderTodayLabel();
  render();

  if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('sw.js').catch(() => {
        /* ignore registration failures (e.g. file:// or unsupported env) */
      });
    });
  }
})();
