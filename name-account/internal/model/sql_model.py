create_account_table = """
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    
    login TEXT NOT NULL,
    password TEXT NOT NULL,
    google_two_fa_key TEXT DEFAULT '',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_account_table = """
DROP TABLE IF EXISTS accounts CASCADE;
"""


create_tables_queries = [
    create_account_table,
]

drop_tables_queries = [
    drop_account_table,
]