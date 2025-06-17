# Developer Documentation (2025)

This section is for contributors and maintainers of the VyOS API project. It provides all the details needed to extend, maintain, and contribute to the project.

---

## Contents
- [How to Extend](how-to-extend.md): Add endpoints, models, and event logic
- [Processes](processes.md): Dev workflow, git, CI, code review, automation
- [Roadmap & Architecture](description_and_roadmap.md): Architecture, roadmap, design notes
- [TODO](TODO.md): Dev-focused TODOs, enhancement ideas
- [Feature Refinement Log](feature_refinement_log.md): Feature logs, refinement history
- [Contributing](CONTRIBUTING.md): Contribution guidelines

---

## Quick Start for Developers
1. Clone the repo and set up a virtual environment (see user installation guide).
2. Install dev dependencies:
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # if present
   ```
3. Run tests:
   ```bash
   pytest
   ```
4. Run the API locally:
   ```bash
   uvicorn main:app --reload
   ```
5. See [how-to-extend.md](how-to-extend.md) for adding features.

---

## Project Structure
- `main.py`: FastAPI entrypoint
- `models.py`: SQLAlchemy models
- `schemas.py`: Pydantic schemas
- `routers/`: All API endpoints
- `crud_*.py`: CRUD logic for each resource
- `utils_*.py`: Utility functions
- `tests/`: Unit and integration tests
- `docs/`: User and developer documentation

---

For more, see the files in this directory and the user docs for API usage.
