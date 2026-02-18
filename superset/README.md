For tables using cross filtering instead of native filtering, replace the org_user and
repo columns in the select with

```
r.org_user || '/' || r.repo AS repository,
```

or

```
org_user || '/' || repo AS repository,
```

That allows users to click on a single cell and have the cross filter work on both org and repo.
For native filtering, added filters on org / repo / branch and scoped them to the detail
tables only.


Layout was:

* Column 1
    * Text noting that 0 in a cell could mean that the check isn't working
        * E.g. for dependabot or vulnerabilities
    * Main table
        * Has a native filter on branch
        * Color coding
            * Coverage
                * Green for > 80
                * Red for =< 80
            * Red for dependencies and critical vulns
            * Yellow for high vulns
* Column 2
    * Test result table
    * Coverage line chart
        * Dimension was branch for cross filtered version only
* Column 3
    * Security updates line chart
    * Vulnerabilities line chart
        * Updated legend names to match color info in JSON below
    
Labels were sorted via category name ascending
    
In the dashboard JSON added:

```
  "label_colors": {
    "Critical": "#DC3545",
    "High": "#FD7E14",
    "Medium": "#FFC107",
    "Low": "#28A745"
  },
```
