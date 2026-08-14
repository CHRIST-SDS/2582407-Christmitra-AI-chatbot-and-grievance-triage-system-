import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'grievances.db')

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Grievances table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS grievances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        student_ref TEXT,
        category TEXT NOT NULL,
        urgency TEXT NOT NULL,
        raw_message TEXT NOT NULL,
        ai_summary TEXT,
        status TEXT DEFAULT 'open',
        routed_to TEXT,
        campus TEXT
    );
    """)
    
    # Chat logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now', 'localtime')),
        role TEXT NOT NULL,
        message TEXT NOT NULL,
        intent TEXT,
        retrieved_chunk_ids TEXT,
        grievance_id INTEGER REFERENCES grievances(id)
    );
    """)
    
    # Source documents table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS source_documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        url TEXT UNIQUE NOT NULL,
        category TEXT,
        campus TEXT,
        scraped_at TEXT DEFAULT (datetime('now', 'localtime')),
        content_hash TEXT
    );
    """)
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
