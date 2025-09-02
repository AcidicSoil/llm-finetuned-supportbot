# repo-setup.md

Set up the initial repository structure and reproducible development environment.
**Outcome:** clean repo scaffold, virtualenv created, dependencies pinned, smoke check for reproducibility.

**When to use:**

* Starting a new project from scratch.
* Resetting a broken or inconsistent environment.

**When not to use:**

* Adding new modules to an existing repo (use feature-specific workflows instead).
* Deploying to staging/prod (use deploy workflows).

---

## Ask AI Preamble

You may assume access to:

* `git`, `gh`, `python3`, `pip`, `venv`
* `bash` shell commands
* File I/O tags (`<read_file>`, `<search_files>`)
* Approval prompts (`<ask_followup_question>`)

Always pause for confirmation before destructive actions (e.g., deleting existing venv).

---

## Preconditions & Safety

* [ ] User has GitHub repo initialized (or empty directory).
* [ ] Python 3.10+ installed.
* [ ] GPU/compute optional (not needed for setup).
* [ ] Internet access for pip installs.

**Safety rules:**

* Never hardcode secrets in `requirements.txt`.
* Use pinned versions only.
* Dry-run commands (list dirs, preview files) before writing.

---

## Inputs & Variables

Required:

* `{{PROJECT_NAME}}` — root directory name.
* `{{PY_VERSION}}` — python version (default `3.10`).

Optional:

* `{{VENV_NAME}}` — name of virtualenv dir (default `.venv`).
* `{{REQ_FILE}}` — requirements file path (default `requirements.txt`).

```xml
<ask_followup_question>
  <question>Provide values for: {{PROJECT_NAME}}, optional: {{PY_VERSION}}, {{VENV_NAME}}, {{REQ_FILE}}. Defaults: python=3.10, venv=.venv, req=requirements.txt. Continue?</question>
  <options>["Continue with defaults","Customize values","Cancel"]</options>
</ask_followup_question>
```

---

## Tooling Inventory

* `<read_file>` / `<search_files>` for inspecting existing files.
* `@terminal` for running commands.
* Git: `git init`, `git add`, `git commit`.
* Python: `python -m venv`, `pip install -r`.

---

## High-Level Flow

1. Confirm project name and inputs.
2. Scaffold directory structure.
3. Initialize Git repo.
4. Create and activate virtualenv.
5. Install pinned dependencies.
6. Generate `requirements.txt`.
7. Verify reproducibility (clean reinstall smoke test).
8. Commit initial setup.

---

## Step-by-Step Procedure

### 1. Confirm Project Root

```bash
pwd
ls -a
```

```xml
<ask_followup_question>
  <question>We are about to scaffold {{PROJECT_NAME}} here. Continue?</question>
  <options>["Yes, continue","No, abort"]</options>
</ask_followup_question>
```

---

### 2. Scaffold Directories

```bash
mkdir -p {{PROJECT_NAME}}/{src,scripts,configs,eval,tests,api,results}
tree {{PROJECT_NAME}} -L 1
```

---

### 3. Initialize Git

```bash
cd {{PROJECT_NAME}}
git init
touch README.md
echo "# {{PROJECT_NAME}}" > README.md
git add README.md
git commit -m "chore: initial repo setup"
```

---

### 4. Create Virtualenv

```bash
python{{PY_VERSION}} -m venv {{VENV_NAME}}
source {{VENV_NAME}}/bin/activate
```

---

### 5. Install Core Dependencies

```bash
pip install --upgrade pip
pip install transformers==4.44.0 peft==0.7.0 bitsandbytes==0.43.0 \
            torch==2.2.2 datasets==2.20.0 fastapi==0.111.0 \
            uvicorn==0.30.0 pytest==8.2.0
```

---

### 6. Freeze Requirements

```bash
pip freeze > {{REQ_FILE}}
cat {{REQ_FILE}} | head -20
```

```xml
<ask_followup_question>
  <question>Dependencies pinned in {{REQ_FILE}}. Proceed to commit them?</question>
  <options>["Yes, commit","No, stop here"]</options>
</ask_followup_question>
```

```bash
git add {{REQ_FILE}}
git commit -m "chore: add pinned dependencies"
```

---

### 7. Smoke Test Reproducibility

```bash
deactivate
rm -rf {{VENV_NAME}}
python{{PY_VERSION}} -m venv {{VENV_NAME}}
source {{VENV_NAME}}/bin/activate
pip install -r {{REQ_FILE}}
```

```xml
<ask_followup_question>
  <question>Smoke test complete. Dependencies reinstalled cleanly? Proceed to final commit?</question>
  <options>["Yes, finalize","No, stop"]</options>
</ask_followup_question>
```

---

### 8. Commit Full Scaffold

```bash
git add src/ scripts/ configs/ eval/ tests/ api/ results/
git commit -m "chore: scaffold repo structure and env"
```

---

## Branching & Decisions

* Abort if `{{PROJECT_NAME}}` dir already exists (prevent overwrite).
* If smoke test fails, retry with smaller dependency set.
* If user cancels at any stage, exit cleanly.

---

## Failure Handling & Recovery

* **pip install fails:** re-run with `--no-cache-dir`.
* **venv broken:** delete and recreate.
* **git conflict:** stash or remove existing `.git`.

---

## Verification & Exit Criteria

* All directories created.
* Virtualenv active.
* `requirements.txt` pinned.
* Smoke reinstall successful.
* Initial commits exist.

---

## Artifacts & Reporting

* Repo scaffold with README.
* `requirements.txt` pinned.
* Initial commits in history.
* Log of commands run (terminal output).

---

## Memory Bank & Documentation Updates

```xml
<ask_followup_question>
  <question>Update memory-bank with: repo scaffolded, venv + deps pinned, smoke verified. Proceed?</question>
  <options>["Yes, update now","Skip"]</options>
</ask_followup_question>
```

---

## Cleanup

```bash
deactivate
echo "Repo setup complete for {{PROJECT_NAME}}"
```

---

## Appendix

**Parameters**

| Name          | Type | Default          | Required |
| ------------- | ---- | ---------------- | -------- |
| PROJECT\_NAME | str  | —                | ✅        |
| PY\_VERSION   | str  | 3.10             | ⬜        |
| VENV\_NAME    | str  | .venv            | ⬜        |
| REQ\_FILE     | str  | requirements.txt | ⬜        |

**Glossary**

* **venv**: Isolated Python environment.
* **pip freeze**: List installed packages + versions.
* **pinned deps**: Exact versions to ensure reproducibility.
* **smoke test**: Quick minimal check to validate reproducibility.
