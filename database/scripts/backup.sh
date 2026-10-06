#!/usr/bin/env bash
set -euo pipefail
mkdir -p artifacts/backups
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
out="artifacts/backups/xsentinel_${stamp}.bak"
db="${MSSQL_DB:-xsentinel}"
echo "Backing up SQL Server database ${db} to ${out}..."
if command -v sqlcmd >/dev/null 2>&1; then
  sqlcmd -S localhost -E -Q "BACKUP DATABASE [${db}] TO DISK = N'$(pwd)/${out}' WITH INIT, STATS = 10"
else
  python -c "
import os, pyodbc
url = os.getenv('XS_DATABASE_URL', 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;Trusted_Connection=yes')
conn = pyodbc.connect(url if 'DRIVER=' in url else 'DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;Trusted_Connection=yes', autocommit=True)
cur = conn.cursor()
bak_path = os.path.abspath('${out}').replace('\\\\', '/')
cur.execute(f\"BACKUP DATABASE [${db}] TO DISK = N'{bak_path}' WITH INIT, STATS = 10\")
conn.close()
"
fi
sha256sum "$out" > "${out}.sha256"
echo "Backup created: $out"
