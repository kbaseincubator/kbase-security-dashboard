WITH repos_expanded AS (
    -- Create one row per repo per branch (main and dev)
    SELECT
        org_user,
        repo,
        main_branch AS branch,
        1 AS branch_order  -- main branch first
    FROM repo_metadata

    UNION ALL  -- cheaper than just UNION and we know we don't have duplicates

    SELECT
        org_user,
        repo,
        dev_branch AS branch,
        2 AS branch_order  -- dev branch second
    FROM repo_metadata
),

latest_test_status AS (
    SELECT DISTINCT ON (org_user, repo, branch)
        org_user,
        repo,
        branch,
        CASE
            WHEN success THEN '✅ Pass'
            ELSE '❌ Fail'
        END AS test_status
    FROM test_status
    ORDER BY org_user, repo, branch, timestamp DESC
),

latest_coverage AS (
    SELECT DISTINCT ON (org_user, repo, branch)
        org_user,
        repo,
        branch,
        coverage
    FROM coverage_history
    ORDER BY org_user, repo, branch, timestamp DESC
),

latest_dependencies AS (
    SELECT DISTINCT ON (org_user, repo)
        org_user,
        repo,
        dependencies
    FROM dependabot_snapshots
    ORDER BY org_user, repo, timestamp DESC
),

latest_dependabot_alerts AS (
    -- Dependabot alerts are repo-wide (not branch-specific)
    SELECT DISTINCT ON (org_user, repo)
        org_user,
        repo,
        critical,
        high
    FROM dependabot_alerts
    ORDER BY org_user, repo, timestamp DESC
),

latest_code_scanning_alerts AS (
    -- Code Scanning alerts are branch-specific
    SELECT DISTINCT ON (org_user, repo, branch)
        org_user,
        repo,
        branch,
        critical,
        high
    FROM code_scanning_alerts
    ORDER BY org_user, repo, branch, timestamp DESC
),

latest_trivy AS (
    -- Trivy scans are branch-specific
    SELECT DISTINCT ON (org_user, repo, branch)
        org_user,
        repo,
        branch,
        critical,
        high
    FROM trivy_scans
    ORDER BY org_user, repo, branch, timestamp DESC
)

SELECT
    r.org_user || '/' || r.repo AS repository,
    r.branch,
    ts.test_status,
    c.coverage,
    d.dependencies,
    -- Sum critical severity issues from all security sources
    COALESCE(da.critical, 0) + COALESCE(csa.critical, 0) + COALESCE(t.critical, 0) AS sec_crit,
    -- Sum high severity issues from all security sources
    COALESCE(da.high, 0) + COALESCE(csa.high, 0) + COALESCE(t.high, 0) AS sec_high
FROM repos_expanded r
LEFT JOIN latest_test_status ts ON r.org_user = ts.org_user
    AND r.repo = ts.repo
    AND r.branch = ts.branch
LEFT JOIN latest_coverage c ON r.org_user = c.org_user
    AND r.repo = c.repo
    AND r.branch = c.branch
LEFT JOIN latest_dependencies d ON r.org_user = d.org_user
    AND r.repo = d.repo
LEFT JOIN latest_dependabot_alerts da ON r.org_user = da.org_user
    AND r.repo = da.repo
    -- Dependabot alerts apply to both branches (repo-wide)
LEFT JOIN latest_code_scanning_alerts csa ON r.org_user = csa.org_user
    AND r.repo = csa.repo
    AND r.branch = csa.branch
LEFT JOIN latest_trivy t ON r.org_user = t.org_user
    AND r.repo = t.repo
    AND r.branch = t.branch
ORDER BY r.org_user, r.repo, r.branch_order;
