# Contributing to VyOS API (2025)

Thank you for your interest in contributing!

---

## How to Contribute
1. Fork the repository and create a feature branch.
2. Write clear, well-documented code and tests.
3. Update documentation in both `docs/user/` (user) and `docs/dev/` (developer) as needed.
4. Submit a pull request (PR) with a clear description of your changes.
5. Link your PR to any relevant issues.

## Code Review
- All PRs require at least one review.
- Address all review comments before merging.
- Use draft PRs for work-in-progress.

## Coding Standards
- Follow PEP8 for Python.
- Use type hints and docstrings.
- Write or update tests for all new features and bugfixes.
- Keep code and documentation in sync.

## Communication
- Use GitHub Issues for bugs, enhancements, and questions.
- Be respectful and constructive in all discussions.

## Development Workflow
- See [processes.md](processes.md) for full workflow and automation details.
- Track features and refinement in [feature_refinement_log.md](feature_refinement_log.md).

## Current Improvement Priorities (June 2025)
1. **Dependency Management**
   - Update requirements.txt to include all necessary packages with proper versions
   - Fix unresolved imports (particularly FastAPI and SQLAlchemy)
   - Implement a virtual environment setup script for consistent development environments

2. **Code Quality**
   - Fix HTML formatting issues in static files
   - Add code linting checks to CI pipeline
   - Update CSS to improve responsive design

3. **Documentation Enhancements**
   - Improve cross-referencing between related features
   - Create a comprehensive API reference with OpenAPI spec
   - Add more examples for common use cases

---

For user/operator documentation, see `docs/user/`. For developer docs, see this directory.
