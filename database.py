import sqlite3
import json
from datetime import datetime, date
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        is_subscribed INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Registered Groups and Channels for auto-broadcast
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chats (
        chat_id INTEGER PRIMARY KEY,
        chat_type TEXT,
        title TEXT,
        is_active INTEGER DEFAULT 1,
        added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Active quiz session per user
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        user_id INTEGER PRIMARY KEY,
        subject TEXT NOT NULL,
        question_ids TEXT NOT NULL,
        current_index INTEGER DEFAULT 0,
        score INTEGER DEFAULT 0,
        total_questions INTEGER DEFAULT 0,
        last_message_id INTEGER DEFAULT NULL,
        auto_next INTEGER DEFAULT 1,
        is_live INTEGER DEFAULT 0,
        slot_id INTEGER DEFAULT 0,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # User overall statistics by subject
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stats (
        user_id INTEGER,
        subject TEXT,
        total_attempted INTEGER DEFAULT 0,
        total_correct INTEGER DEFAULT 0,
        quizzes_completed INTEGER DEFAULT 0,
        last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (user_id, subject),
        FOREIGN KEY (user_id) REFERENCES users(user_id)
    )
    """)

    # Live Quiz Slot Submissions / Leaderboard Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        slot_id INTEGER,
        subject TEXT,
        score INTEGER,
        total INTEGER,
        quiz_date TEXT,
        time_taken_seconds INTEGER DEFAULT 0,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()

def register_user(user_id: int, username: str, first_name: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (user_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name
    """, (user_id, username, first_name))
    conn.commit()
    conn.close()

def register_chat(chat_id: int, chat_type: str, title: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO chats (chat_id, chat_type, title, is_active)
        VALUES (?, ?, ?, 1)
        ON CONFLICT(chat_id) DO UPDATE SET
            chat_type = excluded.chat_type,
            title = excluded.title,
            is_active = 1
    """, (chat_id, chat_type, title))
    conn.commit()
    conn.close()

def get_broadcast_targets():
    """Returns list of all user IDs and channel/group chat IDs for live alerts."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT user_id FROM users WHERE is_subscribed = 1")
    users = [r["user_id"] for r in cursor.fetchall()]
    
    cursor.execute("SELECT chat_id FROM chats WHERE is_active = 1")
    chats = [r["chat_id"] for r in cursor.fetchall()]
    
    conn.close()
    # Combine unique IDs
    all_targets = list(set(users + chats))
    return all_targets

def save_session(user_id: int, subject: str, question_ids: list, current_index: int = 0, score: int = 0, last_message_id: int = None, auto_next: int = 1, is_live: int = 0, slot_id: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    q_ids_json = json.dumps(question_ids)
    cursor.execute("""
        INSERT INTO sessions (user_id, subject, question_ids, current_index, score, total_questions, last_message_id, auto_next, is_live, slot_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            subject = excluded.subject,
            question_ids = excluded.question_ids,
            current_index = excluded.current_index,
            score = excluded.score,
            total_questions = excluded.total_questions,
            last_message_id = excluded.last_message_id,
            auto_next = excluded.auto_next,
            is_live = excluded.is_live,
            slot_id = excluded.slot_id,
            started_at = CURRENT_TIMESTAMP
    """, (user_id, subject, q_ids_json, current_index, score, len(question_ids), last_message_id, auto_next, is_live, slot_id))
    conn.commit()
    conn.close()

def update_session_progress(user_id: int, current_index: int, score: int, last_message_id: int = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE sessions
        SET current_index = ?, score = ?, last_message_id = ?
        WHERE user_id = ?
    """, (current_index, score, last_message_id, user_id))
    conn.commit()
    conn.close()

def get_session(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        data = dict(row)
        data["question_ids"] = json.loads(data["question_ids"])
        return data
    return None

def clear_session(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def record_answer_stat(user_id: int, subject: str, is_correct: bool):
    conn = get_connection()
    cursor = conn.cursor()
    correct_inc = 1 if is_correct else 0
    cursor.execute("""
        INSERT INTO stats (user_id, subject, total_attempted, total_correct, quizzes_completed, last_active)
        VALUES (?, ?, 1, ?, 0, CURRENT_TIMESTAMP)
        ON CONFLICT(user_id, subject) DO UPDATE SET
            total_attempted = total_attempted + 1,
            total_correct = total_correct + ?,
            last_active = CURRENT_TIMESTAMP
    """, (user_id, subject, correct_inc, correct_inc))
    conn.commit()
    conn.close()

def record_quiz_completed(user_id: int, subject: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE stats
        SET quizzes_completed = quizzes_completed + 1,
            last_active = CURRENT_TIMESTAMP
        WHERE user_id = ? AND subject = ?
    """, (user_id, subject))
    conn.commit()
    conn.close()

def record_live_result(user_id: int, slot_id: int, subject: str, score: int, total: int, time_taken_seconds: int = 0):
    conn = get_connection()
    cursor = conn.cursor()
    today_str = date.today().isoformat()
    cursor.execute("""
        INSERT INTO live_results (user_id, slot_id, subject, score, total, quiz_date, time_taken_seconds)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (user_id, slot_id, subject, score, total, today_str, time_taken_seconds))
    conn.commit()
    conn.close()

def get_live_slot_leaderboard(slot_id: int, quiz_date: str = None, limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    if not quiz_date:
        quiz_date = date.today().isoformat()
    cursor.execute("""
        SELECT u.first_name, u.username, lr.score, lr.total, lr.time_taken_seconds
        FROM live_results lr
        JOIN users u ON lr.user_id = u.user_id
        WHERE lr.slot_id = ? AND lr.quiz_date = ?
        ORDER BY lr.score DESC, lr.time_taken_seconds ASC
        LIMIT ?
    """, (slot_id, quiz_date, limit))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_user_stats(user_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT subject, total_attempted, total_correct, quizzes_completed
        FROM stats
        WHERE user_id = ?
    """, (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_leaderboard(limit: int = 10):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT u.first_name, u.username, 
               SUM(s.total_correct) as correct_sum,
               SUM(s.total_attempted) as attempted_sum
        FROM stats s
        JOIN users u ON s.user_id = u.user_id
        GROUP BY s.user_id
        HAVING attempted_sum > 0
        ORDER BY correct_sum DESC, attempted_sum ASC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]
