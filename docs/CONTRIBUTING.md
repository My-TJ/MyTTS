# Contributing

## Commit convention

Use Conventional Commits:

- `feat:` new capabilities
- `fix:` bug fixes
- `refactor:` internal changes without behavior changes
- `docs:` documentation only
- `test:` test additions or fixes
- `chore:` tooling and maintenance

Examples:

```text
feat: add transcript export command
fix: preserve text across paragraph chunks
refactor: split CLI from document synthesis
docs: document source-file workflow
```

## Development workflow

1. Create a focused branch.
2. Make one logical change.
3. Run tests and syntax checks.
4. Commit with a Conventional Commit message.
5. Push the branch or open a merge request.

## Validation

```bash
python -m pip install -e .
python -m pytest
python -m compileall -q src tests
piper-studio --help
```
