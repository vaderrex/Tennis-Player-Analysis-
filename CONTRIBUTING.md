# Contributing to Tennis Rankings Explorer

Thank you for helping make this repository ready for team development.

## Getting Started

1. Clone the repository:

```powershell
git clone <repo-url>
cd Tennis
```

2. Copy environment variables:

```powershell
copy .env.example .env
```

3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
pip install -r requirements.txt
```

## Branching

Use focused branch names for work streams:

- `feature/<feature-name>`
- `bugfix/<bug-description>`
- `chore/<task-name>`

## Commit Messages

Keep commit messages concise and meaningful.

Example:

```text
Add MongoDB staging support for raw API snapshots
```

## Testing

Run the integration/test suite locally before opening a pull request:

```powershell
python test_ingestion_pipeline.py
```

The GitHub Actions workflow also runs tests automatically on push and pull requests.

## Pull Requests

- Base your PR on the latest `main` branch.
- Include a short description of what changed and why.
- Reference any relevant issues or tasks.

## Environment

Do not commit the `.env` file. Use `.env.example` as the source of truth for required local settings.

## Notes for Reviewers

- Verify that the branch is up to date with `main`.
- Confirm that tests were run locally or by CI.
- Check for clear documentation of new functionality.
