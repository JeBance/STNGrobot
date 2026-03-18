"""Script to run migrations."""
import subprocess
import sys


def run_alembic(command: str):
    """Run alembic command."""
    result = subprocess.run(["alembic", command], check=True)
    return result.returncode


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_migrations.py <command>")
        print("Commands: upgrade, downgrade, current, history, heads, stamp")
        sys.exit(1)

    command = sys.argv[1]
    if command == "upgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "head"
        run_alembic(f"upgrade {revision}")
    elif command == "downgrade":
        revision = sys.argv[2] if len(sys.argv) > 2 else "-1"
        run_alembic(f"downgrade {revision}")
    else:
        run_alembic(command)
