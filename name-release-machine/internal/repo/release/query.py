create_release = """
INSERT INTO releases (
    service_name, 
    release_tag, 
    status, 
    initiated_by, 
    github_run_id, 
    github_action_link, 
    github_ref
)
VALUES (
    :service_name, 
    :release_tag, 
    :status, 
    :initiated_by, 
    :github_run_id, 
    :github_action_link, 
    :github_ref
)
RETURNING id;
"""

get_release_by_id = """
SELECT * FROM releases
WHERE id = :release_id
"""

get_active_releases = """
SELECT * FROM releases
WHERE status IN (
    'initiated',
    'initiated',
    'stage_building',
    'stage_test_rollback',
    'manual_testing',
    'manual_test_passed',
    'deploying',
    'production_rollback'
)
ORDER BY created_at DESC;
"""

get_successful_releases = """
SELECT * FROM releases
WHERE status IN (
    'deployed',
    'rollback_done'
)
ORDER BY created_at DESC;
"""

get_failed_releases = """
SELECT * FROM releases
WHERE status IN (
    'stage_building_failed',
    'stage_test_rollback_failed',
    'manual_test_failed',
    'production_failed',
    'rollback_failed'
)
ORDER BY created_at DESC;
"""