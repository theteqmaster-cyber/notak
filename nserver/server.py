"""
nserver/server.py
Flask + Flask-SocketIO HTTP server powering the NServer web app.
All routes use the existing core/database.py and filesystem — no duplicate state.
"""

import os
import io
import json
import mimetypes
import threading
import datetime

from flask import Flask, jsonify, request, send_file, abort, send_from_directory
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS

# ── Ensure correct MIME types for audio files ────────────────────────────────
mimetypes.add_type("audio/mpeg",  ".mp3")
mimetypes.add_type("audio/mp4",   ".m4a")   # critical — avoids browser refusal
mimetypes.add_type("audio/wav",   ".wav")
mimetypes.add_type("audio/ogg",   ".ogg")
mimetypes.add_type("audio/flac",  ".flac")

# ── Path to static SPA ───────────────────────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

# ── Active clients registry (sid → metadata) ─────────────────────────────────
_clients: dict = {}           # {sid: {client_id, username, page, last_seen}}
_clients_lock = threading.Lock()

# ── Mboard strokes store (in-memory, per-session) ────────────────────────────
_mboard_strokes: list = []    # list of stroke dicts
_mboard_lock = threading.Lock()


def create_app():
    app = Flask(
        __name__,
        static_folder=STATIC_DIR,
        static_url_path="/static",
    )
    app.config["SECRET_KEY"] = "notak-nserver-secret"

    CORS(app, resources={r"/api/*": {"origins": "*"}, r"/stream/*": {"origins": "*"}})
    socketio = SocketIO(
        app,
        cors_allowed_origins="*",
        async_mode="threading",
        logger=False,
        engineio_logger=False,
    )

    # ── Serve SPA index for all non-API routes ────────────────────────────────
    @app.route("/")
    def index():
        return send_from_directory(STATIC_DIR, "index.html")

    @app.route("/icon.png")
    def serve_icon():
        return send_file(os.path.join(os.getcwd(), "icon.png"))

    # ── Auth Check ────────────────────────────────────────────────────────────
    @app.before_request
    def check_auth():
        # Exclude static files, shutdown endpoint, and socket.io
        if request.path.startswith("/static/") or request.path.startswith("/socket.io/") or request.path in ["/", "/icon.png", "/_shutdown"]:
            return None
        
        # Simple password check via header or query param
        auth_pw = request.headers.get("X-Notak-Password") or request.args.get("pw")
        if auth_pw != "wish26":
            return jsonify({"error": "Unauthorized"}), 401

    @app.route("/<path:path>")
    def catch_all(path):
        full = os.path.join(STATIC_DIR, path)
        if os.path.isfile(full):
            return send_from_directory(STATIC_DIR, path)
        return send_from_directory(STATIC_DIR, "index.html")

    # ── Graceful shutdown endpoint ────────────────────────────────────────────
    @app.route("/_shutdown", methods=["POST"])
    def shutdown():
        func = request.environ.get("werkzeug.server.shutdown")
        if func:
            func()
        return "Shutting down…", 200

    # ── Status ────────────────────────────────────────────────────────────────
    @app.route("/api/status")
    def api_status():
        with _clients_lock:
            clients = list(_clients.values())
        return jsonify({
            "status": "online",
            "version": "1.0.0",
            "clients": clients,
            "client_count": len(clients),
            "server_time": datetime.datetime.now().isoformat(),
        })

    @app.route("/api/status/clients")
    def api_clients():
        with _clients_lock:
            clients = list(_clients.values())
        return jsonify(clients)

    # ═════════════════════════════════════════════════════════════════════════
    # VAULT / STUDY HUB
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/vault/courses")
    def api_courses():
        from core.database import get_all_courses
        courses = get_all_courses()
        return jsonify(courses)

    @app.route("/api/vault/files")
    def api_files():
        from core.database import get_connection
        course = request.args.get("course", "all")
        conn = get_connection()
        cursor = conn.cursor()
        if course == "all":
            cursor.execute(
                "SELECT id, path, course, category, created_at FROM files "
                "WHERE deleted_at IS NULL ORDER BY created_at DESC"
            )
        else:
            cursor.execute(
                "SELECT id, path, course, category, created_at FROM files "
                "WHERE course=? AND deleted_at IS NULL ORDER BY created_at DESC",
                (course,)
            )
        rows = [dict(r) for r in cursor.fetchall()]
        conn.close()
        # Add basename for convenience
        for r in rows:
            r["name"] = os.path.basename(r["path"])
        return jsonify(rows)

    @app.route("/api/vault/file/<int:file_id>")
    def api_file_meta(file_id):
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE id=?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            abort(404)
        d = dict(row)
        d["name"] = os.path.basename(d["path"])
        return jsonify(d)

    @app.route("/api/vault/search")
    def api_search():
        from core.database import search_files
        q = request.args.get("q", "").strip()
        if not q:
            return jsonify([])
        results = search_files(q)
        for r in results:
            r["name"] = os.path.basename(r["path"])
        return jsonify(results)

    @app.route("/stream/file/<int:file_id>")
    def stream_file(file_id):
        """Serve any vault file (PDF, image, audio) with correct MIME type."""
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path, category FROM files WHERE id=?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        if not row or not os.path.exists(row["path"]):
            abort(404)

        path = row["path"]
        ext  = os.path.splitext(path)[1].lower()

        # Explicit MIME map — don't rely on OS mime database for audio
        mime_map = {
            ".mp3":  "audio/mpeg",
            ".m4a":  "audio/mp4",
            ".wav":  "audio/wav",
            ".ogg":  "audio/ogg",
            ".flac": "audio/flac",
            ".pdf":  "application/pdf",
            ".png":  "image/png",
            ".jpg":  "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif":  "image/gif",
            ".webp": "image/webp",
            ".md":   "text/plain; charset=utf-8",
            ".txt":  "text/plain; charset=utf-8",
            ".csv":  "text/plain; charset=utf-8",
        }
        mime = mime_map.get(ext, "application/octet-stream")

        # Audio files: support HTTP range requests for seeking
        if mime.startswith("audio/"):
            return _range_send(path, mime)

        return send_file(path, mimetype=mime, conditional=True)

    def _range_send(filepath: str, mime: str):
        """HTTP range-request aware file sender — lets web audio player seek."""
        file_size = os.path.getsize(filepath)
        range_header = request.headers.get("Range", None)

        if not range_header:
            with open(filepath, "rb") as f:
                data = f.read()
            from flask import Response
            resp = Response(data, 200, mimetype=mime)
            resp.headers["Accept-Ranges"] = "bytes"
            resp.headers["Content-Length"] = str(file_size)
            return resp

        # Parse "bytes=start-end"
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end   = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = end - start + 1

        with open(filepath, "rb") as f:
            f.seek(start)
            data = f.read(length)

        from flask import Response
        resp = Response(
            data, 206,
            mimetype=mime,
            direct_passthrough=True,
        )
        resp.headers["Content-Range"]  = f"bytes {start}-{end}/{file_size}"
        resp.headers["Accept-Ranges"]  = "bytes"
        resp.headers["Content-Length"] = str(length)
        return resp

    @app.route("/api/vault/note", methods=["POST"])
    def api_save_note():
        """Create or update a markdown note in the vault."""
        data    = request.get_json(force=True)
        course  = data.get("course", "Inbox")
        title   = data.get("title", "Untitled Note")
        content = data.get("content", "")
        file_id = data.get("file_id")     # if editing existing note

        from core.importer import VAULT_DIR
        course_dir = os.path.join(VAULT_DIR, course, "Notes")
        os.makedirs(course_dir, exist_ok=True)

        if file_id:
            # Overwrite existing note
            from core.database import get_connection
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT path FROM files WHERE id=?", (file_id,))
            row = cursor.fetchone()
            conn.close()
            if row and os.path.exists(row["path"]):
                with open(row["path"], "w", encoding="utf-8") as f:
                    f.write(content)
                return jsonify({"ok": True, "path": row["path"]})

        # New note
        import re
        first_line = content.split('\n')[0][:50]
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

        return jsonify({"ok": True, "path": filepath, "file_id": fid})

    @app.route("/api/vault/note/<int:file_id>/content")
    def api_note_content(file_id):
        """Return the raw markdown content of a note file."""
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM files WHERE id=? AND deleted_at IS NULL", (file_id,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            abort(404)
        path = row["path"]
        if not os.path.exists(path):
            abort(404)
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        return jsonify({"content": content, "path": path})

    @app.route("/api/vault/note/<int:file_id>", methods=["PUT"])
    def api_update_note(file_id):
        """Overwrite an existing note file with new markdown content."""
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT path FROM files WHERE id=? AND deleted_at IS NULL", (file_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"error": "File not found"}), 404
        path = row["path"]
        conn.close()

        data    = request.get_json(force=True)
        content = data.get("content", "")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            # Update search index
            conn2 = get_connection()
            try:
                c2 = conn2.cursor()
                c2.execute("UPDATE search_index SET text_content=? WHERE file_id=?", (content[:4000], file_id))
                conn2.commit()
            finally:
                conn2.close()
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ═════════════════════════════════════════════════════════════════════════
    # AI ASSISTANT — SSE streaming via Groq/Llama
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/ai/chat", methods=["POST"])
    def api_ai_chat():
        """Stream an AI response using SSE (text/event-stream)."""
        import os, json as _json
        from flask import Response, stream_with_context
        from dotenv import load_dotenv
        load_dotenv()

        GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
        if not GROQ_API_KEY:
            return jsonify({"error": "GROQ_API_KEY not configured"}), 503

        data         = request.get_json(force=True)
        user_message = data.get("message", "").strip()
        history      = data.get("history", [])
        system_p     = data.get("system_prompt", "You are Ingracia, a brilliant and friendly AI study assistant for Notak. You MUST be extremely concise and straight to the point. Never over-explain. Do not write long paragraphs unless absolutely necessary. If the user says a simple greeting like 'hi', respond with a very short and simple greeting back. Render clear, structured markdown in your answers. Make sure your information is not biased. If you are in an unknown or unclear state, state it clearly—do not try to give pleasing or invented answers. In mathematics, you must ALWAYS perform a double calculation before giving a response (e.g., calculate once, get the result, calculate again, get the result; if they match, provide the answer to the user. If they do not match, find the error and compare until they are the same). I will not tolerate calculation errors.")

        if not user_message:
            return jsonify({"error": "Empty message"}), 400

        selected_model = data.get("model", "groq")
        if selected_model == "qwen":
            url   = "http://localhost:11434/v1/chat/completions"
            model = "qwen2.5:7b"
        else:
            is_openai = GROQ_API_KEY.startswith("sk-")
            url       = "https://api.openai.com/v1/chat/completions" if is_openai else "https://api.groq.com/openai/v1/chat/completions"
            model     = "gpt-4o" if is_openai else "llama-3.3-70b-versatile"

        messages = [{"role": "system", "content": system_p}]
        for msg in history[-20:]:   # cap history at 20 turns
            messages.append(msg)
        messages.append({"role": "user", "content": user_message})

        if selected_model == "qwen":
            headers = {"Content-Type": "application/json"}
        else:
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY.strip()}",
                "Content-Type":  "application/json",
            }
        payload = {"model": model, "messages": messages, "temperature": 0.7, "stream": True}

        def generate():
            try:
                import httpx
                with httpx.stream("POST", url, headers=headers, json=payload, timeout=60.0) as resp:
                    for line in resp.iter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            line = line[6:]
                        if line == "[DONE]":
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            chunk = _json.loads(line)
                            token = chunk["choices"][0].get("delta", {}).get("content", "")
                            if token:
                                yield f"data: {_json.dumps({'token': token})}\n\n"
                        except Exception:
                            continue
            except Exception as e:
                yield f"data: {_json.dumps({'error': str(e)})}\n\n"

        return Response(
            stream_with_context(generate()),
            content_type="text/event-stream",
            headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
        )

    @app.route("/api/vault/import", methods=["POST"])
    def api_import_file():
        """Upload a file into the StudyVault."""
        if "file" not in request.files:
            return jsonify({"error": "No file"}), 400
        f       = request.files["file"]
        course  = request.form.get("course", "Inbox")
        category = request.form.get("category", "Files")

        from core.importer import VAULT_DIR
        dest_dir = os.path.join(VAULT_DIR, course, category)
        os.makedirs(dest_dir, exist_ok=True)

        filepath = os.path.join(dest_dir, f.filename)
        f.save(filepath)

        from core.importer import get_file_hash, process_file_import
        from core.database import check_duplicate_hash
        fhash = get_file_hash(filepath)
        if check_duplicate_hash(fhash):
            os.remove(filepath)
            return jsonify({"error": "duplicate"}), 409

        process_file_import(filepath, course)
        return jsonify({"ok": True, "path": filepath})

    # ═════════════════════════════════════════════════════════════════════════
    # MUSIC HUB
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/music/playlist")
    def api_music_playlist():
        playlist_path = os.path.join(os.getcwd(), ".notak_playlist.json")
        if not os.path.exists(playlist_path):
            return jsonify([])
        try:
            with open(playlist_path, "r") as f:
                data = json.load(f)
        except Exception:
            return jsonify([])

        # Enrich with id (we use DB id for streaming), basename, exists flag
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()

        enriched = []
        for entry in data:
            path = entry.get("path", "")
            if not os.path.exists(path):
                continue
            ext = os.path.splitext(path)[1].lower()

            # Look up DB id
            cursor.execute("SELECT id FROM files WHERE path=?", (path,))
            row = cursor.fetchone()
            db_id = row["id"] if row else None

            enriched.append({
                "path":        path,
                "name":        os.path.basename(path),
                "ext":         ext,
                "db_id":       db_id,
                "play_count":  entry.get("play_count", 0),
                "last_played": entry.get("last_played", ""),
                # Web player streams via /stream/music/<encoded_path>
                "stream_url":  f"/stream/music?path={_encode_path(path)}",
            })

        conn.close()
        enriched.sort(key=lambda x: (x["play_count"], x["last_played"]), reverse=True)
        return jsonify(enriched)

    def _encode_path(path: str) -> str:
        import urllib.parse
        return urllib.parse.quote(path, safe="")

    @app.route("/stream/music")
    def stream_music():
        """Stream a music file by absolute path (web client only uses this)."""
        import urllib.parse
        raw = request.args.get("path", "")
        path = urllib.parse.unquote(raw)

        if not path or not os.path.exists(path):
            abort(404)

        ext = os.path.splitext(path)[1].lower()
        mime_map = {
            ".mp3":  "audio/mpeg",
            ".m4a":  "audio/mp4",     # ← correct MIME for m4a
            ".wav":  "audio/wav",
            ".ogg":  "audio/ogg",
            ".flac": "audio/flac",
        }
        mime = mime_map.get(ext, "audio/mpeg")
        return _range_send(path, mime)

    @app.route("/api/music/played", methods=["POST"])
    def api_music_played():
        """Web client reports a track was played — update play_count."""
        data = request.get_json(force=True)
        path = data.get("path", "")
        if not path:
            return jsonify({"ok": False}), 400

        playlist_path = os.path.join(os.getcwd(), ".notak_playlist.json")
        try:
            with open(playlist_path, "r") as f:
                playlist = json.load(f)
        except Exception:
            playlist = []

        now   = datetime.datetime.now().isoformat()
        found = False
        for entry in playlist:
            if entry.get("path") == path:
                entry["play_count"]  = entry.get("play_count", 0) + 1
                entry["last_played"] = now
                found = True
                break
        if not found:
            playlist.append({"path": path, "play_count": 1, "last_played": now})

        with open(playlist_path, "w") as f:
            json.dump(playlist, f, indent=2)

        return jsonify({"ok": True})

    # ═════════════════════════════════════════════════════════════════════════
    # INTERNET RADIO
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/radio/stations")
    def api_radio_stations():
        radios_path = os.path.join(os.getcwd(), ".notak_radios.json")
        if not os.path.exists(radios_path):
            return jsonify([])
        try:
            with open(radios_path, "r") as f:
                return jsonify(json.load(f))
        except Exception:
            return jsonify([])

    @app.route("/api/radio/station", methods=["POST"])
    def api_radio_add():
        data = request.get_json(force=True)
        name = data.get("name", "").strip()
        url  = data.get("url",  "").strip()
        if not name or not url:
            return jsonify({"error": "name and url required"}), 400

        radios_path = os.path.join(os.getcwd(), ".notak_radios.json")
        try:
            with open(radios_path, "r") as f:
                stations = json.load(f)
        except Exception:
            stations = []

        stations.append({"name": name, "url": url})
        with open(radios_path, "w") as f:
            json.dump(stations, f, indent=2)

        return jsonify({"ok": True})

    @app.route("/api/radio/station/<int:index>", methods=["DELETE"])
    def api_radio_delete(index):
        radios_path = os.path.join(os.getcwd(), ".notak_radios.json")
        try:
            with open(radios_path, "r") as f:
                stations = json.load(f)
            stations.pop(index)
            with open(radios_path, "w") as f:
                json.dump(stations, f, indent=2)
            return jsonify({"ok": True})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    # ═════════════════════════════════════════════════════════════════════════
    # CALENDAR
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/calendar/events")
    def api_calendar_events():
        from core.database import get_events_for_date
        date = request.args.get("date", datetime.date.today().isoformat())
        return jsonify(get_events_for_date(date))

    @app.route("/api/calendar/upcoming")
    def api_calendar_upcoming():
        from core.database import get_upcoming_events
        return jsonify(get_upcoming_events(5))

    @app.route("/api/calendar/events/month")
    def api_calendar_month():
        """Return all event dates in a given year-month for dot indicators."""
        from core.database import get_connection
        ym = request.args.get("month", datetime.date.today().strftime("%Y-%m"))
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DISTINCT event_date FROM calendar_events WHERE event_date LIKE ?",
            (f"{ym}%",)
        )
        dates = [row["event_date"] for row in cursor.fetchall()]
        conn.close()
        return jsonify(dates)

    @app.route("/api/calendar/event", methods=["POST"])
    def api_calendar_add():
        from core.database import insert_event
        data  = request.get_json(force=True)
        date  = data.get("date", "")
        title = data.get("title", "").strip()
        desc  = data.get("description", "")
        if not date or not title:
            return jsonify({"error": "date and title required"}), 400
        insert_event(date, title, desc)
        return jsonify({"ok": True})

    @app.route("/api/calendar/event/<int:event_id>", methods=["DELETE"])
    def api_calendar_delete(event_id):
        from core.database import get_connection
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM calendar_events WHERE id=?", (event_id,))
        conn.commit()
        conn.close()
        return jsonify({"ok": True})

    # ═════════════════════════════════════════════════════════════════════════
    # SESSIONS
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/sessions")
    def api_sessions():
        from core.database import get_session_history
        days = request.args.get("days")
        return jsonify(get_session_history(int(days) if days else None))

    @app.route("/api/sessions", methods=["POST"])
    def api_sessions_add():
        from core.database import insert_session
        data   = request.get_json(force=True)
        intent = data.get("intent", "Study")
        mins   = data.get("duration_minutes", 25)
        status = data.get("status", "finished")
        insert_session(intent, mins, status)
        return jsonify({"ok": True})

    # ═════════════════════════════════════════════════════════════════════════
    # MBOARD (simple — strokes only, in-memory per server session)
    # ═════════════════════════════════════════════════════════════════════════
    @app.route("/api/mboard/strokes")
    def api_mboard_get():
        with _mboard_lock:
            return jsonify(list(_mboard_strokes))

    @app.route("/api/mboard/stroke", methods=["POST"])
    def api_mboard_add():
        stroke = request.get_json(force=True)
        with _mboard_lock:
            _mboard_strokes.append(stroke)
        socketio.emit("mboard_stroke", stroke)
        return jsonify({"ok": True})

    @app.route("/api/mboard/undo", methods=["POST"])
    def api_mboard_undo():
        with _mboard_lock:
            if _mboard_strokes:
                _mboard_strokes.pop()
        socketio.emit("mboard_undo", {})
        return jsonify({"ok": True})

    @app.route("/api/mboard/clear", methods=["POST"])
    def api_mboard_clear():
        with _mboard_lock:
            _mboard_strokes.clear()
        socketio.emit("mboard_clear", {})
        return jsonify({"ok": True})

    # ═════════════════════════════════════════════════════════════════════════
    # SOCKETIO — Active user tracking
    # ═════════════════════════════════════════════════════════════════════════
    @socketio.on("connect")
    def on_connect():
        with _clients_lock:
            _clients[request.sid] = {
                "sid":       request.sid,
                "client_id": "",
                "username":  "Guest",
                "page":      "home",
                "last_seen": datetime.datetime.now().isoformat(),
                "ip":        request.remote_addr or "unknown",
            }

    @socketio.on("disconnect")
    def on_disconnect():
        with _clients_lock:
            _clients.pop(request.sid, None)

    @socketio.on("heartbeat")
    def on_heartbeat(data):
        with _clients_lock:
            if request.sid in _clients:
                _clients[request.sid].update({
                    "client_id": data.get("client_id", ""),
                    "username":  data.get("username",  "Guest"),
                    "page":      data.get("page",      "home"),
                    "last_seen": datetime.datetime.now().isoformat(),
                })

    return app, socketio
