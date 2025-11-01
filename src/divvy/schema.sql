-- Database schema for the Divvy application
CREATE TABLE IF NOT EXISTS periods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    start_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    end_date DATETIME NULL,
    is_settled BOOLEAN NOT NULL DEFAULT 0,
    settled_date DATETIME NULL
);

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
    transaction_type TEXT NOT NULL, -- 'expense' 'deposit' 'refund'
    description TEXT NULL,
    amount INTEGER NOT NULL, -- Stored in cents
    payer_id INTEGER,
    category_id INTEGER,
    period_id INTEGER NOT NULL,
    is_personal BOOLEAN NOT NULL DEFAULT 0, -- If 1, expense only affects payer (not split)
    TIMESTAMP DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payer_id) REFERENCES members (id),
    FOREIGN KEY (category_id) REFERENCES categories (id),
    FOREIGN KEY (period_id) REFERENCES periods (id)
);

-- Pre-populate with default categories
INSERT INTO
    categories (name)
VALUES
    ('Utilities (Water & Electricity & Gas)'),
    ('Groceries'),
    ('Daily Necessities'),
    ('Rent'),
    ('Other');
