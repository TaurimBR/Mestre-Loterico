import sqlite3
import os

DB_PATH = 'src/data/mestre_loterico.db'

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            codigo_loterico TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'user',
            must_change_password BOOLEAN DEFAULT 1
        )
    ''')
    
    # Sponsors table
    c.execute('''
        CREATE TABLE IF NOT EXISTS sponsors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image_path TEXT,
            link TEXT,
            active BOOLEAN DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(codigo_loterico, password_hash, role='user', must_change_password=True):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (codigo_loterico, password_hash, role, must_change_password)
            VALUES (?, ?, ?, ?)
        ''', (codigo_loterico, password_hash, role, must_change_password))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user(codigo_loterico):
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE codigo_loterico = ?', (codigo_loterico,))
    user = c.fetchone()
    conn.close()
    return dict(user) if user else None

def update_password(codigo_loterico, new_password_hash):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        UPDATE users 
        SET password_hash = ?, must_change_password = 0 
        WHERE codigo_loterico = ?
    ''', (new_password_hash, codigo_loterico))
    conn.commit()
    conn.close()

def get_all_users():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT codigo_loterico, role, must_change_password FROM users')
    users = c.fetchall()
    conn.close()
    return [dict(u) for u in users]

def delete_user(codigo_loterico):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM users WHERE codigo_loterico = ?', (codigo_loterico,))
    conn.commit()
    conn.close()

def update_user_password_admin(codigo_loterico, new_password_hash):
    conn = get_connection()
    c = conn.cursor()
    # Força o usuário a mudar a senha no próximo login
    c.execute('''
        UPDATE users 
        SET password_hash = ?, must_change_password = 1 
        WHERE codigo_loterico = ?
    ''', (new_password_hash, codigo_loterico))
    conn.commit()
    conn.close()
