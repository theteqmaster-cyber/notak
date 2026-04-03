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
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

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
    cursor = conn.cursor()
    
    try:
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

def search_files(query: str):
    """
    Search files using FTS5 match query.
    Returns a list of matching file records containing path, course, category.
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # We join the FTS table with the core table to return file metadata
    cursor.execute("""
        SELECT f.id, f.path, f.course, f.category, s.text_content
        FROM search_index s
        JOIN files f ON s.file_id = f.id
        WHERE search_index MATCH ?
        ORDER BY rank
    """, (query,))
    
    results = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return results

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
