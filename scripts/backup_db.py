"""Database backup utility for PetCare 360 PostgreSQL databases.

Usage:
    python scripts/backup_db.py [--output DIR]
"""
import argparse
import os
import subprocess
import sys
from datetime import datetime
from urllib.parse import urlparse


def backup_database(output_dir="backups"):
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    parsed = urlparse(database_url)
    if parsed.scheme.startswith("sqlite"):
        print("Notice: SQLite detected. Use direct file copy of sqlite db file.", file=sys.stderr)
        return

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(output_dir, f"petcare360_backup_{timestamp}.sql")

    env = os.environ.copy()
    if parsed.password:
        env["PGPASSWORD"] = parsed.password

    cmd = [
        "pg_dump",
        "-h", parsed.hostname or "localhost",
        "-p", str(parsed.port or 5432),
        "-U", parsed.username or "postgres",
        "-d", parsed.path.lstrip("/"),
        "-F", "c",  # Custom archive format for pg_restore
        "-f", backup_file,
    ]

    print(f"Starting database backup to {backup_file}...")
    try:
        subprocess.run(cmd, env=env, check=True)
        print(f"Backup successfully generated: {backup_file} ({os.path.getsize(backup_file)} bytes)")
    except FileNotFoundError:
        print("ERROR: pg_dump utility not found in system PATH.", file=sys.stderr)
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Backup failed with exit code {e.returncode}.", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Backup PetCare 360 database")
    parser.add_argument("--output", default="backups", help="Target backup folder")
    args = parser.parse_args()
    backup_database(args.output)

