import sqlite3
import json
from datetime import datetime
from config import DB_PATH

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # Table for storing user details
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Table for active quiz session per user
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
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Table for overall user statistics by subject
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

def save_session(user_id: int, subject: str, question_ids: list, current_index: int = 0, score: int = 0, last_message_id: int = None, auto_next: int = 1):
    conn = get_connection()
    cursor = conn.cursor()
    q_ids_json = json.dumps(question_ids)
    cursor.execute("""
        INSERT INTO sessions (user_id, subject, question_ids, current_index, score, total_questions, last_message_id, auto_next)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            subject = excluded.subject,
            question_ids = excluded.question_ids,
            current_index = excluded.current_index,
            score = excluded.score,
            total_questions = excluded.total_questions,
            last_message_id = excluded.last_message_id,
            auto_next = excluded.auto_next,
            started_at = CURRENT_TIMESTAMP
    """, (user_id, subject, q_ids_json, current_index, score, len(question_ids), last_message_id, auto_next))
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
