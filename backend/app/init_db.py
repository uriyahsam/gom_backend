from pathlib import Path
from .db import connect
from .settings import settings

def init_db():
    db_path = Path(settings.DATABASE_PATH)
    if not db_path.exists():
        db_path.touch()

    conn = connect()
    try:
        schema = Path(__file__).resolve().parent.parent / "db" / "schema.sql"
        seed = Path(__file__).resolve().parent.parent / "db" / "seed.sql"
        conn.executescript(schema.read_text(encoding="utf-8"))
        conn.executescript(seed.read_text(encoding="utf-8"))

        # Seed admins from env (comma-separated telegram IDs)
        if settings.ADMIN_TELEGRAM_IDS.strip():
            for part in settings.ADMIN_TELEGRAM_IDS.split(","):
                part = part.strip()
                if part.isdigit():
                    conn.execute("INSERT OR IGNORE INTO admins(telegram_id) VALUES(?)", (int(part),))

        conn.commit()
    finally:
        conn.close()
