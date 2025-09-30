create_account_table = """
CREATE TABLE IF NOT EXISTS accounts (
    id SERIAL PRIMARY KEY,
    
    account_id INTEGER NOT NULL,
    refresh_token TEXT DEFAULT '',
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

drop_account_table = """
DROP TABLE IF EXISTS accounts;
"""

create_queries = [create_account_table]
drop_queries = [drop_account_table]