"""Create a timestamped official mongodump archive without printing credentials."""

import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402


def main() -> int:
    executable = shutil.which("mongodump")
    if not executable:
        print("BLOCKED mongodump is not installed or not on PATH.")
        return 1
    output = Path("backups") / f"dhakanest-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.archive.gz"
    output.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run([
        executable, f"--uri={settings.mongo_uri}", f"--db={settings.database_name}",
        f"--archive={output}", "--gzip",
    ], check=False)
    if result.returncode:
        print("BLOCKED MongoDB backup failed; credentials were not displayed.")
        return result.returncode
    print(f"PASS Backup created at {output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
