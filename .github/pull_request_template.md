## Description

<!-- Summary of the changes and the motivation behind them -->

## Related Issue

<!-- e.g. Closes #123 -->

## Surface

<!-- Tick all that apply -->

- [ ] Public API (`kotobase.api`)
- [ ] Database Build (`kotobase.db.build`)
- [ ] Database Access (`UoW / Connection / Repos / ...`)
- [ ] CLI (`kotobase.cli / kotobase.terminal_output`)
- [ ] Documentation
- [ ] CI / tooling

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Improvement / refactor
- [ ] Documentation
- [ ] Breaking change

## Checklist

- [ ] I have read the [`Contributing Guide`](https://svdc1.github.io/mirumoji/docs/Contributing)
- [ ] My changes don't break existing functionality
- [ ] I added or updated tests where it makes sense

### Quality Gates

<!-- Run the gates relevant to the surfaces you touched -->

- [ ] Python &rarr; `ruff check kotobase/src` and `ruff format --check kotobase/src`
- [ ] Python &rarr; `cd kotobase && mypy src`
- [ ] Python &rarr; `cd kotobase && pytest`

## Additional Context

<!-- Screenshots, notes, or anything else reviewers should know -->
