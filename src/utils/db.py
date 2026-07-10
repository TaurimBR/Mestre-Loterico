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
            must_change_password BOOLEAN DEFAULT 1,
            nome_loterica TEXT DEFAULT ''
        )
    ''')
    
    # Check if we need to add the column 'nome_loterica' to existing users table
    try:
        c.execute("SELECT nome_loterica FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN nome_loterica TEXT DEFAULT ''")
    
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
    
    # Conversations table
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_loterico TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (codigo_loterico) REFERENCES users(codigo_loterico)
        )
    ''')

    # Messages table
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER,
            role TEXT,
            content TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def add_user(codigo_loterico, password_hash, role='user', must_change_password=True, nome_loterica=''):
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute('''
            INSERT INTO users (codigo_loterico, password_hash, role, must_change_password, nome_loterica)
            VALUES (?, ?, ?, ?, ?)
        ''', (codigo_loterico, password_hash, role, must_change_password, nome_loterica))
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
    c.execute('SELECT codigo_loterico, role, must_change_password, nome_loterica FROM users')
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
    # Also force them to change password again
    c.execute('''
        UPDATE users 
        SET password_hash = ?, must_change_password = 1 
        WHERE codigo_loterico = ?
    ''', (new_password_hash, codigo_loterico))
    conn.commit()
    conn.close()

def create_conversation(codigo_loterico, title):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO conversations (codigo_loterico, title)
        VALUES (?, ?)
    ''', (codigo_loterico, title))
    conn.commit()
    conversation_id = c.lastrowid
    conn.close()
    return conversation_id

def get_conversations(codigo_loterico):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM conversations
        WHERE codigo_loterico = ?
        ORDER BY updated_at DESC
    ''', (codigo_loterico,))
    conversations = c.fetchall()
    conn.close()
    return [dict(row) for row in conversations]

def get_messages(conversation_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        SELECT * FROM messages
        WHERE conversation_id = ?
        ORDER BY created_at ASC
    ''', (conversation_id,))
    messages = c.fetchall()
    conn.close()
    return [dict(row) for row in messages]

def add_message(conversation_id, role, content):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (conversation_id, role, content)
        VALUES (?, ?, ?)
    ''', (conversation_id, role, content))
    
    # Update conversation's updated_at timestamp
    c.execute('''
        UPDATE conversations
        SET updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (conversation_id,))
    
    conn.commit()
    conn.close()
