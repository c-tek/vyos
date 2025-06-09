# Database Migrations Guide: VyOS VM Network Automation API

## Table of Contents
1.  [Overview](#1-overview)
2.  [Setup and Configuration](#2-setup-and-configuration)
3.  [Generating Migrations](#3-generating-migrations)
4.  [Applying Migrations](#4-applying-migrations)
5.  [Reverting Migrations](#5-reverting-migrations)
6.  [Integration with Application Startup](#6-integration-with-application-startup)

---

## 1. Overview

The VyOS VM Network Automation API uses [Alembic](https://alembic.sqlalchemy.org/en/latest/) for managing database schema migrations. Alembic provides a robust and version-controlled way to evolve your database schema as your application changes, ensuring that schema updates are consistent and reproducible across different environments (development, testing, production).

Key benefits of using Alembic:
*   **Version Control:** Each schema change is recorded in a separate Python script, allowing you to track changes over time.
*   **Reproducibility:** Ensures that your database schema can be reliably created or updated to any specific version.
*   **Collaboration:** Facilitates schema changes in team environments by providing a structured workflow.

---

## 2. Setup and Configuration

Alembic is initialized and configured within the project.

### Installation
Alembic is listed as a dependency in `requirements.txt`. Ensure it's installed in your virtual environment:
```bash
pip install -r requirements.txt
```

### Initialization
Alembic was initialized in the project root using:
```bash
alembic init migrations
```
This command created:
*   `alembic.ini`: The main configuration file for Alembic.
*   `migrations/`: A directory containing migration scripts and the `env.py` environment configuration.

### Configuration Details
*   **`alembic.ini`**:
    *   `script_location = migrations`: Points to the directory where migration scripts are stored.
    *   `sqlalchemy.url`: Configured to use the SQLite database (`sqlite:///./vyos.db`). If you change your `DATABASE_URL` in `config.py` or your `.env` file, you should update this line in `alembic.ini` accordingly. For production, this should match your production database URL.

*   **`migrations/env.py`**:
    *   This file is crucial as it defines how Alembic connects to your database and how it discovers your SQLAlchemy models.
    *   `target_metadata = Base.metadata`: This line imports `Base` from `models.py` and sets `target_metadata` to `Base.metadata`. This allows Alembic's `autogenerate` feature to compare your current models with the database schema.
    *   The `run_migrations_online` function is configured to use a synchronous SQLAlchemy engine for Alembic's operations, even if your application uses an asynchronous engine.

---

## 3. Generating Migrations

When you make changes to your SQLAlchemy models (e.g., add a new table, add/remove columns, change column types), you need to generate a new migration script.

```bash
alembic revision --autogenerate -m "Descriptive message for your changes"
```
*   `--autogenerate`: This flag tells Alembic to automatically detect schema changes by comparing your `models.py` with the current database schema and generate the necessary `upgrade()` and `downgrade()` operations.
*   `-m "Descriptive message..."`: Provides a message for the migration script, which will be included in the filename and the script itself.

**Example:**
If you add a new column to an existing model in `models.py`, running the above command will create a new Python file in `migrations/versions/` with `upgrade()` and `downgrade()` functions that contain the DDL (Data Definition Language) statements for that column.

**Important:** Always review the generated migration script before applying it to ensure it accurately reflects your intended changes and doesn't contain any unexpected operations.

---

## 4. Applying Migrations

To apply pending migrations to your database, use the `upgrade` command.

```bash
alembic upgrade head
```
*   `head`: This tells Alembic to upgrade to the latest revision available in your `migrations/versions` directory.

You can also upgrade to a specific revision:
```bash
alembic upgrade <revision_id>
```
Replace `<revision_id>` with the unique identifier of the target migration.

---

## 5. Reverting Migrations

To revert applied migrations (e.g., to go back to a previous schema version), use the `downgrade` command.

```bash
alembic downgrade -1
```
*   `-1`: This reverts the last applied migration.

You can also downgrade to a specific revision:
```bash
alembic downgrade <revision_id>
```
Or revert all migrations:
```bash
alembic downgrade base
```

---

## 6. Integration with Application Startup

The `main.py` application is configured to automatically run Alembic migrations on startup. This ensures that the database schema is always up-to-date when the application starts.

See the `on_startup` event handler in [`main.py`](main.py) for details. It checks if the database is empty and performs an initial `alembic upgrade head` if necessary, or simply ensures the database is up-to-date if it already contains tables.

**Note:** While `main.py` handles automatic upgrades, you will still need to manually generate new migration scripts using `alembic revision --autogenerate -m "..."` whenever you modify your SQLAlchemy models.