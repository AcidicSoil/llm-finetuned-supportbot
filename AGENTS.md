# Repository Guidelines

This repo fine-tunes small LLMs on support-style data using Transformers, PEFT/LoRA, and BitsAndBytes. Follow these standards to keep contributions consistent, observable, and reproducible.

## Project Structure & Module Organization

- `src/`: core code (training, data, utils). Example: `src/training/finetune.py`, `src/data/prepare.py`.
- `tests/`: unit/integration tests (`test_*.py`).
- `eval/`: evaluation scripts → write outputs to `results/` (CSV/JSON).
- `results/`: evaluation artifacts, checkpoints, and summaries.
- `demo.py`: minimal CLI demo for local sanity checks.
- `taskmaster/`, `cursor/`: agent/tooling configs; not used at runtime.

Suggested package layout (create on demand):

```text
src/
  data/         # ingestion, schema, splits, validators
  training/     # HF Trainer/TRL, PEFT/LoRA, quantization
  eval/         # metrics, runners, table/report generation
  api/          # (optional) FastAPI demo
  utils/        # shared helpers (io, logging, seeding)
```

## Build, Test, and Development Commands

- Env: `python -m venv .venv && source .venv/bin/activate` (Windows: `.venv\Scripts\activate`).
- Install: `pip install -r requirements.txt` (install PyTorch separately per CUDA/CPU from pytorch.org).
- Demo: `python demo.py`.
- Tests: `pytest -q`.
- Module entry pattern: `python -m src.training.finetune --help`.

## Coding Style & Naming Conventions

- Python 3.11+; PEP 8/257; full type hints.
- 4 spaces; 88 cols; double quotes; f-strings; import order: stdlib → third-party → local.
- Prefer composition, small functions, and specific exceptions with helpful messages.
- Tools: Black (format) and Ruff (lint/imports) if configured.

## Testing Guidelines

- Pytest under `tests/` named `test_*.py` (mirror package paths where practical).
- Hermetic tests (seed RNG, stub I/O/network); test schemas, tokenization, and short training loops.
- Aim ≥80% coverage; store eval samples and golden outputs under `results/seeded/` when applicable.

## Commit & Pull Request Guidelines

- Conventional Commits, e.g., `feat(training): add LoRA scheduler` or `fix(eval): correct win-rate aggregation`.
- PRs include: description, linked issues, config/model changes, and eval snapshots in `results/` (CSV/JSON or logs/screenshots).
- Before PR: run tests, format/lint, confirm `demo.py` works, and update README tables if metrics changed.

## Taskmaster Workflow & Shorthand

Task tracking lives in `taskmaster/tasks/tasks.json` using the default tag `master`.

Shorthand notation

- IDs: `1` = top-level task; `1.3` = subtask 3 of task 1.
- Multi-select: comma-separated IDs, e.g., `1,2,5.1`.
- Status values: `pending`, `in-progress`, `done`, `review`, `cancelled`, `blocked`, `deferred`.
- Tags: separate contexts (default `master`).

Alias (optional)

- Bash/Zsh: add `alias tm="task-master"` to your shell rc and reload.
- PowerShell: `Set-Alias tm task-master` (persist via `$PROFILE`).

Common commands (use `--tag master` unless you’ve switched):

```bash
# Overview
tm list -s pending --with-subtasks --tag master
tm next --tag master
tm show 1,2,3 --tag master               # multiple IDs

# Progress
tm set-status -i 1 -s in-progress --tag master
tm update-subtask -i 1.2 -p "implemented loader" --tag master
tm set-status -i 1 -s done --tag master

# Editing & planning
tm update-task -i 1 -p "switch to 4-bit" --tag master
tm expand -i 3 -n 5 --tag master          # auto-breakdown
tm add-task -p "Document API demo" --priority medium --tag master
tm add-subtask -p 5 -t "Add argparse flags" --tag master
tm add-dependency -i 4 -d 3 --tag master

# Artifacts
tm generate -o taskmaster/tasks --tag master

# Tags
tm tags
tm add-tag new-exp --copy-from-current
tm use-tag new-exp
```

Recommended session flow

1) `tm list` → `tm next` to choose work.
2) `tm set-status -s in-progress` and implement.
3) Log notes with `tm update-subtask` as you progress.
4) `tm set-status -s done`; run `tm generate` to sync task files.

MCP tool equivalents (for integrated agents)

- List: `get_tasks`; Next: `next_task`; Show: `get_task`.
- Status: `set_task_status`; Update task: `update_task` (append or replace).
- Update subtask: `update_subtask`; Expand: `expand_task` / `expand_all`.
- Dependencies: `add_dependency`; Generate: `generate`.
- Tags: `list_tags`, `add_tag`, `use_tag`, `copy_tag`, `rename_tag`, `delete_tag`.

## Architecture Overview

- Data: schema (id, user_utterance, agent_response, metadata), cleaning, tokenization, splits.
- Training: configurable base model, LoRA/PEFT, quantization (4-bit), small GPU-friendly defaults.
- Evaluation: base vs tuned win-rate on 100 eval Qs, hallucination rubric, CSV/JSON outputs, README-ready tables.
- Demos: CLI Q&A via `demo.py`; optional FastAPI under `src/api/`.

## Security & Configuration Tips

- Copy `.env.example` → `.env`; set provider keys (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GOOGLE_API_KEY`, etc.). Never commit secrets.
- Prefer paths and model names via flags/env; no hardcoded credentials or absolute paths.
- BitsAndBytes works best with CUDA GPUs; provide CPU fallbacks or guards where feasible.

## Agent-Specific Instructions

- Prefer Taskmaster MCP tools (or `tm`) to keep task state accurate; always update status and notes.
- When adding non-trivial work, expand tasks or add subtasks so reviewers can follow the plan.
- After finishing a task, mark it `done` and run `tm generate` so markdown task files stay in sync.
