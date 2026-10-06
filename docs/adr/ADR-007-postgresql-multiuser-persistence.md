# ADR-007 — Microsoft SQL Server for V2/V3 multi-user persistence

## Context
The V1 report did not define a relational database. The multi-user product requirement requires durable, consistent persistence across developers, operators and AI agents. In the operational environment, Microsoft SQL Server (MSSQL) is the primary relational database platform available on Windows host environments, with native ODBC Driver 17/18 support.

## Decision
Use **Microsoft SQL Server (MSSQL)** as the canonical operational persistence and **Alembic** as the schema-change mechanism via `mssql+pyodbc`.
- Supports both local Windows Authentication (`Trusted_Connection=yes`) and SQL Server Authentication (`sa`).
- Docker Compose provides an optional containerized SQL Server 2022 service (`mcr.microsoft.com/mssql/server:2022-latest`).
- Database migration gate `0002_v3_jev_ai_audit` runs before backend startup.

## Alternatives Considered
- PostgreSQL: Originally proposed; superseded by Microsoft SQL Server to align with host environment capabilities without requiring additional DB engine installations.
- MySQL: Available on host, but SQL Server was selected for superior native Windows integration, enterprise T-SQL features, `uniqueidentifier` UUID support, and robust snapshot isolation.
- SQLite/local file: Rejected for multi-user concurrency and schema drift risk.
- Vector DB: Rejected; X-SENTINEL is not a vector-search/embedding product.

## Advantages
- Native Windows service integration with Windows Authentication (zero password management for local dev).
- Strong transactional guarantees (ACID), enterprise-grade reliability, native JSON validation functions (`ISJSON`, `JSON_VALUE`).
- Alembic migration compatibility with custom DDL types.

## Disadvantages
- Requires ODBC Driver 17/18 for SQL Server and `pyodbc` package.
- T-SQL syntax differences for boolean (`BIT`) and JSON columns (`NVARCHAR(MAX)`).

## Consequences
All database models, migrations, connection configs, and backup/restore scripts use Microsoft SQL Server conventions.
