"""
Load Dependabot snapshot data into postgres.
"""

import psycopg2
from psycopg2.extras import execute_values

from kbase._security_dashboard.dependabot import DependabotSnapshot, get_dependabot_snapshot


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the dependabot_snapshots table.
    """
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dependabot_snapshots (
                org_user            VARCHAR(255) NOT NULL,
                repo                VARCHAR(255) NOT NULL,
                timestamp           TIMESTAMPTZ NOT NULL,
                dependencies        INTEGER NOT NULL,
                PRIMARY KEY (org_user, repo, timestamp)
            )
        """)
        
        # Create index for time-series queries
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_dependabot_snapshots_date
                ON dependabot_snapshots (org_user, repo, timestamp DESC)
        """)
        
        conn.commit()


def save_snapshot(
    conn: psycopg2.extensions.connection,
    snapshot: DependabotSnapshot,
):
    """
    Insert a Dependabot snapshot into the table.
    
    If a snapshot already exists for the same repo and timestamp,
    it will be updated with the new values.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO dependabot_snapshots (org_user, repo, timestamp, dependencies)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (org_user, repo, timestamp) DO NOTHING
            """,
            (
                snapshot.owner_org,
                snapshot.repo,
                snapshot.snapshot_date,
                snapshot.total_dependencies,
            )
        )
        conn.commit()


def take_snapshot(
    conn: psycopg2.extensions.connection,
    owner_org: str,
    repo: str,
    github_token: str | None = None,
):
    """
    Convenience function to take a snapshot and save it in one call.
    
    conn - psycopg2 database connection
    owner_org - the owner or organization that owns the repo
    repo - the repo name
    github_token - optional GitHub personal access token for higher rate limits
    """
    
    snapshot = get_dependabot_snapshot(owner_org, repo, github_token)
    save_snapshot(conn, snapshot)
