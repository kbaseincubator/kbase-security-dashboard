## Org / repo joining

The queries combine org_user and repo into a single "repository" column using:

```sql
org_user || '/' || repo AS repository
```

This allows cross-filtering to work on both org and repo with a single click.

## Security Issues Columns

The main table includes two security columns that aggregate data from multiple sources:

- `sec_crit`: Sum of critical severity issues from:
    - Dependabot alerts (repo-wide)
    - Code Scanning alerts (branch-specific)
    - Trivy container scans (branch-specific)

- `sec_high`: Sum of high severity issues from the same three sources

**Note:** Dependabot alerts are repo-wide and appear in both main and develop branch rows.

## Dashboard Layout

* Column 1
    * Text:
        ```
        * Note that 0 may mean "no issues" or "check isn't working"
        * Graphs are not meaningful until a repo is selected in the main table
        ```
        * E.g. for dependabot PRs or security alerts
    * Main table
        * No branch column
            * Could add a "real branch" column, YAGNI
        * Color coding
            * Coverage
                * Green for > 80
                * Red for =< 80
            * Red for dependencies, sec_crit
            * Yellow for sec_high
* Column 2
    * Test result table (multiple branches)
    * Coverage scatter plot
        * branch as dimension
    * Dependabot updates line chart
* Column 3
    * Dependabot alerts line chart
    * Code scanning alerts line chart
    * Trivy alerts line chart
    * For all 3 charts:
        * Metrics are renamed to Critical, High, Medium, Low
            * See JSON color configuration below

## Dashboard General Configuration

* Dashboard has a native single select filter on cnclbrnch that
    * requires a value
    * has a default of main
    * applies to the main table and the code and trivy alerts tables
* Dimension labels were sorted via category name ascending
* For all line charts and scatter plots, values were averaged over each day

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
