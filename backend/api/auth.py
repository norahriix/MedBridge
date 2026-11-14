
import os
import json
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
        password.encode("utf-8"),
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
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'reviewer'
            )
        """)

        columns = {
            row[1]
            for row in db.execute("PRAGMA table_info(users)")
        }

        if "role" not in columns:
            db.execute("""
                ALTER TABLE users
                ADD COLUMN role TEXT NOT NULL DEFAULT 'reviewer'
            """)

        admin_id = os.getenv("MEDBRIDGE_ADMIN_ID")
        admin_password = os.getenv("MEDBRIDGE_ADMIN_PASSWORD")

        if admin_id and admin_password:
            create_user(
                admin_id,
                admin_password,
                role="admin",
                db=db
            )

        # Controlled reviewer accounts:
        # MEDBRIDGE_REVIEWERS='{"judge1":"password1","judge2":"password2"}'
        reviewers_json = os.getenv("MEDBRIDGE_REVIEWERS", "{}")

        try:
            reviewers = json.loads(reviewers_json)
        except json.JSONDecodeError:
            raise RuntimeError(
                "MEDBRIDGE_REVIEWERS must contain valid JSON"
            )

        if not isinstance(reviewers, dict):
            raise RuntimeError(
                "MEDBRIDGE_REVIEWERS must be a JSON object"
            )

        for identity, password in reviewers.items():
            create_user(
                identity,
                password,
                role="reviewer",
                db=db
            )


def create_user(identity, password, role="reviewer", db=None):
    identity = str(identity).strip()
    password = str(password)

    if not identity or len(password) < 12:
        raise ValueError(
            "User identity is required and password must be at least 12 characters"
        )

    if role not in ("admin", "reviewer"):
        raise ValueError("Invalid user role")

    salt, password_hash_value = hash_password(password)

    if db is not None:
        db.execute("""
            INSERT INTO users (id, salt, password_hash, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                salt = excluded.salt,
                password_hash = excluded.password_hash,
                role = excluded.role
        """, (
            identity,
            salt,
            password_hash_value,
            role
        ))
        return

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("""
            INSERT INTO users (id, salt, password_hash, role)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                salt = excluded.salt,
                password_hash = excluded.password_hash,
                role = excluded.role
        """, (
            identity,
            salt,
            password_hash_value,
            role
        ))


def verify_user(identity, password):
    with sqlite3.connect(DB_PATH) as db:
        user = db.execute("""
            SELECT salt, password_hash
            FROM users
            WHERE id = ?
        """, (identity,)).fetchone()

    if user is None:
        return False

    salt = bytes.fromhex(user[0])
    _, entered_hash = hash_password(password, salt)

    return hmac.compare_digest(entered_hash, user[1])


def get_user_role(identity):
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute("""
            SELECT role
            FROM users
            WHERE id = ?
        """, (identity,)).fetchone()

    return row[0] if row else None
