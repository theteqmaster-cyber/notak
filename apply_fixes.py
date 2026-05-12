import re
import os

# 1. Update style.css
css_path = 'nserver/static/style.css'
with open(css_path, 'r') as f:
    css = f.read()

# Replace .ed-btn styling
old_btn_css = """.editor-toolbar-global {
  display: flex; align-items: center; gap: 4px;
  padding: 10px 16px; border-bottom: 1px solid var(--border);
  border-top: 1px solid var(--border);
  background: rgba(0,0,0,0.3); flex-shrink: 0; flex-wrap: wrap;
}
.ed-btn {
  padding: 5px 10px; border-radius: 7px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid transparent;
  background: transparent; color: var(--text-muted);
  transition: all 0.15s; font-family: inherit;
}"""

new_btn_css = """.editor-toolbar-global {
  display: flex; align-items: center; gap: 6px;
  padding: 12px 20px; border-bottom: 1px solid var(--border);
  border-top: 1px solid var(--border);
  background: rgba(10,10,20,0.6); flex-shrink: 0; flex-wrap: wrap;
}
.ed-btn {
  padding: 6px 12px; border-radius: 6px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid rgba(255,255,255,0.05);
  background: rgba(255,255,255,0.03); color: var(--text-muted);
  transition: all 0.2s; font-family: inherit;
}
.ed-btn:hover { background: rgba(255,255,255,0.1); color: var(--text); border-color: rgba(255,255,255,0.15); box-shadow: 0 2px 8px rgba(0,0,0,0.2); }
.ed-btn:active { background: rgba(124,58,237,0.2); color: #a78bfa; border-color: var(--accent); }"""

if old_btn_css in css:
    css = css.replace(old_btn_css, new_btn_css)
else:
    print("Could not find old_btn_css")

# Append modern footer css if not present
if "modern-footer" not in css:
    css += """
/* Modern Footer */
.modern-footer {
  background: #0a0a0f; border-top: 1px solid var(--border);
  display: flex; flex-direction: column; z-index: 150;
  flex-shrink: 0;
}
.footer-top {
  display: flex; justify-content: space-between; padding: 40px 60px;
  gap: 40px;
}
.footer-brand .footer-logo { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.footer-brand .footer-logo span { font-weight: 900; font-size: 18px; color: white; }
.footer-brand p { color: var(--text-muted); font-size: 13px; line-height: 1.6; max-width: 350px; }
.footer-links { display: flex; gap: 80px; }
.footer-col { display: flex; flex-direction: column; gap: 12px; }
.footer-col h4 { font-size: 14px; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.footer-col a { color: var(--text-muted); font-size: 13px; text-decoration: none; transition: color 0.2s; }
.footer-col a:hover { color: var(--accent2); }
.social-icons { display: flex; gap: 10px; margin-bottom: 8px; }
.social-icons a { background: rgba(255,255,255,0.05); padding: 8px; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; width: 32px; height: 32px; }
.social-icons a:hover { background: rgba(255,255,255,0.1); }
.footer-bottom {
  display: flex; justify-content: space-between; align-items: center;
  padding: 20px 60px; border-top: 1px solid rgba(255,255,255,0.05);
  font-size: 12px; color: var(--text-muted);
}
"""

with open(css_path, 'w') as f:
    f.write(css)

# 2. Update index.html
html_path = 'nserver/static/index.html'
with open(html_path, 'r') as f:
    html = f.read()

# Remove note-title input
html = re.sub(r'<input class="input" id="note-title"[^>]+>\s*', '', html)

# Update footer
old_footer = re.search(r'<footer id="global-footer".*?</footer>', html, re.DOTALL)
if old_footer:
    new_footer_html = """<footer id="global-footer" class="modern-footer">
    <div class="footer-top">
      <div class="footer-brand">
        <div class="footer-logo">
          <img src="/icon.png" style="width:24px;border-radius:6px;"/>
          <span>Notak Study Hub</span>
        </div>
        <p>Your digital academic workspace for organizing courses,<br/>taking structured notes, and collaborating with peers.</p>
      </div>
      <div class="footer-links">
        <div class="footer-col">
          <h4>Product</h4>
          <a href="#">Features</a>
          <a href="#">Pricing</a>
          <a href="#">Support</a>
          <a href="#">API</a>
        </div>
        <div class="footer-col">
          <h4>Connect</h4>
          <div class="social-icons">
            <a href="#">GH</a>
            <a href="#">TW</a>
            <a href="#">MAIL</a>
          </div>
          <a href="#">Privacy Policy</a>
          <a href="#">Terms of Service</a>
        </div>
      </div>
    </div>
    <div class="footer-bottom">
      <span>&copy; 2026 Notak Study Hub. Built with ❤️ for university students.</span>
      <span>Created by mphathisi for NUST students</span>
    </div>
  </footer>"""
    html = html.replace(old_footer.group(0), new_footer_html)
else:
    print("Could not find old footer")

with open(html_path, 'w') as f:
    f.write(html)

# 3. Update server.py note creation logic
py_path = 'nserver/server.py'
with open(py_path, 'r') as f:
    py = f.read()

old_server_logic = """        # New note
        safe_title = "".join(c for c in title if c.isalnum() or c in " _-").strip()
        timestamp  = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename   = f"{safe_title}_{timestamp}.md"
        filepath   = os.path.join(course_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# {title}\\n\\n{content}")

        from core.importer import get_file_hash
        from core.database import insert_file, check_duplicate_hash
        fhash = get_file_hash(filepath)
        if not check_duplicate_hash(fhash):
            insert_file(filepath, fhash, course, "Notes", content[:2000])

        return jsonify({"ok": True, "path": filepath})"""

new_server_logic = """        # New note
        import re
        first_line = content.split('\\n')[0][:50]
        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', first_line).strip('_')
        if not safe_name: safe_name = "untitled_note"
        date_str = datetime.datetime.now().strftime("%d_%b_%y").lower()
        filename = f"{safe_name}_{date_str}_sf26.md"
        filepath = os.path.join(course_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        from core.importer import get_file_hash
        from core.database import insert_file, check_duplicate_hash, get_connection
        fhash = get_file_hash(filepath)
        
        fid = None
        if not check_duplicate_hash(fhash):
            fid = insert_file(filepath, fhash, course, "Notes", content[:2000])
        else:
            conn = get_connection()
            c = conn.cursor()
            c.execute("SELECT id FROM files WHERE path=?", (filepath,))
            row = c.fetchone()
            if row: fid = row["id"]
            conn.close()

        return jsonify({"ok": True, "path": filepath, "file_id": fid})"""

if old_server_logic in py:
    py = py.replace(old_server_logic, new_server_logic)
else:
    print("Could not find old server logic")
    
with open(py_path, 'w') as f:
    f.write(py)

# 4. Update app.js Quick Note Save
js_path = 'nserver/static/app.js'
with open(js_path, 'r') as f:
    js = f.read()

old_save_qn = """async function saveQuickNote() {
  const wysiwyg = document.getElementById('qn-note-wysiwyg');
  const md = htmlToMd(wysiwyg).trim();
  const title   = document.getElementById('note-title').value.trim() || 'Quick Note';
  const course  = document.getElementById('note-course').value;
  if (!md) return;

  document.getElementById('qn-editor-status').textContent = 'SAVING…';
  try {
    const r = await fetch('/api/vault/note', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
      body: JSON.stringify({ title, content: md, course })
    });
    if (r.ok) {
      document.getElementById('qn-editor-status').textContent = 'SAVED ✓';
      toast('Note saved to vault ✅', 'success');
      // optionally clear: wysiwyg.innerHTML=''; document.getElementById('note-title').value='';
    } else {
      document.getElementById('qn-editor-status').textContent = 'SAVE ERROR';
    }
  } catch(e) {
    document.getElementById('qn-editor-status').textContent = 'SAVE ERROR';
  }
}"""

new_save_qn = """let _qnSaveTimer = null;
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
    
    // Determine method: if we have a file ID, we PUT, else POST. Wait, the python code handles 'file_id' inside POST!
    const r = await fetch('/api/vault/note?pw=' + _notakPassword, {
      method: 'POST', // Backend handles overwrite if file_id is provided
      headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
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
  document.getElementById('note-wysiwyg').innerHTML = '';
  document.getElementById('note-wysiwyg').focus();
  setEdStatus('READY', '');
}
"""

if old_save_qn in js:
    js = js.replace(old_save_qn, new_save_qn)
else:
    print("Could not find old_save_qn")
    
# Hook onQnEditorInput to qn-note-wysiwyg
# Quick Note initialization:
js = js.replace("document.getElementById('qn-note-wysiwyg').addEventListener('input', function() {", 
                "document.getElementById('qn-note-wysiwyg').addEventListener('input', function() { onQnEditorInput();")

# Update saveNote_wysiwyg to handle new_vault_note correctly via POST
old_save_wysiwyg = """async function saveNote_wysiwyg(sync = false) {
  if (!_edFileId) return;
  const wysiwyg = document.getElementById('note-wysiwyg');
  const md = htmlToMd(wysiwyg);
  if (!md.trim()) return;

  try {
    const r = await fetch(`/api/vault/note/${_edFileId}?pw=${_notakPassword}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
      body:    JSON.stringify({ content: md }),
    });"""

new_save_wysiwyg = """async function saveNote_wysiwyg(sync = false) {
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
      if (data.ok && data.file_id) _edFileId = data.file_id;
    } else {
      r = await fetch(`/api/vault/note/${_edFileId}?pw=${_notakPassword}`, {
        method:  'PUT',
        headers: { 'Content-Type': 'application/json', 'X-Notak-Password': _notakPassword },
        body:    JSON.stringify({ content: md }),
      });
    }"""
    
if old_save_wysiwyg in js:
    js = js.replace(old_save_wysiwyg, new_save_wysiwyg)
else:
    print("Could not find old_save_wysiwyg")
    
with open(js_path, 'w') as f:
    f.write(js)

print("Patch applied successfully.")
