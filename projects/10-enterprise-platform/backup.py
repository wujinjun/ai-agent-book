"""Create a transactionally consistent backup of the local SQLite platform database."""

import os
from pathlib import Path

from ai_agent_book.apps.enterprise_platform import EnterprisePlatform

if __name__ == "__main__":
    source = Path(os.getenv("DATABASE_PATH", ".data/enterprise-platform.db"))
    destination = Path(os.getenv("BACKUP_PATH", ".data/backups/enterprise-platform.db"))
    platform = EnterprisePlatform(source)
    print(platform.backup_sqlite(destination))
