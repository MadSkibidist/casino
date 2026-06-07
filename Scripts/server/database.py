import sqlite3
import hashlib
import os
import time


class CasinoDatabase:
    def __init__(self, db_name: str = "casino.db",
                 pepper: str = "SuperSecretCasinoPepper123!"):
        self.db_name = db_name
        self.pepper  = pepper
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username      TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    salt          TEXT NOT NULL,
                    email         TEXT,
                    otp_code      TEXT,
                    otp_expiry    REAL,
                    is_verified   INTEGER DEFAULT 0,
                    balance       INTEGER DEFAULT 5000
                )
            """)
            conn.commit()

    def _hash(self, password: str, salt: str) -> str:
        raw = password + salt + self.pepper
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def IsUserExist(self, username: str) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            row = conn.execute(
                "SELECT is_verified FROM users WHERE username = ?", (username,)
            ).fetchone()
            return row is not None and row[0] == 1

    def CheckPendingUser(self, username: str, email: str):
        with sqlite3.connect(self.db_name) as conn:
            return conn.execute(
                """SELECT username, otp_expiry, is_verified
                   FROM users WHERE username = ? OR email = ?""",
                (username, email)
            ).fetchone()

    def DeleteUser(self, username: str):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute("DELETE FROM users WHERE username = ?", (username,))
            conn.commit()

    def SaveUser(self, username: str, password: str, email: str,
                 otp_code: str, otp_expiry: float):
        salt = os.urandom(16).hex()
        ph   = self._hash(password, salt)
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                """INSERT INTO users
                   (username, password_hash, salt, email,
                    otp_code, otp_expiry, is_verified, balance)
                   VALUES (?, ?, ?, ?, ?, ?, 0, 5000)""",
                (username, ph, salt, email, otp_code, otp_expiry)
            )
            conn.commit()

    def IsPasswordOK(self, username: str, password: str) -> bool:
        with sqlite3.connect(self.db_name) as conn:
            row = conn.execute(
                "SELECT password_hash, salt, is_verified FROM users WHERE username = ?",
                (username,)
            ).fetchone()
        if not row or row[2] == 0:
            return False
        return self._hash(password, row[1]) == row[0]

    def GetUserEmail(self, username: str) -> str | None:
        with sqlite3.connect(self.db_name) as conn:
            row = conn.execute(
                "SELECT email FROM users WHERE username = ?", (username,)
            ).fetchone()
            return row[0] if row else None

    def UpdateOTP(self, username: str, otp_code: str, otp_expiry: float):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "UPDATE users SET otp_code = ?, otp_expiry = ? WHERE username = ?",
                (otp_code, otp_expiry, username)
            )
            conn.commit()

    def GetOTPInfo(self, username: str):
        with sqlite3.connect(self.db_name) as conn:
            return conn.execute(
                "SELECT otp_code, otp_expiry FROM users WHERE username = ?",
                (username,)
            ).fetchone()

    def SetUserVerified(self, username: str):
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "UPDATE users SET is_verified = 1 WHERE username = ?", (username,)
            )
            conn.commit()

    def UpdatePassword(self, username: str, new_password: str):
        salt = os.urandom(16).hex()
        ph   = self._hash(new_password, salt)
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                (ph, salt, username)
            )
            conn.commit()

    def GetBalance(self, username: str) -> int:
        with sqlite3.connect(self.db_name) as conn:
            row = conn.execute(
                "SELECT balance FROM users WHERE username = ?", (username,)
            ).fetchone()
            return row[0] if row else 5000

    def UpdateBalance(self, username: str, delta: int) -> int:
        with sqlite3.connect(self.db_name) as conn:
            conn.execute(
                "UPDATE users SET balance = MAX(0, balance + ?) WHERE username = ?",
                (delta, username)
            )
            conn.commit()
            row = conn.execute(
                "SELECT balance FROM users WHERE username = ?", (username,)
            ).fetchone()
            return row[0] if row else 0