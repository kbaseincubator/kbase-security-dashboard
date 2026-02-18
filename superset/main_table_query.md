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

latest_vulnerabilities AS (
    SELECT DISTINCT ON (org_user, repo)
        org_user,
        repo,
        critical,
        high
    FROM vulnerability_snapshots
    ORDER BY org_user, repo, timestamp DESC
)

SELECT 
    r.org_user AS org,
    r.repo,
    r.branch,
    ts.test_status,
    c.coverage,
    d.dependencies,
    v.critical AS critical_vulns,
    v.high AS high_vulns
FROM repos_expanded r
LEFT JOIN latest_test_status ts ON r.org_user = ts.org_user 
    AND r.repo = ts.repo 
    AND r.branch = ts.branch
LEFT JOIN latest_coverage c ON r.org_user = c.org_user 
    AND r.repo = c.repo 
    AND r.branch = c.branch
LEFT JOIN latest_dependencies d ON r.org_user = d.org_user 
    AND r.repo = d.repo
LEFT JOIN latest_vulnerabilities v ON r.org_user = v.org_user 
    AND r.repo = v.repo
ORDER BY r.org_user, r.repo, r.branch_order;
