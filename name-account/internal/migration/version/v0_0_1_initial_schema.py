from internal import interface, model
from internal.migration.base import Migration, MigrationInfo


class InitialSchemaMigration(Migration):

    def get_info(self) -> MigrationInfo:
        return MigrationInfo(
            version="v0_0_1",
            name="initial_schema",
        )

    async def up(self, db: interface.IDB):
        queries = [
            create_account_table
        ]

        await db.multi_query(queries)

    async def down(self, db: interface.IDB):
        queries = [
            drop_account_table
        ]

        await db.multi_query(queries)

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