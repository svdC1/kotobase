# Contributing

## Welcome!

First off, thank you for considering contributing to `kotobase` !

This section outlines the different ways you can contribute to the `kotobase` project

## Setting Up A Development Environment

???+ abstract "Pre-Requisites"
    - [`Python>=3.10`](https://www.python.org/downloads/)
    - [`Git`](https://git-scm.com/install/)

### Clone Repository

Clone The `kotobase` Repo

```bash
git clone https://github.com/svdC1/kotobase.git
```

### Open In Your Code Editor

```bash
# VSCode Example
code kotobase
```

### Create A Virtual Environment

Create a virtual environment to isolate dependencies from your system's `Python` installation

```bash
python -m venv .venv  # Create Env In The `.venv` Directory
source .venv/bin/activate # Activate The Environment (Linux)
```

### Install The Package In Editable Mode

Install the `kotobase` package in editable mode with pip so that code changes take place immediately

```bash
# In Repo Root
pip install -e "./kotobase[dev]"
```

### Install Pre-Commit Hooks (Optional)

You can optionally install the repo's `Pre-Commit Hooks` *(scripts that detect errors or formatting issues and abort the `git commit` command before they enter versioning)*
```bash
pre-commit install
```

## Useful Commands

=== "Formatting + Linting With Ruff"
    ``` bash
    ruff check src/
    ruff check src/ --fix
    ruff format src/ --check
    ruff format src/
    ```

=== "Type-Checking With MyPy"
    ```bash
    mypy src/
    ```

=== "Preview The Documentation Site"
    ```bash
    cd docs-site
    mkdocs serve
    ```

=== "Sync Metadata"
    ```bash
    # Syncs (.github/README.md -> kotobase/README.md)
    # Syncs (LICENSE -> kotobase/LICENSE)
    python scripts/sync_meta.py
    ```

### Repository

=== "Creating a Pull Request"

    - Clone + Fork Repo Locally
    ```bash
    gh repo fork owner/repo --clone
    ```

    - Create New Branch
    ```bash
    git checkout -b <BRANCH_NAME>
    ```
    - Commit New Changes

    - Open A Pull Request According To The [`Pull Request Template`](https://github.com/svdC1/kotobase/blob/main/.github/pull_request_template.md)

=== "Opening an Issue"

    - Go To The Repo's  [`Issues Page`](https://github.com/svdC1/kotobase/issues)
    - Click on `New Issue`
    - Choose A Pre-Made Template ([`Bug Issue Template`](https://github.com/svdC1/kotobase/blob/main/.github/ISSUE_TEMPLATE/bug_report.yml) / [`Feature Request Template`](https://github.com/svdC1/kotobase/blob/main/.github/ISSUE_TEMPLATE/feature_request.yml)) Or Open A New Blank Issue
    - Edit Template / Blank Issue With Required Information

## Rules

=== "Purpose of Guidelines"

    Following these guidelines helps to communicate that you respect the time of the developers managing and developing this open source project. In return, they should reciprocate that respect in addressing your issue, assessing changes, and helping you finalize your pull requests

=== "Follow The Code of Conduct"

    When submitting contributions, please adhere to the [`Code of Conduct`](https://github.com/svdC1/kotobase/blob/main/.github/CODE_OF_CONDUCT.md)

    ???+ info "Responsibilities"
        - Create issues for any major changes and enhancements that you wish to make. Discuss things transparently and get community feedback
        - Follow provided issue templates when submitting
        - Keep feature versions as small as possible, preferably one new feature per version
        - Be welcoming to newcomers and encourage diverse new contributors from all backgrounds. See the [`Python Community Code of Conduct`](https://www.python.org/psf/codeofconduct/)
