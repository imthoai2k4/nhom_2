"""
tools/backup_db.py — Backup/restore SQLite an toàn.

Cách dùng:
  python tools/backup_db.py backup
  python tools/backup_db.py backup --dir backups
  python tools/backup_db.py restore backups/utility_mgmt_20261028_220000.db --yes

Backup dùng sqlite3 backup API để không copy file đang ghi dở (WAL-safe).
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "utility_mgmt.db"
DEFAULT_BACKUP_DIR = ROOT / "backups"


def backup_db(backup_dir: Path) -> Path:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Không tìm thấy DB: {DB_PATH}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / f"utility_mgmt_{datetime.now():%Y%m%d_%H%M%S}.db"

    source = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
    dest = sqlite3.connect(target)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    return target


def restore_db(source_path: Path, yes: bool) -> None:
    if not source_path.exists():
        raise FileNotFoundError(f"Không tìm thấy file backup: {source_path}")
    if not yes:
        raise SystemExit("Cần thêm --yes để xác nhận ghi đè DB hiện tại.")

    safety = DB_PATH.with_name(f"utility_mgmt_before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
    if DB_PATH.exists():
        # Backup DB hiện tại trước khi restore
        source = sqlite3.connect(f"file:{DB_PATH.as_posix()}?mode=ro", uri=True)
        dest = sqlite3.connect(safety)
        try:
            source.backup(dest)
        finally:
            dest.close()
            source.close()

    source = sqlite3.connect(source_path)
    dest = sqlite3.connect(DB_PATH)
    try:
        source.backup(dest)
    finally:
        dest.close()
        source.close()

    print(f"Đã restore từ {source_path}")
    print(f"Bản an toàn của DB cũ: {safety}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Backup/restore SQLite cho UtilityAI")
    parser.add_argument("action", choices=["backup", "restore"])
    parser.add_argument("path", nargs="?", help="File backup khi restore")
    parser.add_argument("--dir", default=str(DEFAULT_BACKUP_DIR), help="Thư mục backup")
    parser.add_argument("--yes", action="store_true", help="Xác nhận restore")
    args = parser.parse_args()

    if args.action == "backup":
        target = backup_db(Path(args.dir))
        print(f"Đã backup: {target}")
        return 0

    if not args.path:
        parser.error("restore cần đường dẫn file backup")
    restore_db(Path(args.path), args.yes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
