---
name: db-manager
description: Manage this project's local PostgreSQL database directly through the db-postgres Docker container and psql; use for inspecting, diagnosing, or applying explicit local data/schema changes without Alembic migrations.
---

# DB manager

Use this skill for local database work in this repository.

## Required connection workflow

- Read connection values from the project's `.env`; never hard-code credentials.
- Use the PostgreSQL container named `db-postgres` as the single database entrypoint.
- Enter the container with `docker exec -it db-postgres sh`, then run `psql` inside it.
- For non-interactive checks, the equivalent is `docker exec db-postgres sh -lc 'psql ...'`.
- Prefer the database name, user, and password from `.env` (`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`). If the configured container is not running, report that instead of switching to another database container.

## Safety and change policy

- Inspect the target rows, table schema, and constraints before changing anything.
- Do not create or run Alembic migrations for local data or schema corrections unless the user explicitly asks for a migration.
- Before an UPDATE, INSERT, DELETE, or DDL change, show or record the exact target and use a narrowly scoped SQL statement.
- Treat DELETE, DROP, TRUNCATE, and broad UPDATE statements as destructive: confirm the exact scope with a read query first and ask the user when the target is ambiguous.
- Keep SQL reproducible in the conversation or a project SQL file when the change should be repeatable; do not modify `.env` or expose secrets in output.
- After a change, query the affected rows again and report the result.

## Useful commands

Read `.env` only as needed to obtain values, keeping passwords out of displayed output. Then use commands shaped like:

```sh
docker exec -it db-postgres sh
psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

For a one-shot query, load the values without printing the password and run:

```sh
docker exec db-postgres sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -P pager=off -c "SELECT ..."'
```

If the variables are not present inside the container, pass only the required values from `.env` to `psql`; never include the password in user-facing logs or final responses.

For schema inspection, use `\\dt`, `\\d+ table_name`, and `information_schema` queries. For application diagnosis, first inspect the relevant job/status/error rows, then correlate them with application or worker logs.
