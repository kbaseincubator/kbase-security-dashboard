## Main Table Query

The main table query combines org_user and repo into a single "repository" column using:

```sql
org_user || '/' || repo AS repository
```

This allows cross-filtering to work on both org and repo with a single click.

## Security Issues Columns

The main table includes two security columns that aggregate data from multiple sources:

- **`sec_crit`**: Sum of critical severity issues from:
  - Dependabot alerts (repo-wide)
  - Code Scanning alerts (branch-specific)
  - Trivy container scans (branch-specific)

- **`sec_high`**: Sum of high severity issues from the same three sources

**Note:** Dependabot alerts are repo-wide and appear in both main and develop branch rows.

## Dashboard Layout

* Column 1
    * Text noting that 0 in a cell could mean that the check isn't working
        * E.g. for dependabot PRs or security alerts
    * Main table
        * Has a native filter on branch
        * Color coding
            * Coverage
                * Green for > 80
                * Red for =< 80
            * Red for dependencies, sec_crit
            * Yellow for sec_high
* Column 2
    * Test result table
    * Coverage line chart
        * branch as dimension
* Column 3
    * Dependabot PRs line chart
    * Security issues line charts (separate charts for each source)

Labels were sorted via category name ascending

## Dashboard JSON Configuration

In the dashboard JSON, add:

```json
  "label_colors": {
    "Critical": "#DC3545",
    "High": "#FD7E14",
    "Medium": "#FFC107",
    "Low": "#28A745"
  }
```
