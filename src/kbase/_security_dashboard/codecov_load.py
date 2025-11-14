"""
Load codecov data into postgres.
"""

import psycopg2
from psycopg2.extras import execute_values

from kbase._security_dashboard.codecov import CoverageData


def init_table(conn: psycopg2.extensions.connection):
    """
    Initialize the coverage table.
    """
    with conn.cursor() as cur:
        # Probably should make the tables configurable? Maybe not
        cur.execute("""
            CREATE TABLE IF NOT EXISTS coverage_history (
                org_user      VARCHAR(255) NOT NULL,
                repo          VARCHAR(255) NOT NULL,
                branch        VARCHAR(255) NOT NULL,
                commit        CHAR(40) NOT NULL,
                timestamp     TIMESTAMPTZ NOT NULL,
                coverage      NUMERIC(5,2) NOT NULL,
                PRIMARY KEY (org_user, repo, branch, commit)
            )
        """)
        
        # Create index
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_coverage_timestamp
                ON coverage_history (org_user, repo, branch, timestamp)
        """)
        
        conn.commit()


def save_coverage(
    conn: psycopg2.extensions.connection,
    coverage_data: CoverageData,
):
    """
    Insert coverage data into the table.
    Ignores rows that would violate the unique key.
    """
    rows = []
    for branch, commits in coverage_data.coverage.items():
        for c in commits:
            rows.append((
                coverage_data.owner_org,
                coverage_data.repo,
                branch,
                c.commit_id,
                c.timestamp,
                c.coverage
            ))
    
    if not rows:
        return

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO coverage_history (org_user, repo, branch, commit, timestamp, coverage)
            VALUES %s
            ON CONFLICT (org_user, repo, branch, commit) DO NOTHING
            """,
            rows
        )
        conn.commit()
