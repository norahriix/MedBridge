
import os
import sqlite3
import hashlib
import secrets
import hmac
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent / "users.db"


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)

    hashed = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt,
        200000
    )

    return salt.hex(), hashed.hex()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)

        identity = os.getenv("MEDBRIDGE_ADMIN_ID")
        password = os.getenv("MEDBRIDGE_ADMIN_PASSWORD")

        if identity and password:
            user = db.execute(
                "SELECT id FROM users WHERE id = ?",
                (identity,)
            ).fetchone()

            if user is None:
                salt, password_hash_value = hash_password(password)

                db.execute(
                    "INSERT INTO users VALUES (?, ?, ?)",
                    (identity, salt, password_hash_value)
                )


def verify_user(identity, password):
    with sqlite3.connect(DB_PATH) as db:
        user = db.execute(
            "SELECT salt, password_hash FROM users WHERE id = ?",
            (identity,)
        ).fetchone()

    if user is None:
        return False

    salt = bytes.fromhex(user[0])
    _, entered_hash = hash_password(password, salt)

    return hmac.compare_digest(entered_hash, user[1])
