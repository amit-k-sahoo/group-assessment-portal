"""SQLite storage for ratings. One row per (reviewer, group, parameter); re-rating overwrites."""

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(os.environ.get("REVIEW_PORTAL_DB", Path(__file__).resolve().parent / "data" / "ratings.db"))

PARAMETERS = {
    "ideation": "Ideation",
    "features": "Features",
    "look_feel": "Look and feel",
    "governance": "Governance",
    "presentation": "Presentation",
}
GROUPS = list(range(1, 11))


@contextmanager
def conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    try:
        c.execute(
            """CREATE TABLE IF NOT EXISTS ratings (
                   reviewer_email TEXT NOT NULL,
                   reviewer_name  TEXT,
                   group_no       INTEGER NOT NULL CHECK (group_no BETWEEN 1 AND 10),
                   parameter      TEXT NOT NULL,
                   score          INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
                   updated_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                   PRIMARY KEY (reviewer_email, group_no, parameter))"""
        )
        c.execute(
            """CREATE TABLE IF NOT EXISTS users (
                   login_id    TEXT PRIMARY KEY,
                   full_name   TEXT NOT NULL,
                   salt        TEXT NOT NULL,
                   pw_hash     TEXT NOT NULL,
                   iterations  INTEGER NOT NULL,
                   failed      INTEGER NOT NULL DEFAULT 0,
                   locked_until REAL NOT NULL DEFAULT 0,
                   created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"""
        )
        yield c
        c.commit()
    finally:
        c.close()


def my_scores(email: str, group_no: int) -> dict:
    with conn() as c:
        rows = c.execute(
            "SELECT parameter, score FROM ratings WHERE reviewer_email=? AND group_no=?",
            (email, group_no),
        ).fetchall()
    return dict(rows)


def save_scores(email: str, name: str, group_no: int, scores: dict) -> None:
    with conn() as c:
        for param, score in scores.items():
            if param not in PARAMETERS or not 1 <= int(score) <= 5:
                raise ValueError("invalid rating")
            c.execute(
                """INSERT INTO ratings (reviewer_email, reviewer_name, group_no, parameter, score)
                   VALUES (?,?,?,?,?)
                   ON CONFLICT(reviewer_email, group_no, parameter)
                   DO UPDATE SET score=excluded.score, reviewer_name=excluded.reviewer_name,
                                 updated_at=CURRENT_TIMESTAMP""",
                (email, name, group_no, param, int(score)),
            )


def rated_groups(email: str) -> set:
    with conn() as c:
        rows = c.execute(
            "SELECT group_no FROM ratings WHERE reviewer_email=? GROUP BY group_no HAVING COUNT(*)=?",
            (email, len(PARAMETERS)),
        ).fetchall()
    return {r[0] for r in rows}


def all_ratings():
    with conn() as c:
        return c.execute(
            "SELECT reviewer_email, reviewer_name, group_no, parameter, score, updated_at FROM ratings"
        ).fetchall()


# ---- password accounts (for people who don't use Google) --------------------------------
ITERATIONS = 600_000
MIN_PASSWORD = 8
LOGIN_RE = re.compile(r"^[A-Za-z0-9._@+-]{3,60}$")
MAX_FAILS, LOCK_SECONDS = 5, 600


class AuthError(Exception):
    """Message is safe to show the user."""


def _hash(password: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations).hex()


def create_user(login_id: str, full_name: str, password: str) -> dict:
    login_id, full_name = login_id.strip().lower(), " ".join(full_name.split())
    if len(full_name) < 2:
        raise AuthError("Please enter your full name.")
    if not LOGIN_RE.match(login_id):
        raise AuthError("Login ID must be 3–60 characters: letters, numbers and . _ @ + -")
    if len(password) < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")
    salt = secrets.token_bytes(16)
    with conn() as c:
        try:
            c.execute(
                "INSERT INTO users (login_id, full_name, salt, pw_hash, iterations) VALUES (?,?,?,?,?)",
                (login_id, full_name, salt.hex(), _hash(password, salt, ITERATIONS), ITERATIONS),
            )
        except sqlite3.IntegrityError:
            raise AuthError("That Login ID is already taken.") from None
    return {"id": login_id, "name": full_name}


def authenticate(login_id: str, password: str) -> dict:
    import time
    login_id = login_id.strip().lower()
    generic = AuthError("Wrong Login ID or password.")
    with conn() as c:
        row = c.execute(
            "SELECT full_name, salt, pw_hash, iterations, failed, locked_until FROM users WHERE login_id=?",
            (login_id,),
        ).fetchone()
        if row is None:
            _hash(password, b"\0" * 16, ITERATIONS)  # keep timing similar
            raise generic
        name, salt, pw_hash, iters, failed, locked_until = row
        if locked_until > time.time():
            raise AuthError("Too many failed attempts. Try again in a few minutes.")
        if hmac.compare_digest(_hash(password, bytes.fromhex(salt), iters), pw_hash):
            c.execute("UPDATE users SET failed=0, locked_until=0 WHERE login_id=?", (login_id,))
            return {"id": login_id, "name": name}
        failed += 1
        c.execute(
            "UPDATE users SET failed=?, locked_until=? WHERE login_id=?",
            (0 if failed >= MAX_FAILS else failed,
             time.time() + LOCK_SECONDS if failed >= MAX_FAILS else 0, login_id),
        )
    raise generic
