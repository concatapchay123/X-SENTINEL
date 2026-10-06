#!/usr/bin/env bash
set -euo pipefail
if [[ $# -ne 1 ]]; then echo "usage: $0 <backup.bak>" >&2; exit 2; fi
backup="$1"
test -f "$backup"
db="${MSSQL_DB:-xsentinel}"
echo "RESTORE IS DESTRUCTIVE. Target DB: ${db}" >&2
if [[ "${XS_ALLOW_RESTORE:-false}" != "true" ]]; then
  echo "Set XS_ALLOW_RESTORE=true only after verifying target/backup." >&2
  exit 3
fi
if command -v sqlcmd >/dev/null 2>&1; then
  sqlcmd -S localhost -E -Q "ALTER DATABASE [${db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE; RESTORE DATABASE [${db}] FROM DISK = N'$(pwd)/${backup}' WITH REPLACE; ALTER DATABASE [${db}] SET MULTI_USER;"
else
  python -c "
import os, pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=master;Trusted_Connection=yes', autocommit=True)
cur = conn.cursor()
bak_path = os.path.abspath('${backup}').replace('\\\\', '/')
cur.execute(\"ALTER DATABASE [${db}] SET SINGLE_USER WITH ROLLBACK IMMEDIATE\")
cur.execute(f\"RESTORE DATABASE [${db}] FROM DISK = N'{bak_path}' WITH REPLACE\")
cur.execute(\"ALTER DATABASE [${db}] SET MULTI_USER\")
conn.close()
"
fi
echo "Restore completed for ${db}."
