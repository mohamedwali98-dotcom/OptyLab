"""
auth.py
=======
Self-contained authentication + authorization for the OptyLab dashboard.

Design goals (no new pip dependencies — stdlib only):
  * User accounts with email + password, stored safely (PBKDF2-HMAC-SHA256).
  * A DB of "allowed admin emails". The Admin tab is only visible/usable
    for emails that have been granted access here (the "sheet" page).
  * JWT-style bearer tokens signed with HS256 (implemented from scratch so
    we don't need PyJWT). Tokens are stateless and expire.
  * A per-user login/activity history (kept to the most recent 20 entries).

Tables (SQLite, file: auth.db next to this module):
  users           — id, email (unique), name, pw_hash, created_at
  admin_access    — email (unique, lowercase), granted_by, granted_at
  login_history   — id, user_id, email, ts, ip, action
"""

import os
import re
import json
import hmac
import time
import hashlib
import sqlite3
import secrets
import base64
from pathlib import Path
from datetime import datetime, timezone

from fastapi import Request

# ── Paths / constants ─────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
DB_PATH  = BASE_DIR / "auth.db"

PBKDF2_ITERATIONS = 200_000
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days

# JWT secret: prefer OPTYLAB_JWT_SECRET env; otherwise persist a random one
# to .jwt_secret so issued tokens survive server restarts.
_SECRET_FILE = BASE_DIR / ".jwt_secret"

def _load_secret() -> bytes:
    env = os.environ.get("OPTYLAB_JWT_SECRET")
    if env:
        return env.encode("utf-8")
    if _SECRET_FILE.exists():
        return _SECRET_FILE.read_bytes()
    secret = secrets.token_bytes(48)
    _SECRET_FILE.write_bytes(secret)
    try:
        _SECRET_FILE.chmod(0o600)
    except Exception:
        pass
    return secret

JWT_SECRET = _load_secret()


# ── DB bootstrap ───────────────────────────────────────────────────────────────
def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Create tables if missing. Idempotent."""
    with _connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL UNIQUE COLLATE NOCASE,
                name       TEXT NOT NULL,
                pw_hash    TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS admin_access (
                email      TEXT PRIMARY KEY COLLATE NOCASE,
                granted_by TEXT NOT NULL,
                granted_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS login_history (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL,
                email    TEXT NOT NULL COLLATE NOCASE,
                ts       TEXT NOT NULL,
                ip       TEXT,
                action   TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_login_user ON login_history(user_id, id DESC);

            CREATE TABLE IF NOT EXISTS processed_images (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                email       TEXT NOT NULL COLLATE NOCASE,
                filename    TEXT NOT NULL,
                prediction  TEXT NOT NULL,
                confidence  REAL,
                ts          TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_processed_user ON processed_images(user_id, id DESC);
            """
        )


# ── Password hashing (PBKDF2-HMAC-SHA256) ───────────────────────────────────────
def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iter_s, salt_hex, hash_hex = stored.split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iter_s)
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except Exception:
        return False


# ── Minimal HS256 JWT (header.payload.signature, base64url) ─────────────────────
def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _sign(header_b64: str, payload_b64: str) -> str:
    msg = f"{header_b64}.{payload_b64}".encode("ascii")
    sig = hmac.new(JWT_SECRET, msg, hashlib.sha256).digest()
    return _b64url(sig)


def create_token(user_id: int, email: str) -> str:
    header = _b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
    now = int(time.time())
    payload = _b64url(
        json.dumps(
            {"sub": user_id, "email": email, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
        ).encode("utf-8")
    )
    sig = _sign(header, payload)
    return f"{header}.{payload}.{sig}"


def verify_token(token: str):
    """Return the decoded payload dict if valid, else None."""
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
    except ValueError:
        return None
    expected = _sign(header_b64, payload_b64)
    if not hmac.compare_digest(expected, sig_b64):
        return None
    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except Exception:
        return None
    if payload.get("exp", 0) < int(time.time()):
        return None
    return payload


# ── User / access operations ───────────────────────────────────────────────────
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def normalize_email(email: str) -> str:
    return email.strip().lower()


def email_valid(email: str) -> bool:
    return bool(EMAIL_RE.match(email))


def create_user(email: str, name: str, password: str) -> dict:
    """Insert a new user. Raises ValueError on bad input / duplicate email."""
    email = normalize_email(email)
    if not email_valid(email):
        raise ValueError("Invalid email address.")
    if not name or not name.strip():
        raise ValueError("Name is required.")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters.")
    with _connect() as conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (email, name, pw_hash, created_at) VALUES (?, ?, ?, ?)",
                (email, name.strip(), hash_password(password), datetime.now(timezone.utc).isoformat()),
            )
            uid = cur.lastrowid
        except sqlite3.IntegrityError:
            raise ValueError("An account with this email already exists.")
        return {"id": uid, "email": email, "name": name.strip()}


def authenticate(email: str, password: str) -> dict | None:
    email = normalize_email(email)
    with _connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    if not row:
        return None
    if not verify_password(password, row["pw_hash"]):
        return None
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


def get_user_by_id(user_id: int) -> dict | None:
    with _connect() as conn:
        row = conn.execute(
            "SELECT id, email, name, created_at FROM users WHERE id = ?", (user_id,)
        ).fetchone()
    if not row:
        return None
    return dict(row)


def change_password(user_id: int, old_password: str, new_password: str) -> None:
    if not new_password or len(new_password) < 6:
        raise ValueError("New password must be at least 6 characters.")
    with _connect() as conn:
        row = conn.execute("SELECT pw_hash FROM users WHERE id = ?", (user_id,)).fetchone()
        if not row:
            raise ValueError("User not found.")
        if not verify_password(old_password, row["pw_hash"]):
            raise ValueError("Current password is incorrect.")
        new_hash = hash_password(new_password)
        conn.execute("UPDATE users SET pw_hash = ? WHERE id = ?", (new_hash, user_id))


# ── Admin-access list ("the sheet") ────────────────────────────────────────────
def is_admin_allowed(email: str) -> bool:
    email = normalize_email(email)
    with _connect() as conn:
        row = conn.execute(
            "SELECT email FROM admin_access WHERE email = ?", (email,)
        ).fetchone()
    return row is not None


def list_admin_access() -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT email, granted_by, granted_at FROM admin_access ORDER BY granted_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def grant_admin_access(email: str, granted_by: str) -> dict:
    email = normalize_email(email)
    if not email_valid(email):
        raise ValueError("Invalid email address.")
    with _connect() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO admin_access (email, granted_by, granted_at) VALUES (?, ?, ?)",
            (email, granted_by, datetime.now(timezone.utc).isoformat()),
        )
    return {"email": email, "granted_by": granted_by}


def revoke_admin_access(email: str) -> None:
    email = normalize_email(email)
    with _connect() as conn:
        conn.execute("DELETE FROM admin_access WHERE email = ?", (email,))


# ── Login / activity history (last 20) ─────────────────────────────────────────
def record_login(user_id: int, email: str, ip: str | None, action: str = "login") -> None:
    email = normalize_email(email)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO login_history (user_id, email, ts, ip, action) VALUES (?, ?, ?, ?, ?)",
            (user_id, email, datetime.now(timezone.utc).isoformat(), ip, action),
        )
        # Keep only the most recent 20 entries per user.
        conn.execute(
            """
            DELETE FROM login_history
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM login_history WHERE user_id = ? ORDER BY id DESC LIMIT 20
            )
            """,
            (user_id, user_id),
        )


def get_history(user_id: int, limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT ts, ip, action FROM login_history "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Processed images (attributed to the user who ran classification) ──────────
def record_process(user_id: int, email: str, filename: str, prediction: str,
                   confidence: float | None, ts: str) -> None:
    email = normalize_email(email)
    with _connect() as conn:
        conn.execute(
            "INSERT INTO processed_images "
            "(user_id, email, filename, prediction, confidence, ts) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, email, filename, prediction, confidence, ts),
        )
        # Keep only the most recent 50 entries per user (headroom over the 20 shown).
        conn.execute(
            """
            DELETE FROM processed_images
            WHERE user_id = ? AND id NOT IN (
                SELECT id FROM processed_images WHERE user_id = ? ORDER BY id DESC LIMIT 50
            )
            """,
            (user_id, user_id),
        )


def get_processed(user_id: int, limit: int = 20) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT filename, prediction, confidence, ts FROM processed_images "
            "WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


# ── Request helpers ─────────────────────────────────────────────────────────────
def client_ip(request: Request) -> str | None:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        # Take the first hop.
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


def bearer_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def current_user(request: Request) -> dict | None:
    """Return the user dict for the bearer token in the request, or None."""
    token = bearer_token(request)
    if not token:
        return None
    payload = verify_token(token)
    if not payload:
        return None
    return get_user_by_id(payload.get("sub"))
