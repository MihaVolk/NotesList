import sqlite3

class DB:
    def __init__(self, database="database.db"):
        self.conn = sqlite3.connect(database)
        self.cur = self.conn.cursor()
        
    def close(self):
        self.conn.close()
        
    def commit(self):
        self.conn.commit()
        
    def add_user(self, username, password, full_name=None, phone=None, telegram_id=None):
        self.cur.execute("INSERT INTO users (username, password, full_name, phone, telegram_id) VALUES (?, ?, ?, ?, ?)", (username, password, full_name, phone, telegram_id))
        
    def add_note(self, title, content, created_at, priority, author_id, deadline_date = None):
        self.cur.execute("INSERT INTO notes (title, content, created_at, deadline_date, priority, author_id) VALUES (?, ?, ?, ?, ?, ?)",
                         (title, content, created_at, deadline_date, priority, author_id))
        
    def get_user_notes(self, author_id):
        self.cur.execute("SELECT * FROM notes WHERE author_id = ?", (author_id,))
        return self.cur.fetchall()
    
    def get_user_password(self, username):
        self.cur.execute("SELECT password FROM users WHERE username = ?", (username,))
        return self.cur.fetchone()

    def get_user_by_username(self, username):
        self.cur.execute("SELECT * FROM users WHERE username = ?", (username,))
        return self.cur.fetchone()
    
    def get_user_by_id(self, user_id):
        self.cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return self.cur.fetchone()
    
    def get_user_by_telegram(self, telegram_id):
        self.cur.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        return self.cur.fetchone()
    
    def link_tg(self, user_id, telegram_id):
        self.cur.execute("UPDATE users SET telegram_id = ? WHERE id = ?", (telegram_id, user_id))
    
    def delete_note(self, note_id):
        self.cur.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        
    def unlink(self, telegram_id):
        self.cur.execute(
            "UPDATE users SET telegram_id = NULL where telegram_id = ?", (telegram_id,))