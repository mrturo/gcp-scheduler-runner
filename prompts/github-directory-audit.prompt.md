Act as a senior GitHub repository reviewer. Your task is to audit the `.github/` directory and validate that its files follow relevant standards and best practices. Explicitly EXCLUDE anything inside `.github/workflows/**` (do not open it, do not analyze it, do not mention it).

Scope:
- Include all files under `.github/**` except `.github/workflows/**`.
- If standard files are missing, report them as findings.

What to review (as applicable to the repo):
1) Structure and conventions
- Consistent naming, no duplicates, correct locations.
- Proper use of `.md`/`.yml`/`.yaml`/`.json`.
- No obsolete or redundant files.

2) Templates and community
- `ISSUE_TEMPLATE/**` (YAML forms or templates): required fields, clear instructions, labels/assignees when appropriate, links to documentation, consistent language, no generic placeholder text.
- `PULL_REQUEST_TEMPLATE.md`: actionable checklist, sections for context, changes, testing, breaking changes, issue links, acceptance criteria.
- `DISCUSSION_TEMPLATE/**` if present: clarity and moderation guidance.
- `FUNDING.yml` if applicable: correct format and providers.

3) Ownership and maintainability
- `CODEOWNERS`: valid paths, correct syntax, existing user/team if you can infer it, correct rule ordering, reasonable coverage of critical areas, avoid overly broad rules.
- `dependabot.yml` if located under `.github/`: correct format, reasonable frequency, limits, labels, grouping if applicable, appropriate ecosystems (do not dive into workflows).

4) Security and policies
- `SECURITY.md`: reporting process, SLA/expectations, channels, supported versions.
- `SUPPORT.md`: support channels and expectations.
- `CODE_OF_CONDUCT.md`: proper reference and contact.
- `CONTRIBUTING.md` if inside `.github/`: coherent contribution guidance.
- `release.yml`/`release-drafter.yml` if present: consistent categories and labels (no workflows).

5) GitHub configuration
- Files like `.github/settings.yml` (if using probot/settings): alignment with repo policies, restrictions, branches, squash/rebase, etc.
- Bot configs (e.g., stale.yml, labeler.yml) under `.github/`: syntax, sensible rules, avoid overly aggressive settings.

Output rules:
A) Provide a report table with columns:
- File
- Status (OK / Warning / Fail / Missing)
- Finding
- Concrete recommendation

B) For each Fail/Warning, propose an exact change:
- If it is an existing file: provide a unified diff (```diff ... ```).
- If a file is missing: provide the full proposed content (```<ext> ... ```), with minimal placeholders.

C) Do not invent repo structure: base the analysis only on what you see in `.github/` (excluding `.github/workflows/**`).
D) Keep language consistent (use English).
E) Do not suggest changes to CI/CD or workflows (out of scope).
F) Prioritize standards: clarity, maintainability, security, low noise, and explicit policies.

First, list the file tree you are analyzing within `.github/` excluding `.github/workflows/**`. Then run the audit and deliver the report and diffs.
