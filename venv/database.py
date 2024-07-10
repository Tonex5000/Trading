import sqlite3

def setup_database():
    conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT,
        email TEXT,
        phone_number TEXT,
        paper_balance REAL DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        address TEXT,
        amount REAL,
        balance_usd REAL,
        status TEXT,
        transaction_hash TEXT,
        timestamp INTEGER DEFAULT (strftime('%s', 'now')),
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS trades (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        symbol TEXT,
        type TEXT,
        side TEXT,
        amount REAL,
        price REAL,
        timestamp INTEGER,
        spot_grid_id INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(spot_grid_id) REFERENCES spot_grids(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS spot_grids (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        trading_pair TEXT,
        trading_strategy TEXT,
        roi REAL,
        pnl REAL,
        runtime TEXT,
        min_investment REAL,
        status TEXT,
        user_count INTEGER,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    conn.commit()
    print("Successfully created")
    conn.close()

if __name__ == '__main__':
    setup_database()
