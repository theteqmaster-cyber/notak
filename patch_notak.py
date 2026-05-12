import re

# --- 1. Patch index.html ---
with open('nserver/static/index.html', 'r') as f:
    html = f.read()

# Header and Footer layout, move sidebar
header_html = """
  <!-- ── Global Header ── -->
  <header id="global-header">
    <div class="header-left">
      <img src="/icon.png" style="width: 28px; height: 28px; border-radius: 6px;"/>
      <span class="header-brand">Notak</span>
      <span id="header-clock" class="header-clock"></span>
    </div>
    <div class="header-right">
      <button class="btn btn-ghost btn-icon" onclick="toggleSidebar()" title="Toggle Menu">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="20" height="20"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
    </div>
  </header>
  <div id="app">
"""

html = html.replace('<div id="app">', '<div id="app-container">\n' + header_html)

footer_html = """
  <!-- ── Global Footer ── -->
  <footer id="global-footer">
    <div class="footer-content">
      <span>Notak Study Hub &copy; 2026</span>
    </div>
  </footer>
</div> <!-- end app-container -->
"""

html = html.replace('</main>\n</div>', '</main>\n</div>\n' + footer_html)

# Add close button to Note Editor Toolbar in Study Hub
toolbar_close_btn = """
              <span id="editor-status" class="editor-status">READY</span>
              <button class="ed-btn" onclick="printNote()" title="Print / Export PDF">🖨 Print</button>
              <button class="ed-btn" onclick="closeNoteEditor()" title="Close Note" style="color:var(--danger);">✕ Close</button>
"""
html = html.replace('<span id="editor-status" class="editor-status">READY</span>\n              <button class="ed-btn" onclick="printNote()" title="Print / Export PDF">🖨 Print</button>', toolbar_close_btn)

# Replace Quick Note section with WYSIWYG editor
quick_note_html = """
    <!-- NOTES -->
    <section id="page-notes" class="page" style="padding:0; flex-direction:column;">
      <div class="page-header" style="padding: 32px 36px 0;">
        <div class="page-title">Quick Note</div>
        <div style="display:flex;gap:8px;">
          <select class="input" id="note-course" style="width:auto;padding:8px 12px;"></select>
          <button class="btn btn-primary" onclick="saveQuickNote()">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/></svg>
            Save Note
          </button>
        </div>
      </div>
      <div style="padding: 0 36px;">
        <input class="input" id="note-title" placeholder="Note title…" style="max-width:500px;"/>
        <div style="font-size:12px;color:var(--text-muted);margin-top:8px;">💡 Tip: Saved notes appear in your Study Hub vault automatically.</div>
      </div>
      
      <div id="quick-note-editor-panel" style="display:flex;flex-direction:column;flex:1;margin-top:16px;">
        <!-- Editor toolbar -->
        <div id="qn-editor-toolbar" class="editor-toolbar-global">
          <div class="editor-tool-group">
            <button class="ed-btn" onclick="qnCmd('bold')" title="Bold"><b>B</b></button>
            <button class="ed-btn" onclick="qnCmd('italic')" title="Italic"><i>I</i></button>
            <button class="ed-btn" onclick="qnCmd('underline')" title="Underline"><u>U</u></button>
          </div>
          <div class="ed-sep"></div>
          <div class="editor-tool-group">
            <button class="ed-btn" onclick="qnHeading(1)" title="Heading 1">H1</button>
            <button class="ed-btn" onclick="qnHeading(2)" title="Heading 2">H2</button>
            <button class="ed-btn" onclick="qnHeading(3)" title="Heading 3">H3</button>
          </div>
          <div class="ed-sep"></div>
          <div class="editor-tool-group">
            <button class="ed-btn" onclick="qnCmd('insertUnorderedList')" title="Bullet List">• List</button>
            <button class="ed-btn" onclick="qnCmd('insertOrderedList')" title="Numbered List"># List</button>
            <button class="ed-btn" onclick="qnHRule()" title="Divider">──</button>
          </div>
          <div class="ed-sep"></div>
          <button class="ed-btn ed-btn-ai" onclick="formatQuickNoteWithAI()" id="qn-fmrt-btn" title="AI: Reformat note">✨ fmrt</button>
          <div style="flex:1;"></div>
          <span id="qn-editor-status" class="editor-status">READY</span>
        </div>
        <!-- Contenteditable WYSIWYG area -->
        <div id="qn-note-wysiwyg" class="wysiwyg-area" contenteditable="true" spellcheck="true"
             oninput="onQnEditorInput()" onkeydown="qnKeyDown(event)"
             placeholder="Start writing your note here… (Markdown supported)"></div>
      </div>
    </section>
"""

# Find and replace the entire notes section
notes_start = html.find('<!-- NOTES -->')
notes_end = html.find('<!-- CALENDAR -->')
html = html[:notes_start] + quick_note_html + html[notes_end:]

# Modify toolbar class in Study hub to use global class
html = html.replace('<div id="editor-toolbar">', '<div id="editor-toolbar" class="editor-toolbar-global">')
html = html.replace('<div id="note-wysiwyg" contenteditable="true"', '<div id="note-wysiwyg" class="wysiwyg-area" contenteditable="true"')

with open('nserver/static/index.html', 'w') as f:
    f.write(html)

# --- 2. Patch style.css ---
with open('nserver/static/style.css', 'r') as f:
    css = f.read()

header_footer_css = """
/* ── Global Header & Footer ──────────────────────────────── */
#app-container { display: flex; flex-direction: column; height: 100vh; width: 100vw; overflow: hidden; }
#global-header {
  height: 60px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px;
  background: rgba(10,10,20,0.95);
  border-bottom: 1px solid var(--border);
  backdrop-filter: blur(24px);
  z-index: 150;
}
.header-left { display: flex; align-items: center; gap: 12px; }
.header-brand {
  font-size: 18px; font-weight: 900;
  background: linear-gradient(135deg, var(--accent), var(--accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: -0.5px;
}
.header-clock {
  font-size: 14px; font-weight: 600; color: var(--text-muted);
  margin-left: 16px; font-variant-numeric: tabular-nums;
  padding-left: 16px; border-left: 1px solid var(--border);
}
.header-right { display: flex; align-items: center; gap: 12px; }

#global-footer {
  height: 40px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  background: rgba(10,10,20,0.95);
  border-top: 1px solid var(--border);
  backdrop-filter: blur(24px);
  z-index: 150;
}
.footer-content { font-size: 12px; color: var(--text-muted); font-weight: 500; }

/* Modify app layout */
#app { flex: 1; display: flex; overflow: hidden; position: relative; }
"""

css = css.replace('/* ── Layout ──────────────────────────────────────────────── */\n#app { display: flex; height: 100vh; width: 100vw; }', header_footer_css)

sidebar_css = """
/* ── Sidebar nav (Collapsible Right) ───────────────────────── */
#sidebar {
  position: fixed; top: 60px; right: -300px; width: 260px; bottom: 40px;
  background: rgba(10,10,20,0.97);
  backdrop-filter: blur(24px);
  border-left: 1px solid var(--border);
  border-right: none;
  display: flex; flex-direction: column;
  padding: 24px 0; gap: 4px;
  z-index: 200;
  transition: right 0.3s cubic-bezier(0.4,0,0.2,1);
  box-shadow: -8px 0 40px rgba(0,0,0,0.3);
}
#sidebar.open { right: 0; }
"""

css = css.replace("""/* ── Sidebar nav ─────────────────────────────────────────── */
#sidebar {
  width: var(--nav-w); min-width: var(--nav-w);
  background: rgba(10,10,20,0.85);
  backdrop-filter: blur(24px);
  border-right: 1px solid var(--border);
  display: flex; flex-direction: column;
  padding: 24px 0; gap: 4px;
  z-index: 100;
}""", sidebar_css)

# Update WYSIWYG classes
wysiwyg_css = """
.editor-toolbar-global {
  display: flex; align-items: center; gap: 4px;
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  border-top: 1px solid var(--border);
  background: rgba(0,0,0,0.3); flex-shrink: 0; flex-wrap: wrap;
}

.wysiwyg-area {
  flex: 1; overflow-y: auto; padding: 28px 36px;
  color: var(--text);
  font-family: 'Inter', sans-serif; font-size: 16px; line-height: 1.75;
  outline: none; caret-color: var(--accent);
}
.wysiwyg-area:empty::before {
  content: attr(placeholder); color: var(--text-muted); pointer-events: none;
}
.wysiwyg-area h1 { font-size: 2em; font-weight: 800; margin: 0.6em 0 0.3em; letter-spacing: -0.5px; }
.wysiwyg-area h2 { font-size: 1.5em; font-weight: 700; margin: 0.6em 0 0.25em; }
.wysiwyg-area h3 { font-size: 1.2em; font-weight: 700; margin: 0.5em 0 0.2em; color: #c4b5fd; }
.wysiwyg-area ul  { margin-left: 1.5em; list-style: disc; }
.wysiwyg-area ol  { margin-left: 1.5em; list-style: decimal; }
.wysiwyg-area li  { margin: 0.25em 0; }
.wysiwyg-area hr  { border: none; border-top: 1px solid var(--border); margin: 1.5em 0; }
.wysiwyg-area strong { font-weight: 700; }
.wysiwyg-area em     { font-style: italic; }
.wysiwyg-area u      { text-decoration: underline; }
.wysiwyg-area code {
  background: rgba(255,255,255,0.08); border-radius: 4px;
  padding: 1px 6px; font-size: 0.9em; font-family: monospace;
}
.wysiwyg-area blockquote {
  border-left: 3px solid var(--accent); padding-left: 16px;
  margin-left: 0; color: var(--text-muted); font-style: italic;
}
.wysiwyg-area a { color: var(--accent2); text-decoration: underline; }
"""

# Replace old wysiwyg css
start_wysiwyg = css.find('#editor-toolbar {')
end_wysiwyg = css.find('/* Print styles */')
if start_wysiwyg != -1 and end_wysiwyg != -1:
    css = css[:start_wysiwyg] + wysiwyg_css + "\n" + css[end_wysiwyg:]

with open('nserver/static/style.css', 'w') as f:
    f.write(css)

# --- 3. Patch app.js ---
with open('nserver/static/app.js', 'r') as f:
    js = f.read()

# Replace saveNote
old_save_note = """async function saveNote() {
  const title   = document.getElementById('note-title').value.trim();
  const content = document.getElementById('note-content').value.trim();
  const course  = document.getElementById('note-course').value;
  if (!title || !content) { toast('Title and content required', 'error'); return; }
  try {
    await apiPost('/api/vault/note', { title, content, course });
    toast('Note saved to vault ✅', 'success');
    document.getElementById('note-title').value = '';
    document.getElementById('note-content').value = '';
  } catch(e) { toast('Save failed', 'error'); }
}"""

new_save_note = """
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

async function saveQuickNote() {
  const title   = document.getElementById('note-title').value.trim();
  const wysiwyg = document.getElementById('qn-note-wysiwyg');
  const content = htmlToMd(wysiwyg).trim();
  const course  = document.getElementById('note-course').value;
  
  if (!title || !content) { toast('Title and content required', 'error'); return; }
  try {
    await apiPost('/api/vault/note', { title, content, course });
    toast('Note saved to vault ✅', 'success');
    document.getElementById('note-title').value = '';
    wysiwyg.innerHTML = '';
    document.getElementById('qn-editor-status').textContent = 'READY';
  } catch(e) { toast('Save failed', 'error'); }
}

function onQnEditorInput() {
  document.getElementById('qn-editor-status').textContent = 'EDITING…';
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

  sendAIMessage(`Format and improve this note:\\n\\n${md}`);
}
"""
js = js.replace(old_save_note, new_save_note)

# Update AI format handler to support quick note
ai_format_handler_old = """    // If this was a format-note call, apply result back to editor
    if (_aiFormatMode && _edFileId) {
      const wysiwyg = document.getElementById('note-wysiwyg');
      wysiwyg.innerHTML = mdToHtml(fullText);
      _edDirty = true;
      setEdStatus('AI FORMATTED', 'ai');
      saveNote_wysiwyg();
      cancelAIContext();
      toast('Note reformatted by AI ✨', 'success');
    }"""

ai_format_handler_new = """    // If this was a format-note call, apply result back to editor
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
    }"""
js = js.replace(ai_format_handler_old, ai_format_handler_new)

# Fix navigation to close sidebar when item is clicked
nav_old = """function navigate(page) {
  if (!checkAuth()) return;
  currentPage = page;"""
nav_new = """function navigate(page) {
  if (!checkAuth()) return;
  currentPage = page;
  
  if (_sidebarOpen) toggleSidebar();
"""
js = js.replace(nav_old, nav_new)

with open('nserver/static/app.js', 'w') as f:
    f.write(js)

print("Patch applied successfully.")
