create_account = """
INSERT INTO accounts (
    account_id,
    refresh_token
)
VALUES (
    :account_id,
    ''
)
RETURNING id;
"""

account_by_id = """
SELECT * FROM accounts
WHERE account_id = :account_id;
"""

account_by_refresh_token = """
SELECT * FROM accounts
WHERE refresh_token = :refresh_token;
"""

update_refresh_token = """
UPDATE accounts
SET refresh_token = :refresh_token
WHERE account_id = :account_id;
"""