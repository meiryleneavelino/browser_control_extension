import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "database.db")

# ── Permissões disponíveis ───────────────────────────────────────────────────
VALID_PERMISSIONS = {"read", "write", "update", "delete", "export", "admin"}


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            permissions TEXT    NOT NULL DEFAULT '',
            is_auditor  INTEGER NOT NULL DEFAULT 0,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


# ── Usuários ─────────────────────────────────────────────────────────────────
def create_user(name: str, email: str, password: str, permissions: list, is_auditor: bool = False) -> dict:
    perms = [p for p in permissions if p in VALID_PERMISSIONS]
    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (name, email, password, permissions, is_auditor) VALUES (?, ?, ?, ?, ?)",
            (name, email, hash_password(password), ",".join(perms), int(is_auditor))
        )
        conn.commit()
        return {"ok": True}
    except sqlite3.IntegrityError:
        return {"ok": False, "error": "E-mail já cadastrado"}
    finally:
        conn.close()


def get_user_by_email(email: str) -> dict | None:
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if not row:
        return None
    user = dict(row)
    user["permissions"] = user["permissions"].split(",") if user["permissions"] else []
    user["is_auditor"] = bool(user["is_auditor"])
    return user


def get_all_users() -> list:
    conn = get_db()
    rows = conn.execute("SELECT id, name, email, permissions, is_auditor, created_at FROM users").fetchall()
    conn.close()
    users = []
    for row in rows:
        u = dict(row)
        u["permissions"] = u["permissions"].split(",") if u["permissions"] else []
        u["is_auditor"] = bool(u["is_auditor"])
        users.append(u)
    return users
