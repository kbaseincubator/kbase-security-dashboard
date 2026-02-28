Test:

```
SELECT 
    timestamp,
    org_user || '/' || repo AS repository,
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
    org_user || '/' || repo AS repository,
    branch,
    coverage
FROM coverage_history
ORDER BY timestamp
```

Dependabot:

```
SELECT 
    timestamp,
    org_user || '/' || repo AS repository,
    dependencies
FROM dependabot_snapshots
ORDER BY timestamp
```

Dependabot alerts:

```
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

```
SELECT 
    timestamp,
    org_user || '/' || repo AS repository,
    branch,
    critical,
    high,
    medium,
    low
FROM code_scanning_alerts
ORDER BY timestamp
```

Trivy alerts:

```
SELECT 
    timestamp,
    org_user || '/' || repo AS repository,
    branch,
    critical,
    high,
    medium,
    low
FROM trivy_scans
ORDER BY timestamp
```
