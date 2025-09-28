create_release_table = """
CREATE TABLE IF NOT EXISTS releases (
    id SERIAL PRIMARY KEY,
    service_name TEXT NOT NULL,
    release_tag TEXT NOT NULL,
    rollback_to_tag TEXT DEFAULT '',
    status TEXT NOT NULL,
    
    initiated_by TEXT NOT NULL,
    github_run_id TEXT NOT NULL,
    github_action_link TEXT NOT NULL,
    github_ref TEXT NOT NULL,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL
);
"""

drop_release_table = """
DROP TABLE IF EXISTS releases;
"""

# Обновить существующие списки:
create_queries = [create_release_table]
drop_queries = [drop_release_table]