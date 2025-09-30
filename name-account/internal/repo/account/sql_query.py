create_account = """
INSERT INTO accounts (
    login,
    password,
    google_two_fa_key
)
VALUES (
    :login,
    :password,
    ''
)
RETURNING id;
"""

get_account_by_id = """
SELECT * FROM accounts
WHERE id = :account_id;
"""

get_account_by_login = """
SELECT * FROM accounts
WHERE login = :login;
"""

set_two_fa_key = """
UPDATE accounts
SET google_two_fa_key = :google_two_fa_key
WHERE id = :account_id;
"""

delete_two_fa_key = """
UPDATE accounts
SET google_two_fa_key = ''
WHERE id = :account_id;
"""

update_password = """
UPDATE accounts
SET password = :new_password
WHERE id = :account_id;
"""