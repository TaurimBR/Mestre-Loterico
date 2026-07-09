import sqlite3
from src.utils.db import get_connection

def add_sponsor(name, image_path, link, active=True):
    conn = get_connection()
    c = conn.cursor()
    # Deactivate others if this is active
    if active:
        c.execute('UPDATE sponsors SET active = 0')
    
    c.execute('''
        INSERT INTO sponsors (name, image_path, link, active)
        VALUES (?, ?, ?, ?)
    ''', (name, image_path, link, active))
    conn.commit()
    conn.close()

def get_active_sponsor():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM sponsors WHERE active = 1 ORDER BY id DESC LIMIT 1')
    sponsor = c.fetchone()
    conn.close()
    return dict(sponsor) if sponsor else None

def get_all_sponsors():
    conn = get_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM sponsors ORDER BY id DESC')
    sponsors = c.fetchall()
    conn.close()
    return [dict(s) for s in sponsors]

def set_active_sponsor(sponsor_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('UPDATE sponsors SET active = 0')
    c.execute('UPDATE sponsors SET active = 1 WHERE id = ?', (sponsor_id,))
    conn.commit()
    conn.close()
    
def delete_sponsor(sponsor_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute('DELETE FROM sponsors WHERE id = ?', (sponsor_id,))
    conn.commit()
    conn.close()
