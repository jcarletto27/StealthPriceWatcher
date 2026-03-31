import sqlite3

def init_db():
    conn = sqlite3.connect('tracker.db')
    c = conn.cursor()
    
    # Updated table schema with cookies_json column
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            url TEXT UNIQUE,
            domain TEXT,
            name_selector TEXT,
            price_selector TEXT,
            cookies_json TEXT,
            last_status TEXT DEFAULT 'pending',
            last_error TEXT,
            alert_email TEXT,
            alert_threshold REAL,
            alert_lowest_30d BOOLEAN DEFAULT 0
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER,
            price REAL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()
