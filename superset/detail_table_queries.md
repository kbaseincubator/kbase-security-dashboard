Test:

```
SELECT 
    timestamp,
    org_user AS org,
    repo,
    branch,
    CASE
        WHEN success THEN '✅ Pass'
        ELSE '❌ Fail'
    END AS status
FROM test_status
ORDER BY timestamp DESC
```

Coverage:

```
SELECT 
    timestamp,
    org_user AS org,
    repo,
    branch,
    coverage
FROM coverage_history
ORDER BY timestamp
```

Dependabot:

```
SELECT 
    timestamp,
    org_user AS org,
    repo,
    dependencies
FROM dependabot_snapshots
ORDER BY timestamp
```

CVEs:

```
SELECT 
    timestamp,
    org_user AS org,
    repo,
    critical,
    high,
    medium,
    low
FROM vulnerability_snapshots
ORDER BY timestamp
```
