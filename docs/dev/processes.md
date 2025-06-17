# Project Processes & Automation Reference (2025)

This document is the **single source of truth** for all project workflows, automation, CI/CD, and manual steps.  
It defines how features, tasks, documentation, and releases are processed—by both humans and automation.

---

## 1. Process Naming and Aliases

| Canonical Name      | Aliases                                 | Purpose                                  |
|---------------------|-----------------------------------------|------------------------------------------|
| @dev-cycle          | dev, develop, feature-dev, full-cycle   | Full feature/task lifecycle              |
| @refine-doc         | doc-feature, refine-documentation       | Documentation update/refinement          |
| @refine-features    | refine, refine-all, feature-refine      | Review and improve all features          |
| @push-to-git        | push, git-push, publish                 | Safe code push with checks               |
| @code-review        | review, pr-review                       | Code review and approval                 |
| @full-cycle         | full, complete-cycle                    | Analyze, implement, test, doc, refine    |

---

## 2. Process Definitions

### @dev-cycle

**Purpose:**  
End-to-end lifecycle for a feature or task.

**Steps:**
1. Analyze requirements and update refinement log.
2. Design models, schemas, and endpoints.
3. Implement code and tests.
4. Update documentation.
5. Run all tests and linting.
6. Mark as complete in refinement log.

**Error Handling:**  
- If any step fails, stop and notify the developer.  
- Log errors and suggest fixes.

**Documentation Sync:**  
- Always update docs with code changes.

---

### @refine-doc

**Purpose:**  
Update, enhance, or synchronize documentation.

**Steps:**
1. Identify affected docs.
2. Update content, add examples, and clarify usage.
3. Check for missing or outdated sections.
4. Run spellcheck/lint on docs.
5. Commit and push changes.

**Error Handling:**  
- If doc build or lint fails, stop and fix before merge.

**Documentation Sync:**  
- Always update docs when code or processes change.

---

### @refine-features

**Purpose:**  
Review and improve all features for completeness, consistency, and best practices.

**Steps:**
1. Review all features in the refinement log and TODOs.
2. Refine code, tests, and docs as needed.
3. Mark status and update logs.

**Error Handling:**  
- If issues found, log and address before marking complete.

---

### @push-to-git

**Purpose:**  
Safely push code to the repository.

**Steps:**
1. Run linting on all code (`flake8`, `black`, or project standard).
2. Run all tests (unit, integration).
3. Ensure documentation is up to date.
4. Check for uncommitted changes (`git status`).
5. If all pass, commit and push.
6. If any step fails, stop and notify the developer.

**Error Handling:**  
- On failure, log error and do not push.

**Documentation Sync:**  
- Docs must be updated before push if code changes affect usage, API, or processes.

---

### @code-review

**Purpose:**  
Ensure code quality and correctness before merge.

**Steps:**
1. Reviewer checks code for style, logic, and security.
2. Reviewer checks tests and documentation.
3. Reviewer leaves comments or approves.
4. If changes are requested, developer addresses them and resubmits.
5. If approved, code is merged.

**Error Handling:**  
- If review fails, do not merge. Developer must address feedback.

**Documentation Sync:**  
- Reviewer checks that docs are updated for the change.

---

### @full-cycle

**Purpose:**  
Run the full lifecycle for a feature or task.

**Steps:**  
Same as @dev-cycle, but may be invoked for a batch of features/tasks.

---

## 3. Automation & CI/CD

- Use GitHub Actions for CI (test, lint, build, deploy).
- All pushes and PRs trigger tests and linting.
- Deployments are automated for the main branch.

---

## 4. Tracking Files

- `feature_refinement_log.md`: Track feature progress and refinement.
- `TODO.md`: Track outstanding dev tasks and enhancements.
- `description_and_roadmap.md`: Track architecture and roadmap.

---

## 5. Manual vs. Automated Steps

- Manual: Requirements analysis, code review, final approval.
- Automated: Linting, testing, doc checks, CI/CD, recursive processing.

---

## 6. Error Handling & Escalation

- On any process failure, log the error, notify the responsible party, and halt further steps.
- Escalate to project lead if blocking issues persist.

---

## 7. Documentation Sync Rules

- Documentation must be updated after any code, process, or workflow change.
- No feature or process is marked complete until docs are current.
- If a process changes, update this file and notify the team.

---

## 8. Aliases and Flexibility

- Similar process names (e.g., "doc-feature", "refine-documentation") are interpreted as their canonical process ("refine-doc").
- Contributors may use aliases for convenience.

---

## 9. Code Review Process

- Code review is mandatory before merge.
- Reviewer checks code, tests, and docs.
- Feedback must be addressed before approval.

---

## 10. Adding or Updating Processes

- Propose changes via PR to this file.
- Review and approval required before adoption.

---

**This file is the single source of truth for all project workflows. Always consult and update it as the project evolves.**
