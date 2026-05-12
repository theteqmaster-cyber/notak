/* ═══════════════════════════════════════════════════════════════
   app.js — Notak NServer SPA
   ═══════════════════════════════════════════════════════════════ */

'use strict';

// ── Auth System ────────────────────────────────────────────────
let _notakPassword = localStorage.getItem('notak_password') || '';

function checkAuth() {
  if (_notakPassword !== 'wish26') {
    document.getElementById('login-overlay').style.display = 'flex';
    document.getElementById('login-password').focus();
    return false;
  }
  document.getElementById('login-overlay').style.display = 'none';
  return true;
}

async function attemptLogin() {
  const pw = document.getElementById('login-password').value;
  if (pw === 'wish26') {
    _notakPassword = pw;
    localStorage.setItem('notak_password', pw);
    document.getElementById('login-overlay').style.display = 'none';
    toast('Access granted', 'success');
    loadHome();
  } else {
    toast('Invalid password', 'error');
  }
}

function logout() {
  localStorage.removeItem('notak_password');
  location.reload();
}

// ── SocketIO heartbeat ─────────────────────────────────────────
const socket = io({ transports: ['websocket', 'polling'] });
const CLIENT_ID = Math.random().toString(36).slice(2);
let currentPage = 'home';

socket.on('connect', () => {
  sendHeartbeat();
  setInterval(sendHeartbeat, 10000);
});
function sendHeartbeat() {
  socket.emit('heartbeat', { client_id: CLIENT_ID, username: 'Web User', page: currentPage });
}

// ── Toast system ───────────────────────────────────────────────
function toast(msg, type = 'info') {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Navigation ─────────────────────────────────────────────────
function navigate(page) {
  if (!checkAuth()) return;
  currentPage = page;
  
  if (_sidebarOpen) toggleSidebar();

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  const pageEl = document.getElementById('page-' + page);
  if (pageEl) pageEl.classList.add('active');
  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  if (page === 'home')     loadHome();
  if (page === 'vault')    loadVault();
  if (page === 'music')    loadMusic();
  if (page === 'radio')    loadRadio();
  if (page === 'calendar') loadCalendar();
  if (page === 'session')  loadSessionHistory();
  if (page === 'mboard')   initMboard();
  if (page === 'notes')    loadNotesCourses();
}

// ── API helpers ────────────────────────────────────────────────
async function api(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  opts.headers['X-Notak-Password'] = _notakPassword;
  
  const r = await fetch(url, opts);
  if (r.status === 401) {
    _notakPassword = '';
    localStorage.removeItem('notak_password');
    checkAuth();
    throw new Error('Unauthorized');
  }
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
async function apiPost(url, body) {
  return api(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
}

function getStreamUrl(url) {
  const sep = url.includes('?') ? '&' : '?';
  return `${url}${sep}pw=${_notakPassword}`;
}

function fmtSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / 1048576).toFixed(1) + ' MB';
}
function fileIcon(cat) {
  const m = { PDFs: '📄', Notes: '📝', Images: '🖼️', Slides: '📊', Audio: '🎵', Files: '📁' };
  return m[cat] || '📁';
}

// ═══════════════════════════════════════════════════════════════
// HOME
// ═══════════════════════════════════════════════════════════════
async function loadHome() {
  try {
    const hour = new Date().getHours();
    let greeting = 'Good evening';
    if (hour < 12) greeting = 'Good morning';
    else if (hour < 18) greeting = 'Good afternoon';
    
    if (document.getElementById('home-greeting')) {
      document.getElementById('home-greeting').textContent = `${greeting} 👋`;
      document.getElementById('home-date').textContent = new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
    }

    const [status, courses, files, sessions, upcoming] = await Promise.allSettled([
      api('/api/status'), api('/api/vault/courses'), api('/api/vault/files?course=all'), api('/api/sessions'), api('/api/calendar/upcoming')
    ]);

    // Stats
    if (status.status === 'fulfilled' && courses.status === 'fulfilled' && files.status === 'fulfilled') {
      const statsHTML = `
        <div class="stat-badge">📚 ${files.value.length} Notes & Files</div>
        <div class="stat-badge">🎓 ${courses.value.length} Courses</div>
        <div class="stat-badge">📡 ${status.value.client_count} Devices Connected</div>
      `;
      document.getElementById('home-vital-stats').innerHTML = statsHTML;
    }

    // Recent Files
    if (files.status === 'fulfilled') {
      const recent = files.value.slice(0, 4);
      const container = document.getElementById('widget-recent-files');
      if (container) {
        if (recent.length === 0) container.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:12px;">No recent files.</div>';
        else container.innerHTML = recent.map(f => `
          <div class="file-card" onclick="navigate('vault')" style="background:rgba(255,255,255,0.02); margin-bottom:8px; border:1px solid rgba(255,255,255,0.05); padding:10px; border-radius:8px; cursor:pointer;">
            <div class="file-icon">${fileIcon(f.category)}</div>
            <div class="file-info"><div class="file-name" style="font-size:13px;">${f.name}</div><div class="file-meta" style="font-size:11px;">${f.course}</div></div>
          </div>`).join('');
      }
    }

    // Music
    try {
      let queue = typeof _playlist !== 'undefined' ? _playlist : [];
      if (queue.length === 0) {
        queue = await api('/api/music/playlist');
        if (typeof _playlist !== 'undefined') _playlist = queue;
      }
      const titleEl = document.getElementById('dash-music-title');
      const queueEl = document.getElementById('dash-music-queue');
      if (titleEl && queueEl) {
        if (queue && queue.length > 0) {
          let cIdx = typeof _musicIdx !== 'undefined' && _musicIdx >= 0 ? _musicIdx : 0;
          titleEl.textContent = queue[cIdx].name;
          queueEl.innerHTML = queue.slice(0, 5).map((track, idx) => `
            <div style="padding:6px; background:rgba(255,255,255,0.02); border-radius:4px; cursor:pointer; display:flex; gap:8px; align-items:center;" onclick="navigate('music'); playTrack(${idx})">
               <div style="font-size:10px; color:var(--text-muted); width:16px; text-align:center;">${idx === cIdx ? '▶' : idx+1}</div>
               <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${track.name}</div>
            </div>`).join('');
        } else {
          titleEl.textContent = 'Ready to play';
          queueEl.innerHTML = '<div style="color:var(--text-muted);font-size:11px;text-align:center;">No tracks found</div>';
        }
      }
    } catch(e) {}

    // Sessions
    if (sessions.status === 'fulfilled') {
      renderSessionGraph(sessions.value);
    }

    // Calendar
    if (upcoming.status === 'fulfilled') {
      const calEl = document.getElementById('widget-upcoming-events');
      if (calEl) {
        if (!upcoming.value || upcoming.value.length === 0) calEl.innerHTML = '<div style="color:var(--text-muted);font-size:12px;padding:12px;text-align:center;">No upcoming events.</div>';
        else calEl.innerHTML = upcoming.value.slice(0, 3).map(ev => `
          <div style="display:flex; gap:12px; align-items:center; padding:10px; background:rgba(255,255,255,0.02); border-radius:8px; border:1px solid rgba(255,255,255,0.05); cursor:pointer;" onclick="navigate('calendar')">
            <div style="font-weight:800; color:var(--accent); font-size:12px;">${ev.time ? ev.time.slice(0,5) : ''}</div>
            <div style="flex:1; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; font-size:13px;">${ev.title}</div>
          </div>`).join('');
      }
    }

  } catch (e) {
    console.error("Dashboard failed to load:", e);
  }
}

// ═══════════════════════════════════════════════════════════════
// VAULT / STUDY HUB
// ═══════════════════════════════════════════════════════════════
let _vaultFiles = [];
let _currentCourse = 'all';
let _currentCat = 'all';
let _currentFileId = null;

async function loadVault() {
  try {
    const courses = await api('/api/vault/courses');
    const courseList = document.getElementById('course-list');
    const allCourses = ['all', ...courses];
    courseList.innerHTML = allCourses.map(c => `
      <div class="course-item ${c === _currentCourse ? 'active' : ''}" onclick="selectCourse('${c}')">
        ${c === 'all' ? '🌍' : '📚'} ${c === 'all' ? 'All Library' : c}
      </div>`).join('');
    await loadVaultFiles();
  } catch(e) { toast('Could not load vault', 'error'); }
}

async function loadVaultFiles() {
  try {
    _vaultFiles = await api(`/api/vault/files?course=${_currentCourse}`);
    filterFiles();
  } catch(e) { console.error(e); }
}

function selectCourse(course) {
  _currentCourse = course;
  document.querySelectorAll('.course-item').forEach(el => {
    el.classList.toggle('active', el.textContent.trim().includes(course === 'all' ? 'All Library' : course));
  });
  loadVaultFiles();
}

function setCat(cat) {
  _currentCat = cat;
  document.querySelectorAll('.cat-tab').forEach(t => t.classList.toggle('active', t.dataset.cat === cat));
  filterFiles();
}

function filterFiles() {
  const q = (document.getElementById('vault-search').value || '').toLowerCase();
  const filtered = _vaultFiles.filter(f =>
    (f.name || '').toLowerCase().includes(q) &&
    (_currentCat === 'all' || f.category === _currentCat)
  );
  document.getElementById('file-list').innerHTML = filtered.length
    ? filtered.map(f => `
        <div class="file-card ${f.id === _currentFileId ? 'active' : ''}" onclick="openFile(${f.id})">
          <div class="file-icon">${fileIcon(f.category)}</div>
          <div class="file-info">
            <div class="file-name">${f.name}</div>
            <div class="file-meta">${f.category}</div>
          </div>
        </div>`).join('')
    : `<div class="empty-state"><div>No files found</div></div>`;
}

async function openFile(id) {
  _currentFileId = id;
  filterFiles();
  try {
    const f = await api(`/api/vault/file/${id}`);
    const ext = (f.name || '').split('.').pop().toLowerCase();
    const viewer = document.getElementById('viewer-content');
    const streamUrl = getStreamUrl(`/stream/file/${id}`);

    if (['pdf'].includes(ext)) {
      viewer.innerHTML = `<iframe src="${streamUrl}" style="width:100%;height:100%;border:none;border-radius:10px;background:#111;"></iframe>`;
    } else if (['png','jpg','jpeg','gif','webp'].includes(ext)) {
      viewer.innerHTML = `<img src="${streamUrl}" style="max-width:100%;max-height:80vh;border-radius:12px;object-fit:contain;"/>`;
    } else if (['mp3','m4a','wav','ogg','flac'].includes(ext)) {
      const mime = ext === 'm4a' ? 'audio/mp4' : ext === 'mp3' ? 'audio/mpeg' : 'audio/' + ext;
      viewer.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;gap:20px;padding:40px;">
          <div style="font-size:64px;">🎵</div>
          <div style="font-size:18px;font-weight:700;">${f.name}</div>
          <audio controls style="width:100%;max-width:420px;accent-color:var(--accent);">
            <source src="${streamUrl}" type="${mime}"/>
            Your browser does not support audio.
          </audio>
        </div>`;
    } else if (['md','txt','csv'].includes(ext)) {
      const resp = await fetch(streamUrl);
      const text = await resp.text();
      viewer.innerHTML = `<pre style="white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.7;color:#ddd;padding:8px;">${escHtml(text)}</pre>`;
    } else {
      viewer.innerHTML = `
        <div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);">
          <div style="font-size:48px;">${fileIcon(f.category)}</div>
          <div style="font-size:16px;font-weight:600;">${f.name}</div>
          <div style="font-size:13px;">Preview not available in browser</div>
          <a href="${streamUrl}" download="${f.name}" class="btn btn-primary">⬇ Download</a>
        </div>`;
    }
  } catch(e) { toast('Could not load file', 'error'); }
}

function escHtml(s) {
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ═══════════════════════════════════════════════════════════════
// DEEP SEARCH
// ═══════════════════════════════════════════════════════════════
async function doSearch() {
  const q = document.getElementById('deep-search-input').value.trim();
  if (!q) return;
  document.getElementById('search-results').innerHTML = '<div style="color:var(--text-muted);padding:16px;">Searching…</div>';
  try {
    const results = await api(`/api/vault/search?q=${encodeURIComponent(q)}`);
    if (!results.length) {
      document.getElementById('search-results').innerHTML = '<div class="empty-state"><div>No results found</div></div>';
      return;
    }
    document.getElementById('search-results').innerHTML = results.map(r => `
      <div class="search-result">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
          <span>${fileIcon(r.category)}</span>
          <span style="font-weight:600;">${r.name}</span>
          <span class="pill pill-muted">${r.course}</span>
          <span class="pill pill-purple">${r.category}</span>
        </div>
        <div class="search-snippet">${r.snippet || 'No preview available'}</div>
      </div>`).join('');
  } catch(e) { toast('Search failed', 'error'); }
}

// ═══════════════════════════════════════════════════════════════
// NOTES
// ═══════════════════════════════════════════════════════════════
async function loadNotesCourses() {
  try {
    const courses = await api('/api/vault/courses');
    const sel = document.getElementById('note-course');
    sel.innerHTML = ['Inbox', ...courses].map(c => `<option value="${c}">${c}</option>`).join('');
  } catch(e) {}
}


let _sidebarOpen = false;
function toggleSidebar() {
  _sidebarOpen = !_sidebarOpen;
  document.getElementById('sidebar').classList.toggle('open', _sidebarOpen);
}

function updateClock() {
  const now = new Date();
  const opts = { hour: '2-digit', minute: '2-digit', second: '2-digit' };
  document.getElementById('header-clock').textContent = now.toLocaleTimeString([], opts);
}
setInterval(updateClock, 1000);
updateClock();

let _qnSaveTimer = null;
let _qnFileId = null;

function onQnEditorInput() {
  document.getElementById('qn-editor-status').textContent = 'EDITING…';
  clearTimeout(_qnSaveTimer);
  _qnSaveTimer = setTimeout(() => saveQuickNote(true), 2000);
}

async function saveQuickNote(isAuto = false) {
  const wysiwyg = document.getElementById('qn-note-wysiwyg');
  const md = htmlToMd(wysiwyg).trim();
  const course  = document.getElementById('note-course').value;
  
  if (!md) return;

  if (!isAuto) document.getElementById('qn-editor-status').textContent = 'SAVING…';
  try {
    const payload = { content: md, course: course };
    if (_qnFileId) payload.file_id = _qnFileId;
    
    const r = await fetch('/api/vault/note?pw=' + _notakPassword, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await r.json();
    if (r.ok && data.ok) {
      if (data.file_id) _qnFileId = data.file_id;
      document.getElementById('qn-editor-status').textContent = 'SAVED ✓';
      if (!isAuto) toast('Note saved to vault ✅', 'success');
    } else {
      document.getElementById('qn-editor-status').textContent = 'SAVE ERROR';
    }
  } catch(e) { 
    document.getElementById('qn-editor-status').textContent = 'SAVE ERROR'; 
  }
}

function createNewNoteInVault() {
  _edFileId = 'new_vault_note';
  document.getElementById('viewer-content').style.display = 'none';
  document.getElementById('note-editor-panel').style.display = 'flex';
  document.getElementById('note-wysiwyg').innerHTML = '<h1>Untitled Note</h1><p><br></p>';
  document.getElementById('note-wysiwyg').focus();
  setEdStatus('SAVING…', '');
  saveNote_wysiwyg();
}

function qnCmd(cmd) {
  document.getElementById('qn-note-wysiwyg').focus();
  document.execCommand(cmd, false, null);
}

function qnHeading(level) {
  document.getElementById('qn-note-wysiwyg').focus();
  document.execCommand('formatBlock', false, `h${level}`);
}

function qnHRule() {
  document.getElementById('qn-note-wysiwyg').focus();
  document.execCommand('insertHorizontalRule', false, null);
}

function qnKeyDown(e) {
  if (e.key === 'Tab') {
    e.preventDefault();
    document.execCommand('insertText', false, '    ');
  }
}

function formatQuickNoteWithAI() {
  const wysiwyg = document.getElementById('qn-note-wysiwyg');
  const md = htmlToMd(wysiwyg);
  if (!md.trim()) { toast('Note is empty', 'error'); return; }

  _aiFormatMode = true;
  _edFileId = 'quick_note'; // Special flag for AI formatting
  if (!_aiOpen) toggleAIPanel();
  document.getElementById('ai-context-bar').style.display = 'flex';
  document.getElementById('qn-editor-status').textContent = 'AI FORMATTING…';

  sendAIMessage(`Format and improve this note:\n\n${md}`);
}


// ═══════════════════════════════════════════════════════════════
// CALENDAR
// ═══════════════════════════════════════════════════════════════
let _calDate = new Date();
let _calSelected = new Date();
let _calEventDates = new Set();

async function loadCalendar() {
  await fetchEventDates();
  renderCalendar();
  loadEventsForDate(_calSelected);
}

async function fetchEventDates() {
  const ym = `${_calDate.getFullYear()}-${String(_calDate.getMonth()+1).padStart(2,'0')}`;
  try {
    const dates = await api(`/api/calendar/events/month?month=${ym}`);
    _calEventDates = new Set(dates);
  } catch(e) {}
}

function renderCalendar() {
  const y = _calDate.getFullYear();
  const m = _calDate.getMonth();
  const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
  document.getElementById('cal-month-label').textContent = `${months[m]} ${y}`;

  const first = new Date(y, m, 1).getDay();
  const days  = new Date(y, m+1, 0).getDate();
  const prevDays = new Date(y, m, 0).getDate();
  const today = new Date();
  const todayStr = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
  const selStr = `${_calSelected.getFullYear()}-${String(_calSelected.getMonth()+1).padStart(2,'0')}-${String(_calSelected.getDate()).padStart(2,'0')}`;

  let html = '';
  for (let i = 0; i < first; i++) {
    html += `<div class="mini-day" style="opacity:0.2">${prevDays - first + 1 + i}</div>`;
  }
  for (let d = 1; d <= days; d++) {
    const dateStr = `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const isToday = dateStr === todayStr;
    const isSel   = dateStr === selStr;
    const hasDot  = _calEventDates.has(dateStr);
    html += `<div class="mini-day ${isToday?'today':''} ${isSel?'selected':''}" onclick="selectDate('${dateStr}')">
      ${d}${hasDot ? '<div class="mini-day-dot" style="background:currentColor"></div>' : ''}
    </div>`;
  }
  document.getElementById('cal-days').innerHTML = html;
}

function selectDate(dateStr) {
  _calSelected = new Date(dateStr + 'T12:00:00');
  renderCalendar();
  loadEventsForDate(_calSelected);
}

async function loadEventsForDate(date) {
  const dateStr = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}`;
  document.getElementById('cal-selected-label').textContent = date.toLocaleDateString('en-US', { weekday:'long', month:'long', day:'numeric' });
  try {
    const events = await api(`/api/calendar/events?date=${dateStr}`);
    
    const countEl = document.getElementById('cal-event-count');
    if (countEl) countEl.textContent = `${events.length} Event${events.length!==1?'s':''}`;

    document.getElementById('cal-events').innerHTML = events.length
      ? events.map(e => `
          <div class="timeline-card" style="border-left: 4px solid var(--primary);">
            <div class="timeline-time">All Day</div>
            <div class="timeline-content">
              <div class="timeline-title">${e.title}</div>
              ${e.description ? `<div class="timeline-desc">${e.description}</div>` : ''}
            </div>
            <button class="btn btn-ghost btn-sm btn-icon" onclick="deleteEvent(${e.id},'${dateStr}')" style="align-self:flex-start">✕</button>
          </div>`).join('')
      : `<div style="text-align:center; padding: 40px 0; color:var(--text-muted);">
           <div style="font-size:32px; margin-bottom:12px; opacity:0.5;">☕</div>
           <div style="font-weight:600; font-size:14px;">Free Day</div>
           <div style="font-size:12px; margin-top:4px;">No events scheduled for this day.</div>
         </div>`;
  } catch(e) {}
}

async function deleteEvent(id, dateStr) {
  try {
    await fetch(`/api/calendar/event/${id}`, { method: 'DELETE' });
    await loadEventsForDate(new Date(dateStr + 'T12:00:00'));
    await fetchEventDates(); renderCalendar();
    toast('Event deleted', 'info');
  } catch(e) { toast('Delete failed', 'error'); }
}

function calPrev() { _calDate.setMonth(_calDate.getMonth()-1); fetchEventDates().then(renderCalendar); }
function calNext() { _calDate.setMonth(_calDate.getMonth()+1); fetchEventDates().then(renderCalendar); }

function showAddEvent() {
  const dateStr = `${_calSelected.getFullYear()}-${String(_calSelected.getMonth()+1).padStart(2,'0')}-${String(_calSelected.getDate()).padStart(2,'0')}`;
  showModal(`
    <div class="modal-title">Add Event</div>
    <div class="form-group">
      <label class="form-label">Date</label>
      <input class="input" id="ev-date" type="date" value="${dateStr}"/>
    </div>
    <div class="form-group">
      <label class="form-label">Title</label>
      <input class="input" id="ev-title" placeholder="Event title…"/>
    </div>
    <div class="form-group">
      <label class="form-label">Description (optional)</label>
      <input class="input" id="ev-desc" placeholder="Details…"/>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="submitEvent()">Add Event</button>
    </div>`);
}

async function submitEvent() {
  const date  = document.getElementById('ev-date').value;
  const title = document.getElementById('ev-title').value.trim();
  const desc  = document.getElementById('ev-desc').value.trim();
  if (!date || !title) { toast('Date and title required', 'error'); return; }
  try {
    await apiPost('/api/calendar/event', { date, title, description: desc });
    closeModal(); toast('Event added ✅', 'success');
    await fetchEventDates(); renderCalendar();
    loadEventsForDate(new Date(date + 'T12:00:00'));
  } catch(e) { toast('Failed to add event', 'error'); }
}

// ── Modal helpers ──────────────────────────────────────────────
function showModal(html) {
  document.getElementById('modal-root').innerHTML = `
    <div class="modal-backdrop" onclick="if(event.target===this)closeModal()">
      <div class="modal">${html}</div>
    </div>`;
}
function closeModal() { document.getElementById('modal-root').innerHTML = ''; }

// ═══════════════════════════════════════════════════════════════
// SESSIONS
// ═══════════════════════════════════════════════════════════════
let _sessionTimer = null;
let _sessionTotal = 0;
let _sessionLeft  = 0;
const CIRCUMFERENCE = 2 * Math.PI * 80; // r=80

// ── Focus Forest Engine (PREMIUM ISOMETRIC) ──
let _forestTrees = [];
let _clouds = []; // For atmospheric clouds
let _selectedTreeType = 'pine';
let _forestAnimReq = null;
const TILE_W = 70;
const TILE_H = 35;
const TILE_DEPTH = 12; // Thickness of the land
const GRID_SIZE = 6;

function initForest() {
  const canvas = document.getElementById('forest-canvas');
  if (!canvas) return;
  const container = document.getElementById('forest-container');
  if (!container) return;
  
  const dpr = window.devicePixelRatio || 1;
  const w = container.clientWidth || container.offsetWidth || 500;
  const h = container.clientHeight || container.offsetHeight || 500;
  
  if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
    canvas.width = w * dpr;
    canvas.height = h * dpr;
    canvas.style.width = w + 'px';
    canvas.style.height = h + 'px';
  }
  
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // Initialize clouds if empty
  if (_clouds.length === 0) {
    for (let i = 0; i < 4; i++) {
      _clouds.push({
        x: Math.random() * 800,
        y: 50 + Math.random() * 150,
        w: 60 + Math.random() * 60,
        h: 25 + Math.random() * 15,
        speed: 0.1 + Math.random() * 0.2,
        opacity: 0.3 + Math.random() * 0.3
      });
    }
  }

  // Restart animation loop
  if (_forestAnimReq) cancelAnimationFrame(_forestAnimReq);
  const animate = () => {
    renderForest();
    _forestAnimReq = requestAnimationFrame(animate);
  };
  animate();

  // Tree picker logic
  document.querySelectorAll('.tree-opt').forEach(opt => {
    opt.onclick = () => {
      document.querySelectorAll('.tree-opt').forEach(o => o.classList.remove('active'));
      opt.classList.add('active');
      _selectedTreeType = opt.dataset.type;
    };
  });

  // Hover/Click info logic
  canvas.onclick = (e) => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    
    // Find tree under cursor (Check from front to back for precision)
    let found = null;
    const sortedFrontToBack = [..._forestTrees].sort((a,b) => b.sy - a.sy);
    for (let t of sortedFrontToBack) {
      const dx = x - t.screenX;
      const dy = y - (t.screenY - 25); // Offset to canopy
      if (Math.sqrt(dx*dx + dy*dy) < 25) {
        found = t;
        break; 
      }
    }

    const popup = document.getElementById('tree-info-popup');
    if (found) {
      document.getElementById('tip-intent').textContent = found.intent;
      document.getElementById('tip-meta').textContent = `${found.mins}m · ${found.status.toUpperCase()}`;
      popup.style.display = 'block';
      popup.style.left = `${found.screenX - 75}px`;
      popup.style.top = `${found.screenY - 100}px`;
    } else {
      popup.style.display = 'none';
    }
  };

  renderForest();
}

function renderForest() {
  const canvas = document.getElementById('forest-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const w = canvas.width / dpr;
  const h = canvas.height / dpr;
  
  if (w < 10 || h < 10) return;
  
  ctx.clearRect(0, 0, w, h);

  // 0. Update & Draw Clouds
  ctx.fillStyle = 'rgba(255, 255, 255, 1)';
  _clouds.forEach(c => {
    c.x += c.speed;
    if (c.x > w + 100) c.x = -150;
    
    ctx.save();
    ctx.globalAlpha = c.opacity;
    // Draw "puffy" cloud
    ctx.beginPath();
    ctx.ellipse(c.x, c.y, c.w, c.h, 0, 0, Math.PI * 2);
    ctx.ellipse(c.x - c.w*0.3, c.y - c.h*0.4, c.w*0.4, c.h*0.6, 0, 0, Math.PI * 2);
    ctx.ellipse(c.x + c.w*0.3, c.y - c.h*0.2, c.w*0.5, c.h*0.7, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();
  });

  // Center the grid - ensure it's ALWAYS visible even if offsets are weird
  const offsetX = w / 2;
  const offsetY = h / 2 - (GRID_SIZE * TILE_H / 2) + 40;

  // 1. Draw Grass Grid with Depth
  for (let row = 0; row < GRID_SIZE; row++) {
    for (let col = 0; col < GRID_SIZE; col++) {
      const sx = (col - row) * (TILE_W / 2) + offsetX;
      const sy = (col + row) * (TILE_H / 2) + offsetY;
      
      // Basic bounds check to avoid drawing way off screen
      if (sx > -100 && sx < w + 100 && sy > -100 && sy < h + 100) {
        drawIsoBlock(ctx, sx, sy); 
      }
    }
  }

  // 2. Draw Trees (Depth Sorted)
  _forestTrees.sort((a,b) => a.sy - b.sy);
  _forestTrees.forEach(t => {
    const sx = (t.col - t.row) * (TILE_W / 2) + offsetX;
    const sy = (t.col + t.row) * (TILE_H / 2) + offsetY;
    t.screenX = sx;
    t.screenY = sy;
    drawIsoTree(ctx, sx, sy, t);
  });
}

function drawIsoBlock(ctx, x, y) {
  // 1. Right Side (Earth)
  ctx.fillStyle = '#5c4033';
  ctx.beginPath();
  ctx.moveTo(x, y + TILE_H);
  ctx.lineTo(x + TILE_W / 2, y + TILE_H / 2);
  ctx.lineTo(x + TILE_W / 2, y + TILE_H / 2 + TILE_DEPTH);
  ctx.lineTo(x, y + TILE_H + TILE_DEPTH);
  ctx.fill();

  // 2. Left Side (Earth)
  ctx.fillStyle = '#4a332a';
  ctx.beginPath();
  ctx.moveTo(x, y + TILE_H);
  ctx.lineTo(x - TILE_W / 2, y + TILE_H / 2);
  ctx.lineTo(x - TILE_W / 2, y + TILE_H / 2 + TILE_DEPTH);
  ctx.lineTo(x, y + TILE_H + TILE_DEPTH);
  ctx.fill();

  // 3. Top (Grass)
  ctx.fillStyle = '#78bc61';
  ctx.beginPath();
  ctx.moveTo(x, y);
  ctx.lineTo(x + TILE_W / 2, y + TILE_H / 2);
  ctx.lineTo(x, y + TILE_H);
  ctx.lineTo(x - TILE_W / 2, y + TILE_H / 2);
  ctx.closePath();
  ctx.fill();
  
  // Grid Lines
  ctx.strokeStyle = 'rgba(255,255,255,0.1)';
  ctx.stroke();
}

function drawIsoTree(ctx, x, y, t) {
  const bx = x;
  const by = y + TILE_H / 2;

  if (t.status === 'cancelled') {
    ctx.fillStyle = '#3a2b1f';
    ctx.fillRect(bx - 3, by - 10, 6, 10);
    return;
  }

  // Trunk
  ctx.fillStyle = '#5c4033';
  ctx.fillRect(bx - 3, by - 15, 6, 15);

  if (t.type === 'pine') {
    // Pine layers
    const layers = [{w:18,h:20,y:-15}, {w:14,h:18,y:-28}, {w:10,h:15,y:-40}];
    layers.forEach((l,i) => {
      ctx.fillStyle = i === 2 ? '#3d7a4d' : i === 1 ? '#2d6a3f' : '#1b4332';
      ctx.beginPath();
      ctx.moveTo(bx, by + l.y - l.h);
      ctx.lineTo(bx + l.w, by + l.y);
      ctx.lineTo(bx - l.w, by + l.y);
      ctx.fill();
    });
  } else if (t.type === 'oak' || t.type === 'palm') {
    // Fluffy Round Tree
    ctx.fillStyle = '#2d6a4f';
    ctx.beginPath(); ctx.arc(bx, by - 35, 18, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#40916c';
    ctx.beginPath(); ctx.arc(bx - 5, by - 40, 12, 0, Math.PI * 2); ctx.fill();
  } else if (t.type === 'flower') {
    // Blossom
    ctx.fillStyle = '#ff85a1';
    ctx.beginPath(); ctx.arc(bx, by - 35, 16, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = 'white';
    ctx.beginPath(); ctx.arc(bx + 4, by - 40, 3, 0, Math.PI * 2); ctx.fill();
    ctx.beginPath(); ctx.arc(bx - 6, by - 32, 2, 0, Math.PI * 2); ctx.fill();
  }
}

function updateForestData(sessions) {
  _forestTrees = [];
  
  // Create a deterministic set of unique positions
  const occupied = new Set();
  
  sessions.forEach((s, i) => {
    // Generate deterministic row/col based on session metadata
    const hash = s.id ? String(s.id).split('').reduce((acc, char) => acc + char.charCodeAt(0), 0) : i * 127;
    
    let row = hash % GRID_SIZE;
    let col = Math.floor(hash / GRID_SIZE) % GRID_SIZE;
    
    // Simple collision avoidance
    let attempts = 0;
    while (occupied.has(`${row},${col}`) && attempts < 50) {
      col = (col + 1) % GRID_SIZE;
      if (col === 0) row = (row + 1) % GRID_SIZE;
      attempts++;
    }
    occupied.add(`${row},${col}`);

    _forestTrees.push({
      row, col,
      sy: (col + row), // Depth sorting helper
      intent: s.intent,
      mins: s.duration_minutes,
      status: s.status,
      type: s.tree_type || 'pine'
    });
  });

  const stats = document.getElementById('tree-count-val');
  if (stats) {
    const healthy = _forestTrees.filter(t => t.status === 'finished').length;
    stats.textContent = healthy;
  }

  renderForest();
}

function renderSessionGraph(sessions) {
  updateForestData(sessions);
  const container = document.getElementById('dash-session-graph');
  if (!container) return;
  
  const recent = sessions.filter(s => s.status === 'finished').slice(0, 5).reverse();
  if (!recent.length) {
    container.innerHTML = '<div style="color:var(--text-muted); font-size:11px; width:100%; text-align:center; padding-top:40px;">Start your first session!</div>';
    return;
  }

  const maxMin = Math.max(...recent.map(s => s.duration_minutes), 30);
  container.innerHTML = recent.map(s => {
    const h = (s.duration_minutes / maxMin) * 100;
    const date = s.created_at ? s.created_at.slice(5, 10).replace('-', '/') : '';
    return `<div class="graph-bar" style="height: ${h}%;">
      <div class="graph-tooltip">${s.duration_minutes}m - ${s.intent}<br/>${date}</div>
    </div>`;
  }).join('');
}

function loadSessionHistory() {
  api('/api/sessions').then(sessions => {
    // Apply Timeframe Filter
    const filter = document.getElementById('forest-filter')?.value || 'all';
    let filtered = sessions;
    const now = new Date();
    
    if (filter === 'today') {
      const todayStr = now.toISOString().slice(0, 10);
      filtered = sessions.filter(s => s.created_at && s.created_at.startsWith(todayStr));
    } else if (filter === '7days') {
      const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      filtered = sessions.filter(s => s.created_at && new Date(s.created_at) > weekAgo);
    } else if (filter === 'month') {
      const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      filtered = sessions.filter(s => s.created_at && new Date(s.created_at) > monthAgo);
    }

    // 1. Render History List FIRST (Safety First)
    const historyList = document.getElementById('session-history');
    if (historyList) {
      historyList.innerHTML = filtered.slice(0, 15).map(s => {
        const statusColor = { finished:'#10b981', cancelled:'#f59e0b', running:'#7c3aed' }[s.status] || '#aaa';
        return `<div class="session-hist-item">
          <div style="width:8px;height:8px;border-radius:50%;background:${statusColor};flex-shrink:0;"></div>
          <div style="flex:1;">
            <div style="font-weight:600;font-size:13px;color:white;">${s.intent}</div>
            <div style="font-size:11px;color:var(--text-muted);">${s.duration_minutes} min · ${s.created_at ? s.created_at.slice(0,16).replace('T',' ') : ''}</div>
          </div>
          <span class="pill ${s.status==='finished'?'pill-green':s.status==='cancelled'?'pill-muted':'pill-purple'}">${s.status}</span>
        </div>`;
      }).join('') || '<div style="color:var(--text-muted);padding:24px;font-size:13px;text-align:center;">No sessions in this period.</div>';
    }

    // 2. Sync Dashboard
    renderSessionGraph(sessions);

    // 3. Attempt Forest Rendering (Experimental, wrapped in try/catch)
    const runForest = () => {
      try {
        initForest(); 
        updateForestData(filtered);
      } catch (e) {
        console.error("Forest render failed:", e);
      }
    };
    
    setTimeout(runForest, 100);
    setTimeout(runForest, 600);
  }).catch(err => {
    console.error("Failed to load sessions:", err);
  });
}

function startSession() {
  if (_sessionTimer) return;
  const intent = document.getElementById('session-intent').value.trim() || 'Study';
  const mins   = parseInt(document.getElementById('session-duration').value);
  const treeType = _selectedTreeType;

  _sessionTotal = mins * 60;
  _sessionLeft  = _sessionTotal;
  document.getElementById('session-start-btn').style.display = 'none';
  document.getElementById('session-cancel-btn').style.display = '';
  document.getElementById('timer-label').textContent = intent;
  updateTimerDisplay();

  _sessionTimer = setInterval(() => {
    _sessionLeft--;
    updateTimerDisplay();
    if (_sessionLeft <= 0) {
      clearInterval(_sessionTimer); _sessionTimer = null;
      apiPost('/api/sessions', { intent, duration_minutes: mins, status: 'finished', tree_type: treeType });
      document.getElementById('timer-label').textContent = '🎉 Complete!';
      document.getElementById('session-start-btn').style.display = '';
      document.getElementById('session-cancel-btn').style.display = 'none';
      toast(`Session complete! ${mins} minutes of ${intent} done.`, 'success');
      loadSessionHistory();
    }
  }, 1000);
}

function cancelSession() {
  if (_sessionTimer) { clearInterval(_sessionTimer); _sessionTimer = null; }
  const intent = document.getElementById('session-intent').value.trim() || 'Study';
  const mins   = parseInt(document.getElementById('session-duration').value);
  const treeType = _selectedTreeType;
  
  apiPost('/api/sessions', { intent, duration_minutes: mins, status: 'cancelled', tree_type: treeType });
  _sessionLeft = 0; _sessionTotal = 0;
  document.getElementById('timer-display').textContent = `${String(mins).padStart(2,'0')}:00`;
  document.getElementById('timer-label').textContent = 'Ready';
  document.getElementById('session-start-btn').style.display = '';
  document.getElementById('session-cancel-btn').style.display = 'none';
  document.getElementById('timer-progress').style.strokeDashoffset = '0';
  loadSessionHistory();
}

function updateTimerDisplay() {
  const m = Math.floor(_sessionLeft / 60);
  const s = _sessionLeft % 60;
  const timeStr = `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  
  // Page Display
  const timerDisplay = document.getElementById('timer-display');
  if (timerDisplay) timerDisplay.textContent = timeStr;
  
  // Header Timer
  const headerTimer = document.getElementById('header-session-timer');
  const headerTimerVal = document.getElementById('header-timer-val');
  if (headerTimer && headerTimerVal) {
    headerTimerVal.textContent = timeStr;
    headerTimer.classList.toggle('active', _sessionTimer !== null);
  }

  const progress = _sessionTotal > 0 ? (_sessionTotal - _sessionLeft) / _sessionTotal : 0;
  const progressCircle = document.getElementById('timer-progress');
  if (progressCircle) {
    progressCircle.style.strokeDasharray  = CIRCUMFERENCE;
    progressCircle.style.strokeDashoffset = CIRCUMFERENCE * (1 - progress);
  }
}

// ═══════════════════════════════════════════════════════════════
// MUSIC HUB
// ═══════════════════════════════════════════════════════════════
let _playlist     = [];
let _musicIdx     = -1;
let _musicMode    = 'loop'; // loop | one | shuffle
const audioEl     = () => document.getElementById('audio-el');

async function loadMusic() {
  try {
    _playlist = await api('/api/music/playlist');
    renderMusicList();
  } catch(e) { toast('Could not load playlist', 'error'); }
}

function renderMusicList(filter = '') {
  const fl = filter.toLowerCase();
  const list = document.getElementById('music-list');
  if (!list) return;

  const items = _playlist.filter(t => !fl || t.name.toLowerCase().includes(fl));
  list.innerHTML = items.length
    ? items.map((t, i) => {
        const isPlaying = i === _musicIdx;
        return `
          <div class="track-card ${isPlaying ? 'active' : ''}" onclick="playTrack(${i})">
            <div class="track-art">${isPlaying ? '🔊' : '🎵'}</div>
            <div class="track-info">
              <div class="track-name">${t.name}</div>
              <div class="track-count">${t.ext.replace('.','').toUpperCase()} · ${t.play_count} plays</div>
            </div>
            ${isPlaying ? '<div class="visualizer" style="height:14px; gap:2px;"><div class="v-bar" style="width:2px;"></div><div class="v-bar" style="width:2px;"></div><div class="v-bar" style="width:2px;"></div></div>' : ''}
          </div>`;
      }).join('')
    : `<div style="text-align:center; padding:60px; color:var(--text-muted);">
         <div style="font-size:32px; margin-bottom:12px;">🔍</div>
         <div>No matching tracks found</div>
       </div>`;
}



function jumpToTop() {
  // Try scrolling the grid first
  const list = document.getElementById('music-list');
  if (list && list.scrollTop > 0) {
    list.scrollTo({ top: 0, behavior: 'smooth' });
    return;
  }
  // Fallback: Scroll the layout or the page itself
  const layout = document.getElementById('music-layout');
  if (layout) {
    layout.scrollIntoView({ behavior: 'smooth' });
  }
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function filterMusic() {
  renderMusicList(document.getElementById('music-search').value);
}

function playTrack(idx) {
  _musicIdx = idx;
  const track = _playlist[idx];
  if (!track) return;

  const au = audioEl();
  au.src = getStreamUrl(track.stream_url);
  // Set correct MIME type as source element for m4a
  const ext = track.ext.toLowerCase();
  const mimeMap = { '.mp3':'audio/mpeg', '.m4a':'audio/mp4', '.wav':'audio/wav', '.ogg':'audio/ogg', '.flac':'audio/flac' };
  au.type = mimeMap[ext] || 'audio/mpeg';

  au.load();
  au.play().catch(e => toast('Playback error: ' + e.message, 'error'));

  document.getElementById('player-title').textContent  = track.name;
  document.getElementById('player-artist').textContent = track.ext.replace('.','').toUpperCase();

  // Update Hero Visuals
  const viz = document.getElementById('hero-visualizer');
  if (viz) viz.style.display = 'flex';
  const artIcon = document.getElementById('player-art-icon');
  if (artIcon) artIcon.textContent = '🔊';

  renderMusicList(document.getElementById('music-search').value);
  
  // Sync dashboard widget if exists
  const dashTitle = document.getElementById('dash-music-title');
  if (dashTitle) dashTitle.textContent = track.name;

  // Report play to server
  apiPost('/api/music/played', { path: track.path }).catch(()=>{});

  au.onended = () => musicAutoNext();
  au.ontimeupdate = () => {
    if (!au.duration) return;
    document.getElementById('progress-bar').value = (au.currentTime / au.duration) * 100;
    document.getElementById('cur-time').textContent = fmtTime(au.currentTime);
    document.getElementById('dur-time').textContent = fmtTime(au.duration);
  };
  au.onplay  = () => setPlayIcon(true);
  au.onpause = () => setPlayIcon(false);
}

function setPlayIcon(playing) {
  const svg = playing
    ? '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
    : '<polygon points="5 3 19 12 5 21 5 3"/>';
  const mainIcon = document.getElementById('play-icon');
  if (mainIcon) mainIcon.innerHTML = svg;
  const dashIcon = document.getElementById('dash-play-icon');
  if (dashIcon) dashIcon.innerHTML = svg;
}

function togglePlay() {
  const au = audioEl();
  if (_musicIdx < 0 && _playlist.length) { playTrack(0); return; }
  if (au.paused) au.play(); else au.pause();
}

function musicNext() {
  if (!_playlist.length) return;
  let next;
  if (_musicMode === 'shuffle') {
    do { next = Math.floor(Math.random() * _playlist.length); } while (next === _musicIdx && _playlist.length > 1);
  } else {
    next = (_musicIdx + 1) % _playlist.length;
  }
  playTrack(next);
}

function musicPrev() {
  if (!_playlist.length) return;
  const prev = (_musicIdx - 1 + _playlist.length) % _playlist.length;
  playTrack(prev);
}

function musicAutoNext() {
  if (_musicMode === 'one') {
    const au = audioEl(); au.currentTime = 0; au.play();
  } else { musicNext(); }
}

function changeMusicMode() { _musicMode = document.getElementById('music-mode').value; }
function setVolume(v) { audioEl().volume = v / 100; }
function seekTo(v) { const au = audioEl(); if (au.duration) au.currentTime = (v / 100) * au.duration; }
function fmtTime(s) { const m = Math.floor(s/60); return `${m}:${String(Math.floor(s%60)).padStart(2,'0')}`; }

// ═══════════════════════════════════════════════════════════════
// RADIO
// ═══════════════════════════════════════════════════════════════
let _radioStations  = [];
let _radioIdx       = -1;
let _radioPlaying   = false;
const radioEl       = () => document.getElementById('radio-el');

async function loadRadio() {
  try {
    _radioStations = await api('/api/radio/stations');
    renderRadioList();
  } catch(e) { toast('Could not load stations', 'error'); }
}

function renderRadioList() {
  document.getElementById('radio-list').innerHTML = _radioStations.length
    ? _radioStations.map((s, i) => `
        <div class="radio-item ${i === _radioIdx ? 'playing' : ''}" onclick="selectStation(${i})">
          <div class="radio-dot"></div>
          <div style="flex:1;">
            <div style="font-weight:600;font-size:14px;">${s.name}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:2px;">${s.url}</div>
          </div>
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();deleteStation(${i})">✕</button>
        </div>`).join('')
    : `<div class="empty-state"><div>No stations added yet</div></div>`;
}

function selectStation(idx) {
  _radioIdx = idx;
  const s = _radioStations[idx];
  document.getElementById('radio-name').textContent   = s.name;
  document.getElementById('radio-status').textContent = 'Connecting…';
  const re = radioEl();
  re.src = s.url;
  re.load();
  re.play().then(() => {
    _radioPlaying = true;
    setRadioPlayIcon(true);
    document.getElementById('radio-status').textContent = 'Streaming Live…';
  }).catch(e => {
    document.getElementById('radio-status').textContent = 'Connection failed';
    toast('Stream error: ' + e.message, 'error');
  });
  renderRadioList();
}

function toggleRadio() {
  const re = radioEl();
  if (re.paused) {
    if (!re.src) return;
    re.play().then(() => { _radioPlaying = true; setRadioPlayIcon(true); document.getElementById('radio-status').textContent = 'Streaming Live…'; });
  } else {
    re.pause(); _radioPlaying = false;
    setRadioPlayIcon(false);
    document.getElementById('radio-status').textContent = 'Paused';
  }
}

function setRadioPlayIcon(playing) {
  document.getElementById('radio-play-icon').innerHTML = playing
    ? '<rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/>'
    : '<polygon points="5 3 19 12 5 21 5 3"/>';
}

function setRadioVol(v) { radioEl().volume = v / 100; }

function showAddStation() {
  showModal(`
    <div class="modal-title">Add Radio Station</div>
    <div class="form-group">
      <label class="form-label">Station Name</label>
      <input class="input" id="st-name" placeholder="e.g. Lofi Radio"/>
    </div>
    <div class="form-group">
      <label class="form-label">Stream URL</label>
      <input class="input" id="st-url" placeholder="http://stream.example.com/radio"/>
    </div>
    <div class="modal-footer">
      <button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
      <button class="btn btn-primary" onclick="submitStation()">Add Station</button>
    </div>`);
}

async function submitStation() {
  const name = document.getElementById('st-name').value.trim();
  const url  = document.getElementById('st-url').value.trim();
  if (!name || !url) { toast('Name and URL required', 'error'); return; }
  try {
    await apiPost('/api/radio/station', { name, url });
    closeModal(); toast('Station added ✅', 'success');
    _radioStations = await api('/api/radio/stations');
    renderRadioList();
  } catch(e) { toast('Failed to add station', 'error'); }
}

async function deleteStation(idx) {
  try {
    await fetch(`/api/radio/station/${idx}`, { method: 'DELETE' });
    if (_radioIdx === idx) { radioEl().pause(); _radioIdx = -1; _radioPlaying = false; setRadioPlayIcon(false); }
    _radioStations = await api('/api/radio/stations');
    renderRadioList();
    toast('Station removed', 'info');
  } catch(e) { toast('Failed to delete station', 'error'); }
}

// ═══════════════════════════════════════════════════════════════
// MBOARD — infinite canvas with pen, eraser, undo
// ═══════════════════════════════════════════════════════════════
let _mbTool   = 'pen';
let _mbDrawing = false;
let _mbStrokes = [];       // [{color,size,points:[{x,y}]}]
let _mbCurrent = null;
let _mbOffX = 0, _mbOffY = 0;  // pan offset
let _mbPanStart = null;
let _mbCanvas = null, _mbCtx = null;
let _mbInitted = false;

function initMboard() {
  if (_mbInitted) { resizeMboard(); return; }
  _mbInitted = true;
  _mbCanvas = document.getElementById('mboard-canvas');
  _mbCtx    = _mbCanvas.getContext('2d');
  resizeMboard();
  window.addEventListener('resize', resizeMboard);

  const wrap = document.getElementById('mboard-canvas-wrap');

  // Mouse
  wrap.addEventListener('mousedown',  mbPointerDown);
  wrap.addEventListener('mousemove',  mbPointerMove);
  wrap.addEventListener('mouseup',    mbPointerUp);
  wrap.addEventListener('mouseleave', mbPointerUp);

  // Touch
  wrap.addEventListener('touchstart', e => { e.preventDefault(); mbPointerDown(e.touches[0]); }, { passive:false });
  wrap.addEventListener('touchmove',  e => { e.preventDefault(); mbPointerMove(e.touches[0]); }, { passive:false });
  wrap.addEventListener('touchend',   e => { e.preventDefault(); mbPointerUp();                }, { passive:false });

  // Pan with right-click / two-finger scroll
  wrap.addEventListener('wheel', e => {
    e.preventDefault();
    _mbOffX -= e.deltaX; _mbOffY -= e.deltaY;
    mbRedraw();
  }, { passive:false });

  // Load existing strokes from server
  api('/api/mboard/strokes').then(strokes => { _mbStrokes = strokes || []; mbRedraw(); }).catch(()=>{});

  // SocketIO live sync
  socket.on('mboard_stroke', s => { _mbStrokes.push(s); mbRedraw(); });
  socket.on('mboard_undo',   () => { _mbStrokes.pop();  mbRedraw(); });
  socket.on('mboard_clear',  () => { _mbStrokes = [];   mbRedraw(); });
}

function resizeMboard() {
  const wrap = document.getElementById('mboard-canvas-wrap');
  if (!wrap || !_mbCanvas) return;
  _mbCanvas.width  = wrap.clientWidth;
  _mbCanvas.height = wrap.clientHeight;
  mbRedraw();
}

function mbPointerDown(e) {
  const rect  = _mbCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left - _mbOffX;
  const y = e.clientY - rect.top  - _mbOffY;

  if (e.button === 2 || _mbTool === 'pan') {
    _mbPanStart = { mx: e.clientX, my: e.clientY, ox: _mbOffX, oy: _mbOffY };
    return;
  }
  _mbDrawing = true;
  _mbCurrent = {
    color:  _mbTool === 'eraser' ? '#0c0c18' : document.getElementById('stroke-color').value,
    size:   parseInt(document.getElementById('stroke-size').value),
    eraser: _mbTool === 'eraser',
    points: [{ x, y }]
  };
  _mbCtx.beginPath();
}

function mbPointerMove(e) {
  if (_mbPanStart) {
    _mbOffX = _mbPanStart.ox + (e.clientX - _mbPanStart.mx);
    _mbOffY = _mbPanStart.oy + (e.clientY - _mbPanStart.my);
    mbRedraw(); return;
  }
  if (!_mbDrawing || !_mbCurrent) return;
  const rect = _mbCanvas.getBoundingClientRect();
  const x = e.clientX - rect.left - _mbOffX;
  const y = e.clientY - rect.top  - _mbOffY;
  _mbCurrent.points.push({ x, y });
  mbRedraw();
  // Live preview of current stroke
  mbDrawStroke(_mbCurrent);
}

function mbPointerUp() {
  _mbPanStart = null;
  if (!_mbDrawing || !_mbCurrent) return;
  _mbDrawing = false;
  if (_mbCurrent.points.length > 1) {
    _mbStrokes.push(_mbCurrent);
    apiPost('/api/mboard/stroke', _mbCurrent).catch(()=>{});
  }
  _mbCurrent = null;
}

function mbRedraw() {
  if (!_mbCtx) return;
  _mbCtx.clearRect(0, 0, _mbCanvas.width, _mbCanvas.height);
  _mbCtx.save();
  _mbCtx.translate(_mbOffX, _mbOffY);
  _mbStrokes.forEach(s => mbDrawStroke(s));
  if (_mbDrawing && _mbCurrent) mbDrawStroke(_mbCurrent);
  _mbCtx.restore();
}

function mbDrawStroke(s) {
  if (!s.points || s.points.length < 2) return;
  _mbCtx.save();
  _mbCtx.globalCompositeOperation = s.eraser ? 'destination-out' : 'source-over';
  _mbCtx.strokeStyle = s.color;
  _mbCtx.lineWidth   = s.size;
  _mbCtx.lineCap     = 'round';
  _mbCtx.lineJoin    = 'round';
  _mbCtx.beginPath();
  _mbCtx.moveTo(s.points[0].x, s.points[0].y);
  for (let i = 1; i < s.points.length; i++) {
    _mbCtx.lineTo(s.points[i].x, s.points[i].y);
  }
  _mbCtx.stroke();
  _mbCtx.restore();
}

function setTool(tool) {
  _mbTool = tool;
  document.querySelectorAll('.tool-btn').forEach(b => b.classList.remove('active'));
  const btn = document.getElementById('tool-' + tool);
  if (btn) btn.classList.add('active');
  document.getElementById('mboard-canvas-wrap').style.cursor = tool === 'eraser' ? 'cell' : 'crosshair';
}

async function mbUndo() {
  if (_mbStrokes.length) {
    _mbStrokes.pop();
    mbRedraw();
    await apiPost('/api/mboard/undo', {}).catch(()=>{});
  }
}

async function mbClear() {
  _mbStrokes = []; mbRedraw();
  await apiPost('/api/mboard/clear', {}).catch(()=>{});
}

// ── INIT ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  if (checkAuth()) {
    loadHome();
  }
});

// ═══════════════════════════════════════════════════════════════
// MARKDOWN ↔ HTML CONVERTER (no external deps)
// ═══════════════════════════════════════════════════════════════
function mdToHtml(md) {
  if (!md) return '';
  let lines = md.split('\n');
  let out = [];
  let inList = false, listType = '';

  const inlineFormat = s =>
    s.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
     .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
     .replace(/__(.+?)__/g, '<strong>$1</strong>')
     .replace(/\*(.+?)\*/g, '<em>$1</em>')
     .replace(/_(.+?)_/g, '<em>$1</em>')
     .replace(/~~(.+?)~~/g, '<del>$1</del>')
     .replace(/`(.+?)`/g, '<code>$1</code>')
     .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank">$1</a>');

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Headings
    const hm = line.match(/^(#{1,6})\s+(.*)/);
    if (hm) {
      if (inList) { out.push(`</${listType}>`); inList = false; }
      const lvl = hm[1].length;
      out.push(`<h${lvl}>${inlineFormat(hm[2])}</h${lvl}>`);
      continue;
    }
    // Horizontal rule
    if (/^(\*{3,}|-{3,}|_{3,})$/.test(line.trim())) {
      out.push('<hr/>'); continue;
    }
    // Blockquote
    if (line.startsWith('> ')) {
      if (inList) { out.push(`</${listType}>`); inList = false; }
      out.push(`<blockquote>${inlineFormat(line.slice(2))}</blockquote>`); continue;
    }
    // Unordered list
    const ulm = line.match(/^[\s]*[-*+]\s+(.*)/);
    if (ulm) {
      if (!inList || listType !== 'ul') {
        if (inList) out.push(`</${listType}>`);
        out.push('<ul>'); inList = true; listType = 'ul';
      }
      out.push(`<li>${inlineFormat(ulm[1])}</li>`); continue;
    }
    // Ordered list
    const olm = line.match(/^[\s]*\d+\.\s+(.*)/);
    if (olm) {
      if (!inList || listType !== 'ol') {
        if (inList) out.push(`</${listType}>`);
        out.push('<ol>'); inList = true; listType = 'ol';
      }
      out.push(`<li>${inlineFormat(olm[1])}</li>`); continue;
    }
    // End list
    if (inList && line.trim() === '') {
      out.push(`</${listType}>`); inList = false;
      out.push('<br/>'); continue;
    }
    // Blank line
    if (!line.trim()) {
      out.push('<br/>'); continue;
    }
    // Normal paragraph line
    out.push(`<p>${inlineFormat(line)}</p>`);
  }
  if (inList) out.push(`</${listType}>`);
  return out.join('');
}

function htmlToMd(el) {
  function nodeToMd(node, ctx) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    const tag = node.nodeName.toLowerCase();
    const children = () => Array.from(node.childNodes).map(c => nodeToMd(c, ctx)).join('');
    if (tag === 'h1') return `\n# ${children()}\n`;
    if (tag === 'h2') return `\n## ${children()}\n`;
    if (tag === 'h3') return `\n### ${children()}\n`;
    if (tag === 'h4') return `\n#### ${children()}\n`;
    if (tag === 'h5') return `\n##### ${children()}\n`;
    if (tag === 'h6') return `\n###### ${children()}\n`;
    if (tag === 'strong' || tag === 'b') return `**${children()}**`;
    if (tag === 'em' || tag === 'i') return `*${children()}*`;
    if (tag === 'u') return children(); // no md underline; drop
    if (tag === 'del' || tag === 's') return `~~${children()}~~`;
    if (tag === 'code') return `\`${children()}\``;
    if (tag === 'blockquote') return `\n> ${children().trim()}\n`;
    if (tag === 'hr') return `\n---\n`;
    if (tag === 'br') return `\n`;
    if (tag === 'li') return `- ${children().trim()}\n`;
    if (tag === 'ul' || tag === 'ol') return `\n${children()}`;
    if (tag === 'p') return `\n${children()}\n`;
    if (tag === 'a') {
      const href = node.getAttribute('href') || '';
      return `[${children()}](${href})`;
    }
    if (tag === 'div') return `\n${children()}`;
    return children();
  }
  return nodeToMd(el, {}).replace(/\n{3,}/g, '\n\n').trim();
}

// ═══════════════════════════════════════════════════════════════
// WYSIWYG NOTE EDITOR
// ═══════════════════════════════════════════════════════════════
let _edFileId   = null;
let _edSaveTimer = null;
let _edDirty    = false;

function openNoteEditor(fileId) {
  _edFileId = fileId;
  _edDirty  = false;

  document.getElementById('viewer-content').style.display    = 'none';
  document.getElementById('note-editor-panel').style.display = 'flex';
  setEdStatus('LOADING…', '');

  const url = `/api/vault/note/${fileId}/content?pw=${_notakPassword}`;
  api(url.replace(`?pw=${_notakPassword}`, ''))  // use api() which injects header
    .catch(() => null)
    .then(async () => {
      // Fetch raw content via authenticated fetch
      const r = await fetch(`/api/vault/note/${fileId}/content?pw=${_notakPassword}`);
      if (!r.ok) { toast('Could not load note', 'error'); return; }
      const data = await r.json();
      const html = mdToHtml(data.content || '');
      const wysiwyg = document.getElementById('note-wysiwyg');
      wysiwyg.innerHTML = html;
      setEdStatus('READY', '');
      wysiwyg.focus();
    });
}

function closeNoteEditor() {
  if (_edDirty) saveNote_wysiwyg(true);
  document.getElementById('viewer-content').style.display    = '';
  document.getElementById('note-editor-panel').style.display = 'none';
  _edFileId = null;
}

function setEdStatus(text, mode) {
  const el = document.getElementById('editor-status');
  if (!el) return;
  el.textContent = text;
  el.className   = 'editor-status' + (mode ? ' ' + mode : '');
}

function onEditorInput() {
  _edDirty = true;
  setEdStatus('EDITING…', 'editing');
  clearTimeout(_edSaveTimer);
  _edSaveTimer = setTimeout(() => saveNote_wysiwyg(), 2000);
}

async function saveNote_wysiwyg(sync = false) {
  if (!_edFileId) return;
  const wysiwyg = document.getElementById('note-wysiwyg');
  const md = htmlToMd(wysiwyg);
  if (!md.trim()) return;

  try {
    let r;
    if (_edFileId === 'new_vault_note') {
      const activeCat = document.querySelector('.course-item.active');
      const course = activeCat ? activeCat.textContent.replace('📚 ','').trim() : 'Inbox';
      r = await fetch('/api/vault/note?pw=' + _notakPassword, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
        body: JSON.stringify({ content: md, course: course })
      });
      const data = await r.json();
      if (data.ok && data.file_id) {
        _edFileId = data.file_id;
        loadVaultFiles();
      }
    } else {
      r = await fetch(`/api/vault/note/${_edFileId}?pw=${_notakPassword}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
        body:    JSON.stringify({ content: md }),
      });
    }
    if (r.ok) {
      _edDirty = false;
      setEdStatus('SAVED ✓', 'saved');
    } else {
      setEdStatus('SAVE ERROR', '');
    }
  } catch(e) {
    setEdStatus('OFFLINE', '');
  }
}

// Formatting commands
function edCmd(cmd) {
  document.getElementById('note-wysiwyg').focus();
  document.execCommand(cmd, false, null);
}

function edHeading(level) {
  document.getElementById('note-wysiwyg').focus();
  // Use formatBlock to wrap in heading
  document.execCommand('formatBlock', false, `h${level}`);
}

function edHRule() {
  document.getElementById('note-wysiwyg').focus();
  document.execCommand('insertHorizontalRule', false, null);
}

function edKeyDown(e) {
  // Ctrl+B/I/U already handled by browser contenteditable
  // Tab → indent (prevent focus change)
  if (e.key === 'Tab') {
    e.preventDefault();
    document.execCommand('insertText', false, '    ');
  }
  // Auto-save on Ctrl+S
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault();
    saveNote_wysiwyg(true);
  }
}

function printNote() {
  window.print();
}

// Patch openFile to route .md to WYSIWYG editor
const _origOpenFile = openFile;
async function openFile(id) {
  _currentFileId = id;
  filterFiles();
  try {
    const f = await api(`/api/vault/file/${id}`);
    const ext = (f.name || '').split('.').pop().toLowerCase();
    if (ext === 'md') {
      openNoteEditor(id);
    } else {
      // Close editor if open and show viewer
      document.getElementById('viewer-content').style.display    = '';
      document.getElementById('note-editor-panel').style.display = 'none';
      _edFileId = null;

      const streamUrl = getStreamUrl(`/stream/file/${id}`);
      const viewer    = document.getElementById('viewer-content');

      if (ext === 'pdf') {
        viewer.innerHTML = `<iframe src="${streamUrl}" style="width:100%;height:100%;border:none;border-radius:10px;background:#111;"></iframe>`;
      } else if (['png','jpg','jpeg','gif','webp'].includes(ext)) {
        viewer.innerHTML = `<img src="${streamUrl}" style="max-width:100%;max-height:80vh;border-radius:12px;object-fit:contain;"/>`;
      } else if (['mp3','m4a','wav','ogg','flac'].includes(ext)) {
        const mime = ext === 'm4a' ? 'audio/mp4' : ext === 'mp3' ? 'audio/mpeg' : 'audio/' + ext;
        viewer.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;gap:20px;padding:40px;">
          <div style="font-size:64px;">🎵</div>
          <div style="font-size:18px;font-weight:700;">${f.name}</div>
          <audio controls style="width:100%;max-width:420px;accent-color:var(--accent);">
            <source src="${streamUrl}" type="${mime}"/>
          </audio></div>`;
      } else if (['txt','csv'].includes(ext)) {
        const resp = await fetch(streamUrl);
        const text = await resp.text();
        viewer.innerHTML = `<pre style="white-space:pre-wrap;word-break:break-word;font-size:13px;line-height:1.7;color:#ddd;padding:8px;">${escHtml(text)}</pre>`;
      } else {
        viewer.innerHTML = `<div style="display:flex;flex-direction:column;align-items:center;gap:16px;padding:40px;color:var(--text-muted);">
          <div style="font-size:48px;">${fileIcon(f.category)}</div>
          <div style="font-size:16px;font-weight:600;">${f.name}</div>
          <div style="font-size:13px;">Preview not available in browser</div>
          <a href="${streamUrl}" download="${f.name}" class="btn btn-primary">⬇ Download</a></div>`;
      }
    }
  } catch(e) { toast('Could not load file', 'error'); }
}

// ═══════════════════════════════════════════════════════════════
// AI ASSISTANT — INGRACIA
// ═══════════════════════════════════════════════════════════════
let _aiOpen    = false;
let _aiHistory = [];          // [{role, content}]
let _aiStreaming = false;
let _aiFormatMode = false;    // true = format-note context

function toggleAIPanel() {
  _aiOpen = !_aiOpen;
  const panel = document.getElementById('ai-panel');
  const navBtn = document.getElementById('nav-ai');
  panel.classList.toggle('open', _aiOpen);
  navBtn.classList.toggle('active', _aiOpen);
  if (_aiOpen && !document.getElementById('ai-messages').children.length) {
    appendAIBubble('assistant', "Hi! I'm **Ingracia**, your study assistant ✨\n\nAsk me anything — I can help summarise notes, explain concepts, format text, and much more.");
  }
  if (_aiOpen) setTimeout(() => document.getElementById('ai-input').focus(), 300);
}

function clearAIChat() {
  _aiHistory = [];
  document.getElementById('ai-messages').innerHTML = '';
  appendAIBubble('assistant', "Chat cleared. Ready to help! 🚀");
}

function appendAIBubble(role, text, streaming = false) {
  const msgs = document.getElementById('ai-messages');
  const div  = document.createElement('div');
  div.className = `ai-bubble ${role}${streaming ? ' ai-typing-cursor' : ''}`;
  div.innerHTML = mdToHtml(text);
  msgs.appendChild(div);
  msgs.scrollTop = msgs.scrollHeight;
  return div;
}

async function sendAIMessage(overrideMsg = null) {
  if (_aiStreaming) return;
  const input   = document.getElementById('ai-input');
  const message = overrideMsg || input.value.trim();
  if (!message) return;

  if (!overrideMsg) { input.value = ''; autoResizeAI(input); }

  // Add user bubble
  appendAIBubble('user', message);
  _aiHistory.push({ role: 'user', content: message });

  // Prepare assistant bubble
  const aiBubble   = appendAIBubble('assistant', '', true);
  aiBubble.innerHTML = '';
  let fullText     = '';

  _aiStreaming = true;
  setAIStatusDot('thinking');
  document.getElementById('ai-send-btn').disabled = true;

  let systemPrompt = "You are Ingracia, a brilliant and friendly AI study assistant for Notak. You MUST be extremely concise and straight to the point. Never over-explain. Do not write long paragraphs unless absolutely necessary. If the user says a simple greeting like 'hi', respond with a very short and simple greeting back. Render clear, structured markdown in your answers. Make sure your information is not biased. If you are in an unknown or unclear state, state it clearly—do not try to give pleasing or invented answers. In mathematics, you must ALWAYS perform a double calculation before giving a response (e.g., calculate once, get the result, calculate again, get the result; if they match, provide the answer to the user. If they do not match, find the error and compare until they are the same). I will not tolerate calculation errors.";
  if (_aiFormatMode) {
    systemPrompt = "You are a professional academic text formatter for Notak. Format the text into clean markdown with proper headings, bullets and spacing. Preserve the meaning. Output ONLY the formatted text — no intro, no explanations.";
  }

  try {
    const modelSelection = document.getElementById('ai-model-select').value;
    const resp = await fetch('/api/ai/chat', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
      body:    JSON.stringify({ message, history: _aiHistory.slice(0,-1), system_prompt: systemPrompt, model: modelSelection }),
    });

    if (!resp.ok) {
      const err = await resp.json();
      aiBubble.classList.remove('ai-typing-cursor');
      aiBubble.innerHTML = `<span style="color:var(--danger);">Error: ${err.error || 'Unknown'}</span>`;
      _aiStreaming = false; setAIStatusDot('idle');
      document.getElementById('ai-send-btn').disabled = false;
      return;
    }

    const reader = resp.body.getReader();
    const dec    = new TextDecoder();
    let   buf    = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const lines = buf.split('\n');
      buf = lines.pop();

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const payload = line.slice(6).trim();
        if (payload === '[DONE]') break;
        try {
          const obj = JSON.parse(payload);
          if (obj.token) {
            fullText += obj.token;
            aiBubble.innerHTML = mdToHtml(fullText);
            document.getElementById('ai-messages').scrollTop = document.getElementById('ai-messages').scrollHeight;
          }
          if (obj.error) { aiBubble.innerHTML += `<span style="color:var(--danger);"> [${obj.error}]</span>`; }
        } catch(e) {}
      }
    }

    aiBubble.classList.remove('ai-typing-cursor');
    _aiHistory.push({ role: 'assistant', content: fullText });

    // If this was a format-note call, apply result back to editor
    if (_aiFormatMode && _edFileId) {
      if (_edFileId === 'quick_note') {
        const wysiwyg = document.getElementById('qn-note-wysiwyg');
        wysiwyg.innerHTML = mdToHtml(fullText);
        document.getElementById('qn-editor-status').textContent = 'AI FORMATTED';
        cancelAIContext();
        toast('Quick Note reformatted by AI ✨', 'success');
      } else {
        const wysiwyg = document.getElementById('note-wysiwyg');
        wysiwyg.innerHTML = mdToHtml(fullText);
        _edDirty = true;
        setEdStatus('AI FORMATTED', 'ai');
        saveNote_wysiwyg();
        cancelAIContext();
        toast('Note reformatted by AI ✨', 'success');
      }
    }

  } catch(e) {
    aiBubble.classList.remove('ai-typing-cursor');
    aiBubble.innerHTML = `<span style="color:var(--danger);">Connection error: ${e.message}</span>`;
  }

  _aiStreaming = false;
  setAIStatusDot('idle');
  document.getElementById('ai-send-btn').disabled = false;
  _aiFormatMode = false;
}

function formatNoteWithAI() {
  if (!_edFileId) { toast('Open a note first', 'error'); return; }
  const wysiwyg = document.getElementById('note-wysiwyg');
  const md = htmlToMd(wysiwyg);
  if (!md.trim()) { toast('Note is empty', 'error'); return; }

  _aiFormatMode = true;
  if (!_aiOpen) toggleAIPanel();
  document.getElementById('ai-context-bar').style.display = 'flex';
  setEdStatus('AI FORMATTING…', 'ai');

  sendAIMessage(`Format and improve this note:\n\n${md}`);
}

function cancelAIContext() {
  _aiFormatMode = false;
  document.getElementById('ai-context-bar').style.display = 'none';
}

function setAIStatusDot(state) {
  const dot = document.getElementById('ai-status-dot');
  dot.className = state === 'idle' ? 'idle' : state;
}

function aiInputKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendAIMessage(); }
}

function autoResizeAI(el) {
  el.style.height = 'auto';
  el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

// Global shortcuts
document.addEventListener('keydown', e => {
  // Ctrl+Space: Toggle AI panel
  if ((e.ctrlKey || e.metaKey) && e.key === ' ') {
    e.preventDefault();
    toggleAIPanel();
  }
  // Ctrl+B: Toggle Sidebar
  if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
    e.preventDefault();
    toggleSidebar();
  }
});
