# PR Review Checklist

- [ ] CI green (lint, format, tests)
- [ ] pre-commit run -a is clean
- [ ] Rebased on latest `main`
- [ ] Scope limited to title/description
- [ ] README/docs updated (if applicable)
- [ ] Tests added/updated; names are descriptive
- [ ] Backward-compat verified or migration noted

Reviewer focus:
- Correctness and clarity over style (formatter handles style)
- Edge cases covered in tests
- Docs/examples match flags/config
