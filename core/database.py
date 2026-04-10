import os
import sqlite3

VAULT_DIR = os.path.expanduser("~/StudyVault")
DB_PATH = os.path.join(VAULT_DIR, ".metadata", "library.db")

def get_connection():
    """Returns a connection to the SQLite database."""
    # Ensure metadata directory exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_db():
    """Create tables if they don't exist, including FTS5 for search."""
    conn = get_connection()
    cursor = conn.cursor()

    # Core files table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            file_hash TEXT NOT NULL,
            course TEXT NOT NULL,
            category TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            deleted_at TIMESTAMP DEFAULT NULL
        )
    """)
    
    # Migration: Add deleted_at column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE files ADD COLUMN deleted_at TIMESTAMP DEFAULT NULL")
    except sqlite3.OperationalError:
        # Column already exists
        pass

    # Calendar table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calendar_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_date TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # High scores table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS high_scores (
            game_id TEXT PRIMARY KEY,
            score INTEGER DEFAULT 0,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Search index virtual table
    cursor.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
            file_id UNINDEXED,
            text_content
        )
    """)
    
    conn.commit()
    conn.close()

def check_duplicate_hash(file_hash: str) -> bool:
    """Check if a file hash already exists in the vault."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM files WHERE file_hash = ?", (file_hash,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def insert_file(path: str, file_hash: str, course: str, category: str, text_content: str = "") -> int:
    """Insert a new file record and its extracted text for search."""
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO files (path, file_hash, course, category)
            VALUES (?, ?, ?, ?)
        """, (path, file_hash, course, category))
        
        file_id = cursor.lastrowid
        
        if text_content:
            cursor.execute("""
                INSERT INTO search_index (file_id, text_content)
                VALUES (?, ?)
            """, (file_id, text_content))
            
        conn.commit()
        return file_id
    except sqlite3.IntegrityError:
        # Path already exists or other constraint failed
        conn.rollback()
        return -1
    finally:
        conn.close()
def mark_as_deleted(path: str):
    """Mark a file as deleted with a timestamp."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET deleted_at = CURRENT_TIMESTAMP WHERE path = ?", (path,))
    conn.commit()
    conn.close()

def restore_file_by_path(path: str):
    """Restore a deleted file by clearing the deleted_at flag."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE files SET deleted_at = NULL WHERE path = ?", (path,))
    conn.commit()
    conn.close()

def get_deleted_files():
    """Retrieve all files currently in the recycle bin."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM files WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC")
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def purge_old_deleted_items(days: int = 30):
    """Permanently delete items from disk and DB that have been in the bin for too long."""
    conn = get_connection()
    cursor = conn.cursor()
    # SQLite DATE('now', '-30 days')
    cursor.execute("""
        SELECT path FROM files 
        WHERE deleted_at IS NOT NULL 
        AND deleted_at < datetime('now', ?)
    """, (f"-{days} days",))
    
    to_delete = [row['path'] for row in cursor.fetchall()]
    conn.close()
    
    for path in to_delete:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        delete_file_by_path(path)
    
    return len(to_delete)

def delete_file_by_path(path: str):
    """Remove a file record and its search index entry by path."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get ID first for search index cleanup if CASCADE not available
    cursor.execute("SELECT id FROM files WHERE path = ?", (path,))
    result = cursor.fetchone()
    if result:
        file_id = result['id']
        cursor.execute("DELETE FROM search_index WHERE file_id = ?", (file_id,))
        cursor.execute("DELETE FROM files WHERE id = ?", (file_id,))
        conn.commit()
    conn.close()

def search_files(query: str):
    """
    Search files using FTS5 match query with snippets.
    Returns matching file records with a snippet of the text containing the keyword.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # We join the FTS table with the core table and fetch a snippet
    cursor.execute("""
        SELECT f.id, f.path, f.course, f.category, snippet(search_index, 1, '[', ']', '...', 20) as snippet
        FROM search_index
        JOIN files f ON search_index.file_id = f.id
        WHERE search_index MATCH ? AND f.deleted_at IS NULL
        ORDER BY rank
    """, (query,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_recent_files(limit: int = 5):
    """Retrieve the most recently added files that are not deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM files 
        WHERE deleted_at IS NULL 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def get_library_stats():
    """Returns a dictionary containing library metrics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT count(*) FROM files WHERE deleted_at IS NULL")
    total_files = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(DISTINCT course) FROM files WHERE deleted_at IS NULL AND course != 'Notei'")
    course_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT count(*) FROM files WHERE category = 'Notes' AND deleted_at IS NULL")
    notei_count = cursor.fetchone()[0]
    
    conn.close()
    return {
        "total_files": total_files,
        "course_count": course_count,
        "notei_count": notei_count
    }

def get_all_courses():
    """Retrieve a unique list of courses currently in the vault."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT course FROM files ORDER BY course")
    results = [row['course'] for row in cursor.fetchall()]
    conn.close()
    return results

def insert_event(date: str, title: str, description: str = ""):
    """Insert a new event for a specific date (YYYY-MM-DD)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO calendar_events (event_date, title, description)
        VALUES (?, ?, ?)
    """, (date, title, description))
    conn.commit()
    conn.close()

def get_events_for_date(date: str):
    """Retrieve all events for a specific date (YYYY-MM-DD)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM calendar_events WHERE event_date = ? ORDER BY id ASC", (date,))
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

def update_high_score(game_id, score):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM high_scores WHERE game_id = ?", (game_id,))
        row = cursor.fetchone()
        if not row or score > row['score']:
            cursor.execute("""
                INSERT INTO high_scores (game_id, score)
                VALUES (?, ?)
                ON CONFLICT(game_id) DO UPDATE SET 
                    score = excluded.score,
                    updated_at = CURRENT_TIMESTAMP
            """, (game_id, score))
            conn.commit()
            return True
        return False
    finally:
        conn.close()

def get_high_score(game_id):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM high_scores WHERE game_id = ?", (game_id,))
        row = cursor.fetchone()
        return row['score'] if row else 0
    finally:
        conn.close()
