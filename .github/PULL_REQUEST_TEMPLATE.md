## Problem and resulting behaviour

Describe the concrete problem, the fix and any change callers must account for.

## Validation

List the checks actually run and their results, including new regression cases.
Do not claim complete coverage unless it has been measured.

- [ ] Tests: `python -m pytest tests`
- [ ] Lint: `python -m flake8 pbdp tests`
- [ ] Documentation: `python -m sphinx -b html docs docs/_build/html -W`
- [ ] Package: `python -m build`
- [ ] Relevant changes recorded in [CHANGELOG.md](../CHANGELOG.md)

## Limitations

Record remaining format, platform or scientific assumptions relevant to this change.
