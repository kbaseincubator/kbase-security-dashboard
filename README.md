# KBase security dashboard

**This is currently a prototype**

This is a small service to collect and store KBase repo security information in a database.

### Adding code

* While in rapid initial development, we'll be pushing directly to `main`
* Once the basic idea is working, we'll switch to an alpha / prototype stage, where
  we will PR (do not push directly) to `main`. In the future we will add a `develop` branch.
* The PR creator merges the PR and deletes branches (after builds / tests / linters complete).

### Code requirements for prototype code

* Any code committed must at least have a test file that imports it and runs a noop test so that
  the code is shown with no coverage in the coverage statistics. This will make it clear what
  code needs tests when we move beyond the prototype stage.
* Each module should have its own test file. Eventually these will be expanded into unit tests
  (or integration tests in the case of app.py)
* Any code committed must have regular code and user documentation so that future devs
  converting the code to production can understand it.
* Release notes are not strictly necessary while deploying to CI, but a concrete version (e.g.
  no `-dev*` or `-prototype*` suffix) will be required outside of that environment. On a case by
  case basis, add release notes and bump the prototype version (e.g. 0.1.0-prototype3 ->
  0.1.0-prototype4) for changes that should be documented.

### Running tests

```
uv sync --dev  # only the first time or when uv.lock changes
PYTHONPATH=. uv run pytest test
```

### Exit from prototype status

* Run through all code, refactor to production quality
* Add tests where missing (which is a lot) and inspect current tests for completeness and quality
  * E.g. don't assume existing tests are any good
