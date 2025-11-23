"""
Manage repository metadata in postgres.
"""

import logging
import psycopg2


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the repo_metadata table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS repo_metadata (
                org_user       VARCHAR(255) NOT NULL,
                repo           VARCHAR(255) NOT NULL,
                type           VARCHAR(50) NOT NULL,
                main_branch    VARCHAR(50) NOT NULL,
                dev_branch     VARCHAR(50) NOT NULL,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                PRIMARY KEY (org_user, repo)
            )
        """)
        conn.commit()


def upsert_repo_metadata(
    conn: psycopg2.extensions.connection,
    repos: list[dict[str, str | list[str]]],
):
    """
    Insert or update repository metadata.
    
    Updates the updated_at timestamp if type or branches change.
    
    repos - list of repo config dictionaries with keys:
            - org (str)
            - repo (str)
            - type (str) - e.g., "core", "support"
            - main_branch (str)
            - dev_branch (str)
    """
    logr = logging.getLogger(__name__)
    
    if not repos:
        logr.warning("No repositories to upsert")
        return
    
    with conn.cursor() as cur:
        for repo_config in repos:
            org = repo_config["org"]
            repo = repo_config["repo"]
            repo_type = repo_config["type"]
            main_branch = repo_config["main_branch"]
            dev_branch = repo_config["dev_branch"]
            
            cur.execute(
                """
                INSERT INTO repo_metadata (org_user, repo, type, main_branch, dev_branch, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
                ON CONFLICT (org_user, repo) 
                DO UPDATE SET
                    type = EXCLUDED.type,
                    main_branch = EXCLUDED.main_branch,
                    dev_branch = EXCLUDED.dev_branch,
                    updated_at = CASE
                        WHEN repo_metadata.type != EXCLUDED.type 
                             OR repo_metadata.main_branch != EXCLUDED.main_branch
                             OR repo_metadata.dev_branch != EXCLUDED.dev_branch
                        THEN NOW()
                        ELSE repo_metadata.updated_at
                    END
                """,
                (org, repo, repo_type, main_branch, dev_branch)
            )
            
            logr.debug(f"Upserted metadata for {org}/{repo} (type={repo_type})")
        
        conn.commit()
    
    logr.info(f"Upserted metadata for {len(repos)} repositories")
