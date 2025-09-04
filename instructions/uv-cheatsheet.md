# uv Cheat Sheet — Venvs, Packages, Locking

This is a practical reference for using `uv` with virtual environments, packages, and reproducible installs across Linux/macOS/Windows/WSL.

## Install uv

- Linux/macOS: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`
- Verify: `uv --version`

## Virtual Environments

- Create venv in current directory: `uv venv` (creates `.venv`)
- Create with name/path: `uv venv .venv-dev`
- Create for a specific Python: `uv venv --python 3.11`
- Activate:
  - Linux/macOS/WSL: `source .venv/bin/activate`
  - Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
  - Windows cmd: `.venv\\Scripts\\activate.bat`
- Deactivate: `deactivate`

## Packages (pip-compatible interface)

- Install from requirements: `uv pip install -r requirements.txt`
- Install packages: `uv pip install ruff httpx`
- Uninstall: `uv pip uninstall <pkg>`
- List/Freeze/Tree: `uv pip list` | `uv pip freeze` | `uv pip tree`

## Reproducible Installs (lock + sync)

- Compile lock from input spec:
  - `uv pip compile requirements.in -o requirements.txt`
  - `uv pip compile pyproject.toml -o requirements.txt`
- Sync environment exactly to lock: `uv pip sync requirements.txt`
- Upgrades: `uv pip compile --upgrade` or `uv pip compile --upgrade-package <pkg>`

## Project Workflow (pyproject + uv.lock)

- Add/remove deps (writes `pyproject.toml` and updates `uv.lock`):
  - `uv add httpx`
  - `uv remove httpx`
  - Dev group: `uv add --group dev pytest`
- Sync environment from project metadata: `uv sync`
- Run commands in the project env (auto lock/sync if needed): `uv run pytest -q`

## Running Commands

- Project-coupled run: `uv run <cmd> [args...]`
- With ad‑hoc deps for a single run:
  `uv run --with httpx==0.26 python -c "import httpx;print(httpx.__version__)"`

## Tools (pipx-like)

- One-off tool execution: `uvx ruff --version`
- Install tool: `uv tool install ruff`
- Upgrade all tools: `uv tool upgrade --all`
- Update shell PATH shims: `uv tool update-shell`
- Rule of thumb: use `uv run` for project tools (e.g., `pytest`), `uvx` for global/isolated CLIs.

## Python Versions

- Install interpreters: `uv python install 3.11 3.12`
- Pin directory default: `uv python pin 3.11` (writes `.python-version`)
- Create venv with pinned version: `uv venv --python 3.11`

## Cache Controls

- Clean all caches: `uv cache clean`
- CI-friendly prune: `uv cache prune --ci`
- Force revalidate packages: `--refresh` or `--refresh-package <pkg>`
- Force reinstall: `--reinstall`

## System Installs and Containers

- Install into system environment: `uv pip install --system <pkg>`
- Docker hint: set `UV_SYSTEM_PYTHON=1` when intentionally targeting the system interpreter inside a container.

## Windows / WSL Tips

- WSL activation: `source .venv/bin/activate` (Linux-style path)
- Native Windows activation: `.venv\\Scripts\\Activate.ps1`
- If a repo is used from both WSL and Windows, prefer creating the venv within the environment you’ll actually run in (paths differ between `.venv/bin` and `.venv/Scripts`).

## Troubleshooting

- `pytest: command not found` → ensure installed: `uv add --group dev pytest` then `uv run pytest -q`.
- Permission/cache issues in CI → use `uv cache prune --ci` or set a writable `UV_CACHE_DIR`.
- Mixed Python versions → check `python -V`, `.python-version`, and recreate venv: `rm -rf .venv && uv venv`.

## Handy One-liners

- New project quickstart:
  `uv init && uv add fastapi[standard] && uv run uvicorn app:app --reload`
- Rebuild from lock:
  `uv pip sync requirements.txt`
- Export lock for interop (avoid keeping both long-term):
  `uv export --format requirements-txt > requirements.txt`

---
Sources: docs.astral.sh/uv (official documentation).
