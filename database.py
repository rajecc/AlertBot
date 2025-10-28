import sqlite3
from datetime import datetime, timedelta

DB_PATH = "database.db"

def connect_db():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Инициализация базы данных (если нет таблиц, они создаются)."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS downtimes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workshop_num INTEGER,
                unit_num INTEGER,
                start_time TEXT,
                end_time TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workshop_num INTEGER,
                unit_num INTEGER,
                time TEXT,
                info TEXT,
                author TEXT
            )
        """)
        conn.commit()

def save_error_data(workshop_num, unit_num, time, info):
    """Сохранение информации об ошибке."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO errors (workshop_num, unit_num, time, info, author) VALUES (?, ?, ?, ?, ?)",
            (workshop_num, unit_num, time, info)
        )
        conn.commit()

def save_start_downtime(workshop_num, unit_num, start_time):
    """Сохранение начала простоя с правильным форматом даты."""
    full_start_time = datetime.now().strftime("%Y-%m-%d") + f" {start_time}"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO downtimes (workshop_num, unit_num, start_time) VALUES (?, ?, ?)",
            (workshop_num, unit_num, full_start_time)
        )
        conn.commit()

def save_end_downtime(workshop_num, unit_num, end_time):
    """Завершение простоя и расчет его длительности с добавлением времени начала"""
    full_end_time = datetime.now().strftime("%Y-%m-%d") + f" {end_time}"
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, start_time FROM downtimes WHERE workshop_num=? AND unit_num=? AND end_time IS NULL ORDER BY id DESC LIMIT 1",
            (workshop_num, unit_num)
        )
        row = cursor.fetchone()

        if row:
            downtime_id, start_time = row
            cursor.execute(
                "UPDATE downtimes SET end_time=? WHERE id=?",
                (full_end_time, downtime_id)
            )
            conn.commit()
            return f"{start_time} - {full_end_time}"
        else:
            return "Не найдено начальное время простоя"




def delete_old_downtimes():
    """Удаляет записи о простоях, которым больше месяца."""
    conn = connect_db()
    cursor = conn.cursor()
    one_month_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM downtimes WHERE start_time < ?", (one_month_ago,))
    conn.commit()
    conn.close()

def get_downtime_report(period):
    """Получает отчет о простоях за последние 24 часа, 7 дней или 30 дней."""
    conn = connect_db()
    cursor = conn.cursor()
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if period == "day":
        since = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif period == "week":
        since = (datetime.now() - timedelta(weeks=1)).strftime("%Y-%m-%d %H:%M:%S")
    elif period == "month":
        since = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    else:
        return []

    cursor.execute("""
        SELECT workshop_num, unit_num, start_time, end_time 
        FROM downtimes 
        WHERE datetime(start_time) BETWEEN datetime(?) AND datetime(?)
           OR (end_time IS NOT NULL AND datetime(end_time) BETWEEN datetime(?) AND datetime(?))
    """, (since, now, since, now))
    
    report = cursor.fetchall()
    conn.close()
    return report




def get_active_downtimes():
    """Получает список активных простоев (без завершенного времени)."""
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("SELECT workshop_num, unit_num, start_time FROM downtimes WHERE end_time IS NULL")
    active_downtimes = cursor.fetchall()
    conn.close()
    return active_downtimes

def save_breakdown(workshop_num, unit_num, time, info, author):
    """Сохранение информации о поломке."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO errors (workshop_num, unit_num, time, info, author) VALUES (?, ?, ?, ?, ?)",
            (workshop_num, unit_num, time, info, author)
        )
        conn.commit()


# Инициализация базы данных
init_db()
