# ci-pipeline.md

A production‑grade CI workflow for this repo that runs lint, tests, coverage, and artifacts across a Python version **matrix** with smart **caching**.
**Outcome:** Fast, deterministic PR checks that block merges until quality gates pass.

**When to use / When not to use**

* Use on every `push` and `pull_request` to `main` and feature branches.
* Don’t use for deploys (create a separate `deploy-*.md`), or for local ad‑hoc runs (use `pytest` locally).

---

## Ask AI Preamble

**Ask AI:** You may assume access to `git`, GitHub Actions, YAML editing, Python (3.10–3.12), and repo tools (`pytest`, `black`, `ruff`). Use file I/O tags (`<read_file>`, `<search_files>`) and approval prompts. Always pause before overwriting existing workflow files or required‑status settings. Prefer **dry‑runs**, add **caching**, and keep everything **idempotent**. Ask for approval before adding branch protection notes.

---

## Preconditions & Safety

* [ ] Repo has `.git` and GitHub origin.
* [ ] Tests live under `tests/` and run via `pytest`.
* [ ] Dependencies pinned in `requirements.txt` (and optionally `requirements-dev.txt`).
* [ ] No secrets committed to the repo; use **GitHub Secrets** only.
* [ ] Workflows run on ephemeral VMs; treat filesystem as non‑persistent between jobs.

**Safety Rules**

* Use built‑in `setup-python` caching (`cache: 'pip'`) and include a manual cache with `hashFiles()` fallback.
* Gate destructive steps behind approvals.
* Concurrency: cancel in‑flight older runs for the same branch to reduce CI spend.

---

## Inputs & Variables

**Required**

* `{{PY_MATRIX}}` — Python versions to test (default: `["3.10","3.11","3.12"]`)
* `{{REQ_FILE}}` — path to runtime requirements (default: `requirements.txt`)

**Optional**

* `{{REQ_DEV_FILE}}` — dev requirements (default: `requirements-dev.txt` if present)
* `{{CI_NAME}}` — workflow file name (default: `ci.yml`)
* `{{LINT_PATHS}}` — paths to lint (default: `"."`)
* `{{TEST_FLAGS}}` — extra pytest flags (default: `-q --maxfail=1`)
* `{{COVERAGE}}` — enable coverage (default: `true`)

```xml
<ask_followup_question>
  <question>Confirm CI config: PY_MATRIX={{PY_MATRIX}}, REQ_FILE={{REQ_FILE}}, REQ_DEV_FILE={{REQ_DEV_FILE}}, LINT_PATHS={{LINT_PATHS}}, COVERAGE={{COVERAGE}}. Proceed to write/update .github/workflows/{{CI_NAME}}?</question>
  <options>["Yes, proceed","Customize first","Cancel"]</options>
</ask_followup_question>
```

---

## Tooling Inventory

* `<read_file>` / `<search_files>` to detect existing workflows and requirements.
* `@terminal` for local lint/test dry‑runs (optional).
* GitHub Actions building blocks:

  * `actions/checkout@v4`, `actions/setup-python@v5`
  * `actions/cache@v4`, `actions/upload-artifact@v4`
* Python tools: `pip`, `pytest`, `coverage.py` (optional), `black`, `ruff`.

---

## High‑Level Flow

1. Detect existing workflow; prompt before overwrite.
2. Write a **matrix** GitHub Actions workflow (3.10–3.12).
3. Enable **pip caching** (built‑in + fallback `actions/cache`).
4. Lint (`black --check`, `ruff check`) then test (`pytest`) with coverage.
5. Upload **artifacts** (coverage XML/HTML, junit) on success/failure.
6. Add **concurrency** and **fail‑fast** strategy.
7. (Optional) Note branch protection rules to require CI before merge.
8. Provide **local validation** commands and commit/push gate.

---

## Step‑by‑Step Procedure (Executable)

### 1) Inspect Existing CI

```xml
<search_files>
  <pattern>.github/workflows/.*\.yml|\.yaml</pattern>
  <paths>[".github/workflows"]</paths>
</search_files>
```

```xml
<ask_followup_question>
  <question>Found existing workflow(s). Overwrite or create {{CI_NAME}} alongside?</question>
  <options>["Create/Update {{CI_NAME}} safely","Stop"]</options>
</ask_followup_question>
```

---

### 2) Author the Workflow (matrix + caching)

```bash
mkdir -p .github/workflows
cat > .github/workflows/{{CI_NAME}} <<'EOF'
name: CI

on:
  pull_request:
  push:
    branches: [ "main", "**" ]

# Cancel superseded runs per-branch to save minutes
concurrency:
  group: ci-${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-and-test:
    name: Lint & Test (py${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: {{PY_MATRIX}}
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
          cache-dependency-path: |
            {{REQ_FILE}}
            requirements-dev.txt

      # Fallback cache: compiled wheels / venv site-packages (optional, safe)
      - name: Prepare pip cache dir
        id: pip-cache
        run: echo "PIP_CACHE_DIR=$(python -c 'import site,os;print(os.getenv(\"PIP_CACHE_DIR\",\"~/.cache/pip\"))')" >> $GITHUB_OUTPUT

      - name: Cache pip (fallback)
        uses: actions/cache@v4
        with:
          path: |
            ~/.cache/pip
          key: pip-${{ runner.os }}-${{ matrix.python-version }}-${{ hashFiles('{{REQ_FILE}}','requirements-dev.txt') }}
          restore-keys: |
            pip-${{ runner.os }}-${{ matrix.python-version }}-

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r {{REQ_FILE}}
          if [ -f "{{REQ_DEV_FILE}}" ]; then pip install -r {{REQ_DEV_FILE}}; fi
          # Ensure core tools exist even if not in requirements
          pip install --upgrade pytest black ruff coverage

      - name: Lint (black, ruff)
        run: |
          black --version
          ruff --version
          black --check {{LINT_PATHS}}
          ruff check {{LINT_PATHS}}

      - name: Run tests
        env:
          PYTHONWARNINGS: default
        run: |
          if [ "${{ '{{' }} inputs.coverage {{ '}}' }}" = "true" ] || [ "{{COVERAGE}}" = "true" ]; then
            coverage run -m pytest {{TEST_FLAGS}} || EXIT=$?
            coverage xml -o coverage.xml || true
            coverage html -d coverage_html || true
            exit ${EXIT:-0}
          else
            pytest {{TEST_FLAGS}}
          fi

      - name: Upload artifacts (coverage, junit, logs)
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ci-artifacts-py${{ matrix.python-version }}
          path: |
            coverage.xml
            coverage_html/
            .pytest_cache/
            junit.xml
          if-no-files-found: ignore
EOF
```

---

### 3) (Optional) Add a Separate Lint‑Only Job (quick fail)

```bash
cat >> .github/workflows/{{CI_NAME}} <<'EOF'

  lint-only:
    name: Lint Only (fast)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: 'pip'
          cache-dependency-path: {{REQ_FILE}}
      - name: Install lint deps
        run: |
          python -m pip install --upgrade pip
          pip install black ruff
      - name: Lint
        run: |
          black --check {{LINT_PATHS}}
          ruff check {{LINT_PATHS}}
EOF
```

---

### 4) Local Dry‑Run (optional but recommended)

```bash
# Ensure tools available locally
python -m pip install --upgrade pip
pip install -r {{REQ_FILE}} || true
[ -f "{{REQ_DEV_FILE}}" ] && pip install -r {{REQ_DEV_FILE}} || true
pip install black ruff pytest coverage

# Local checks
black --check {{LINT_PATHS}}
ruff check {{LINT_PATHS}}
coverage run -m pytest {{TEST_FLAGS}} ; coverage report -m || true
```

```xml
<ask_followup_question>
  <question>Local checks look OK. Commit and push the new/updated workflow?</question>
  <options>["Yes, commit & push","No, stop here"]</options>
</ask_followup_question>
```

```bash
git add .github/workflows/{{CI_NAME}}
git commit -m "ci: matrix (3.10–3.12), pip caching, lint, tests, coverage, artifacts"
git push origin HEAD
```

---

## Branching & Decisions

* **Matrix versions:** Default `["3.10","3.11","3.12"]`. Trim if dependency constraints require it.
* **Coverage on/off:** Controlled by `{{COVERAGE}}`. If off, skip `coverage` steps.
* **Dev requirements:** Install `{{REQ_DEV_FILE}}` only if present.
* **Fail‑fast:** Disabled in matrix to see all breakages; enable by toggling `strategy.fail-fast: true` if desired.
* **Separate lint job:** Optional; keeps a fast signal for style.

---

## Failure Handling & Recovery

* **Dependency resolution fails**

  * Retry with `pip install --no-cache-dir -r {{REQ_FILE}}`.
  * Pin/adjust conflicting versions; regenerate `requirements.txt`.
* **Lint failures**

  * Run `black .` locally to auto‑format; fix `ruff` issues with `ruff --fix` where safe.
* **Test failures**

  * Inspect artifacts: `coverage.xml`, `coverage_html/`, and `.pytest_cache/`.
  * Reproduce locally with same Python version shown in job name.
* **Cache misses / stale cache**

  * Cache keys are tied to `hashFiles('{{REQ_FILE}}','requirements-dev.txt')`. Update keys if lockfiles change.
* **Long install times**

  * Consider building wheels in a dedicated job and caching `~/.cache/pip`.
* **Intermittent flakiness**

  * Mark tests with `@pytest.mark.flaky` + retries (plugin) or rerun jobs; investigate root cause.

---

## Verification & Exit Criteria

* CI triggers on `push` and `pull_request`.
* All matrix entries complete; status reported back to PR.
* Artifacts present on failures (logs/coverage).
* Lint and test steps are **required checks** before merge (configure in branch protection).

---

## Artifacts & Reporting

* `coverage.xml` (for Codecov/Sonar if later integrated)
* `coverage_html/` (human‑readable)
* `.pytest_cache/` and optional `junit.xml` (if you enable `--junitxml=junit.xml`)
* GitHub PR checks summary with per‑Python results

---

## Memory Bank & Documentation Updates

```xml
<ask_followup_question>
  <question>Update docs to include CI badges and “How to run tests locally” in README?</question>
  <options>["Yes, update README","Skip"]</options>
</ask_followup_question>
```

If “Yes”, add:

```bash
# Example badge (after first run)
echo '\n![CI](https://github.com/${GITHUB_REPOSITORY}/actions/workflows/{{CI_NAME}}/badge.svg)\n' >> README.md
git add README.md && git commit -m "docs: add CI badge and local test instructions" && git push
```

---

## Cleanup

* No long‑running resources in CI. Ensure artifacts are small; HTML coverage can be large—keep, but consider retention policies.

---

## Appendix

### Parameter Table

| Name           | Type       | Default                         | Required |
| -------------- | ---------- | ------------------------------- | -------- |
| PY\_MATRIX     | json array | `["3.10","3.11","3.12"]`        | ✅        |
| REQ\_FILE      | string     | `requirements.txt`              | ✅        |
| REQ\_DEV\_FILE | string     | `requirements-dev.txt` (if any) | ⬜        |
| CI\_NAME       | string     | `ci.yml`                        | ⬜        |
| LINT\_PATHS    | string     | `.`                             | ⬜        |
| TEST\_FLAGS    | string     | `-q --maxfail=1`                | ⬜        |
| COVERAGE       | boolean    | `true`                          | ⬜        |

### Notes & Tips

* **Caching:** `setup-python@v5` with `cache: 'pip'` is usually enough. The fallback `actions/cache` keeps resilience when lockfiles aren’t detected.
* **Parallelization:** Keep a single job with a matrix to simplify; add separate `lint-only` for quick feedback.
* **Artifacts Retention:** Configure repo settings if you want shorter retention to save space.
* **Coverage Gates:** You can fail builds on low coverage via `coverage report --fail-under=NN`.

---

### (Optional) JUnit & Coverage Flags

Add to `pytest.ini` to automatically emit artifacts:

```bash
cat > pytest.ini <<'PY'
[pytest]
addopts = --junitxml=junit.xml
PY
```

---

### (Optional) Branch Protection Reminder

Require the following checks **before merging** into `main`:

* `Lint & Test (py3.10)`
* `Lint & Test (py3.11)`
* `Lint & Test (py3.12)`
* (Optional) `Lint Only (fast)`
