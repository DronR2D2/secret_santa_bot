# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_name='santa.db'):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def create_tables(self):
        # Таблица участников
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS participants (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                full_name TEXT,
                address TEXT,
                gift_code TEXT,
                recipient_id INTEGER,
                santa_id INTEGER,
                is_active BOOLEAN DEFAULT 1,
                registered_at TIMESTAMP
            )
        ''')
        
        # Таблица жеребьевки
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS draw_results (
                santa_id INTEGER,
                recipient_id INTEGER,
                draw_date TIMESTAMP,
                PRIMARY KEY (santa_id, recipient_id)
            )
        ''')
        
        self.conn.commit()
    
    def add_participant(self, user_id, username, full_name):
        self.cursor.execute('''
            INSERT OR REPLACE INTO participants 
            (user_id, username, full_name, registered_at) 
            VALUES (?, ?, ?, ?)
        ''', (user_id, username, full_name, datetime.now()))
        self.conn.commit()
    
    def update_address(self, user_id, address):
        self.cursor.execute('''
            UPDATE participants SET address = ? WHERE user_id = ?
        ''', (address, user_id))
        self.conn.commit()
    
    def update_gift_code(self, user_id, gift_code):
        self.cursor.execute('''
            UPDATE participants SET gift_code = ? WHERE user_id = ?
        ''', (gift_code, user_id))
        self.conn.commit()
    
    def get_participant(self, user_id):
        self.cursor.execute('SELECT * FROM participants WHERE user_id = ?', (user_id,))
        return self.cursor.fetchone()
    
    def get_all_participants(self):
        self.cursor.execute('SELECT * FROM participants WHERE is_active = 1')
        return self.cursor.fetchall()
    
    def perform_draw(self):
        """Проводит жеребьевку"""
        participants = self.get_all_participants()
        if len(participants) < 2:
            return False
        
        # Получаем ID участников
        user_ids = [p[0] for p in participants]
        
        # Создаем пары (санта -> получатель)
        import random
        shuffled = user_ids.copy()
        
        # Гарантируем, что никто не выпадет сам себе
        while True:
            random.shuffle(shuffled)
            valid = all(s != r for s, r in zip(user_ids, shuffled))
            if valid:
                break
        
        # Очищаем предыдущие результаты
        self.cursor.execute('DELETE FROM draw_results')
        
        # Сохраняем новые пары
        for santa_id, recipient_id in zip(user_ids, shuffled):
            self.cursor.execute('''
                INSERT INTO draw_results (santa_id, recipient_id, draw_date)
                VALUES (?, ?, ?)
            ''', (santa_id, recipient_id, datetime.now()))
            
            # Обновляем в таблице participants
            self.cursor.execute('''
                UPDATE participants 
                SET recipient_id = ?, santa_id = ? 
                WHERE user_id = ?
            ''', (recipient_id, santa_id, santa_id))
        
        self.conn.commit()
        return True
    
    def get_recipient(self, santa_id):
        """Получаем информацию о получателе для данного санты"""
        self.cursor.execute('''
            SELECT p.* FROM participants p
            JOIN draw_results dr ON p.user_id = dr.recipient_id
            WHERE dr.santa_id = ?
        ''', (santa_id,))
        return self.cursor.fetchone()
    
    def get_santa(self, recipient_id):
        """Получаем информацию о санте для данного получателя"""
        self.cursor.execute('''
            SELECT p.* FROM participants p
            JOIN draw_results dr ON p.user_id = dr.santa_id
            WHERE dr.recipient_id = ?
        ''', (recipient_id,))
        return self.cursor.fetchone()
    
    def is_draw_completed(self):
        self.cursor.execute('SELECT COUNT(*) FROM draw_results')
        return self.cursor.fetchone()[0] > 0
    
    def close(self):
        self.conn.close()