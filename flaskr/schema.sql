CREATE TABLE user_info (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username TEXT UNIQUE NOT NULL,
  password TEXT NOT NULL,
  balance DECIMAL(15,2) DEFAULT 1000000.00,
  role TEXT DEFAULT 'user'
);

CREATE TABLE user_assets (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  symbol TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  FOREIGN KEY (user_id) REFERENCES user_info (id)
);

CREATE TABLE stock_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    adjusted_close REAL NOT NULL,
    simple_return REAL,
    log_return REAL,
    cumulative_return REAL,
    FOREIGN KEY (user_id) REFERENCES user_info (id),
    UNIQUE(symbol, date) ON CONFLICT REPLACE
);

CREATE TABLE transactions_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    symbol TEXT,
    type TEXT,
    quantity INTEGER,
    price REAL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_info (id)
);

CREATE TABLE contact_us (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE index_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    adjusted_close REAL NOT NULL,
    simple_return REAL,
    log_return REAL,
    cumulative_return REAL,
    UNIQUE(symbol, date) ON CONFLICT IGNORE

);
