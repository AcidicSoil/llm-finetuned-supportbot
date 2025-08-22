---
root: true
targets: ["*"]
description: "Project overview and general development guidelines"
globs: ["**/*"]
---

# Project Overview (Python)

## General Guidelines

- Use **Python 3.11+** for all new code.
- Follow **PEP 8** naming conventions:
  - `snake_case` for functions and variables
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
- Write self-documenting code with clear names and **PEP 257** docstrings.
- Prefer **composition over inheritance** to reduce tight coupling.
- Add meaningful comments for complex business logic (focus on the *why*, not the obvious *what*).
- Use **type hints (PEP 484)** and keep them accurate.

## Code Style

- Use **4 spaces** for indentation; never tabs.
- **No semicolons**; one statement per line.
- Use **double quotes** for strings by default and triple double quotes for docstrings.
- Include **trailing commas** in multi-line lists, dicts, tuples, and argument lists to keep diffs small.
- Keep lines to **max 88 chars** (Black default).
- Prefer **f-strings** for string formatting.
- Order imports as: standard library, third-party, local; avoid wildcard imports.

> Recommended tooling: **Black** (format), **Ruff** (lint/imports), **mypy/pyright** (types).

## Architecture Principles

- **Organize by feature/domain**, not by file type; keep related modules close together within a package.
- Use **dependency injection** via constructor or function parameters; depend on **protocols/ABCs** instead of concrete implementations where practical.
- Implement proper error handling: raise and catch **specific exceptions**, and **log** at integration boundaries.
- Follow the **Single Responsibility Principle**: keep modules and classes small, cohesive, and testable.
