import sqlite3

def setup_database():
    conn = sqlite3.connect('trading_bot.db', check_same_thread=False)
    c = conn.cursor()

    # Create users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        email TEXT UNIQUE,
        password TEXT,
        username TEXT,
        phone_number TEXT,
        paper_balance REAL DEFAULT 0
    )''')

    # Create deposits table
    c.execute('''CREATE TABLE IF NOT EXISTS deposits (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        timestamp REAL,
        amount REAL,
        balance_usd REAL,
        status TEXT,
        wallet_address TEXT,  -- New column for wallet address
        transaction_hash TEXT,
        contract_address TEXT,
        transaction_fee REAL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    # Create trades table
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

    # Create spot_grids table
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

    # Create tokens table
    c.execute('''CREATE TABLE IF NOT EXISTS tokens (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        token TEXT NOT NULL,
        expires_at DATETIME NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')

    conn.commit()
    print("Successfully created")
    conn.close()

if __name__ == '__main__':
    setup_database()
