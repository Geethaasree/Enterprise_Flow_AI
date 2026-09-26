# Hermes Git Workflow

This file defines how Hermes must use Git for the EnterpriseFlow AI project.

## 1. Important Safety Rules

- Never commit API keys, passwords, tokens, `.env` files, private certificates, or other secrets.
- Never use `git add .` blindly without first checking `git status` and reviewing the files that will be committed.
- Never force-push.
- Never rewrite Git history unless explicitly instructed by the user.
- Never push directly to `main`/`master` unless the repository workflow explicitly requires it.
- Before every commit, run the relevant tests for the current phase.
- Only commit work that belongs to the current phase.
- Do not commit broken or untested functionality.
- If GitHub authentication or push permission is unavailable, stop and report the issue. Do not attempt to bypass authentication.

## 2. Initial Repository Setup

Run these commands once if Git has not already been initialized:

```bash
git init
git branch -M main
git status
```

Configure the repository remote only if it has not already been configured:

```bash
git remote -v
```

If no remote exists, the user must provide/configure the GitHub remote. Do not invent a repository URL.

Example:

```bash
git remote add origin <https://github.com/Geethaasree/Enterprise_Flow_AI>
```

Verify:

```bash
git remote -v
```

## 3. Initial Specifications Commit

After the five files have been verified:

```bash
git status
git add specs/
git diff --cached
git commit -m "docs: add project specifications"
git push -u origin main
```

Do not push if the remote is not configured.

## 4. Before Every Phase

Before starting a new phase:

```bash
git status
git branch --show-current
git log --oneline -5
```

Confirm the working tree is in a known state.

## 5. After Completing a Phase

Hermes must complete the following sequence:

### Step 1 — Inspect changes

```bash
git status
git diff --stat
git diff
```

Review the changes and ensure that only intended files are included.

### Step 2 — Check for secrets

At minimum verify:

```bash
git status --short
```

Ensure that files such as these are NOT staged:

```text
.env
.env.*
*.pem
*.key
credentials.json
service-account.json
```

The `.env.example` file is allowed if it contains placeholders only.

### Step 3 — Run validation

Run the tests and checks required by the current phase.

For example:

```bash
pytest
```

and, when configured:

```bash
ruff check .
mypy .
```

For frontend phases, also run the appropriate:

```bash
npm test
npm run lint
npm run build
```

Only run commands that actually exist in the project.

### Step 4 — Stage intended changes

Prefer explicitly staging the intended project files.

```bash
git add <files>
```

If many files belong to the current phase, Hermes may use:

```bash
git add .
```

but ONLY after checking `git status` and confirming that no secrets or unrelated files are present.

### Step 5 — Review staged changes

```bash
git status
git diff --cached --stat
git diff --cached
```

Do not commit if unexpected files or secrets are present.

### Step 6 — Commit

Use a conventional commit message.

Examples:

```bash
git commit -m "feat: implement phase 1 foundation"
git commit -m "feat: integrate Grok provider"
git commit -m "feat: add LangGraph orchestration"
git commit -m "feat: add enterprise database models"
git commit -m "feat: add MCP tool layer"
git commit -m "feat: implement policy RAG"
git commit -m "feat: add specialist agents"
git commit -m "feat: add memory and context management"
git commit -m "feat: add human approval workflow"
git commit -m "feat: add enterprise API integration"
git commit -m "feat: add MLflow tracing and evaluation"
git commit -m "feat: add security and automated tests"
git commit -m "feat: add Next.js frontend"
git commit -m "feat: add Databricks integration path"
git commit -m "build: add production Docker configuration"
git commit -m "ci: add Coolify deployment pipeline"
git commit -m "docs: finalize production and interview package"
```

### Step 7 — Create phase tag

After the commit succeeds:

```bash
git tag phase-XX-<short-name>
```

Examples:

```bash
git tag phase-01-foundation
git tag phase-02-grok
git tag phase-03-langgraph
git tag phase-04-database
git tag phase-05-mcp
git tag phase-06-rag
git tag phase-07-agents
git tag phase-08-memory
git tag phase-09-approval
git tag phase-10-integrations
git tag phase-11-mlflow
git tag phase-12-security
git tag phase-13-frontend
git tag phase-14-databricks
git tag phase-15-production-docker
git tag phase-16-coolify
git tag phase-17-hardening
```

### Step 8 — Push commit and tag

```bash
git push origin <current-branch>
git push origin phase-XX-<short-name>
```

For example:

```bash
git push origin main
git push origin phase-01-foundation
```

## 6. Recommended Phase Branching

If the repository workflow uses feature branches, use:

```bash
git checkout -b phase-XX-<short-name>
```

Example:

```bash
git checkout -b phase-01-foundation
```

After implementation:

```bash
git add .
git commit -m "feat: implement phase 1 foundation"
git push -u origin phase-01-foundation
```

Do NOT merge branches automatically unless the user explicitly asks Hermes to do so.

If the user prefers a simple single-branch workflow, commits and tags may be made directly on `main`.

## 7. Never Force Push

Never run:

```bash
git push --force
git push -f
```

unless the user explicitly and knowingly requests it.

## 8. Handling Push Failures

If:

```bash
git push
```

fails because of authentication, permissions, remote configuration, branch protection, or another GitHub issue:

1. Do not modify Git history.
2. Do not delete commits.
3. Do not force-push.
4. Report the exact failure.
5. Tell the user what action is required.

Do not expose credentials in logs or responses.

## 9. Before Starting the Next Phase

After a successful phase push:

```bash
git status
git log --oneline -5
git tag --list | tail
```

The working tree should normally be clean:

```text
nothing to commit, working tree clean
```

Then the next phase can begin.

## 10. Hermes Phase Completion Report

At the end of every phase, report:

```text
Git status:
<clean/changes remaining>

Commit:
<commit hash>

Commit message:
<message>

Tag:
<tag>

Push:
<success/failure>

Branch:
<branch>

Tests:
<results>

Known issues:
<issues or none>
```

## 11. Critical Rule

Do not automatically push code simply because code was generated.

Push only after:

1. The current phase is implemented.
2. Tests pass.
3. Relevant lint/type checks pass.
4. Secrets have been checked.
5. Staged changes have been reviewed.
6. The commit succeeds.

Then push the commit and its phase tag.

## 12. Authentication

GitHub authentication must be configured outside this file.

Recommended approaches include:

- SSH authentication
- GitHub CLI authentication
- an existing credential manager

Do NOT put a GitHub token, password, SSH private key, or other credential into this file.

Verify authentication with the user's configured method before attempting the first push.

