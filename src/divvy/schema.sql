-- Database schema for the Divvy application

CREATE TABLE IF NOT EXISTS members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 1,
    paid_remainder_in_cycle BOOLEAN NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_type TEXT NOT NULL, -- 'expense' or 'deposit'
    description TEXT NOT NULL,
    remark TEXT,
    amount INTEGER NOT NULL, -- Stored in cents
    payer_id INTEGER,
    category_id INTEGER,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payer_id) REFERENCES members (id),
    FOREIGN KEY (category_id) REFERENCES categories (id)
);

-- Pre-populate with some default categories for shared living scenario
INSERT INTO categories (name) VALUES 
    ('Rent'), 
    ('Utilities (Water & Electricity)'), 
    ('Gas Bill'), 
    ('Groceries'), 
    ('Daily Necessities'), 
    ('Dining Out / Takeaway'), 
    ('Transportation'), 
    ('Other');
