Test:

```sql
SELECT
    ts.timestamp,
    ts.org_user || '/' || ts.repo AS repository,
    CASE
        WHEN ts.branch = m.main_branch THEN 'main'
        WHEN ts.branch = m.dev_branch THEN 'develop'
    END AS cnclbrnch,
    CASE
        WHEN success THEN '✅ Pass'
        ELSE '❌ Fail'
    END AS status
FROM test_status ts
JOIN repo_metadata m ON ts.org_user = m.org_user AND ts.repo = m.repo
ORDER BY ts.timestamp DESC
```

Coverage:

```sql
SELECT
    ch.timestamp,
    ch.org_user || '/' || ch.repo AS repository,
    CASE
        WHEN ch.branch = m.main_branch THEN 'main'
        WHEN ch.branch = m.dev_branch THEN 'develop'
    END AS cnclbrnch,
    ch.coverage
FROM coverage_history ch
JOIN repo_metadata m ON ch.org_user = m.org_user AND ch.repo = m.repo
ORDER BY ch.timestamp
```

Dependabot:

```sql
SELECT
    timestamp,
    org_user || '/' || repo AS repository,
    dependencies
FROM dependabot_snapshots
ORDER BY timestamp
```

Dependabot alerts:

```sql
SELECT
    timestamp,
    org_user || '/' || repo AS repository,
    critical,
    high,
    medium,
    low
FROM dependabot_alerts
ORDER BY timestamp
```

Code scanning alerts:

```sql
SELECT
    csa.timestamp,
    csa.org_user || '/' || csa.repo AS repository,
    CASE
        WHEN csa.branch = m.main_branch THEN 'main'
        WHEN csa.branch = m.dev_branch THEN 'develop'
    END AS cnclbrnch,
    csa.critical,
    csa.high,
    csa.medium,
    csa.low
FROM code_scanning_alerts csa
JOIN repo_metadata m ON csa.org_user = m.org_user AND csa.repo = m.repo
ORDER BY csa.timestamp
```

Trivy alerts:

```sql
SELECT
    t.timestamp,
    t.org_user || '/' || t.repo AS repository,
    CASE
        WHEN t.branch = m.main_branch THEN 'main'
        WHEN t.branch = m.dev_branch THEN 'develop'
    END AS cnclbrnch,
    t.critical,
    t.high,
    t.medium,
    t.low
FROM trivy_scans t
JOIN repo_metadata m ON t.org_user = m.org_user AND t.repo = m.repo
ORDER BY t.timestamp
```
