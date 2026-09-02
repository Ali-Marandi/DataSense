"""Local column encryption helpers for DataSense.

The helper intentionally returns a new DataFrame so callers can place the operation
through DataManager.set_frame() and preserve undo/redo and lineage semantics.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken
import pandas as pd


class DataSecurity:
    """Encrypt/decrypt individual dataframe columns with a caller-supplied Fernet key."""

    def __init__(self, key: bytes | str | None = None) -> None:
        if key is None:
            self.key = Fernet.generate_key()
        elif isinstance(key, str):
            self.key = key.encode("utf-8")
        else:
            self.key = key
        self.cipher = Fernet(self.key)

    def encrypt_column(self, df: pd.DataFrame, column_name: str):
        """Return a copy with one column encrypted; never mutate caller-owned data."""
        if column_name not in df.columns:
            return df, f"ستون {column_name} یافت نشد."
        try:
            out = df.copy()
            out[column_name] = out[column_name].map(
                lambda value: self.cipher.encrypt(str(value).encode("utf-8")).decode("utf-8")
            )
            return out, None
        except Exception as exc:
            return df, str(exc)

    def decrypt_column(self, df: pd.DataFrame, column_name: str):
        """Return a copy with one column decrypted; invalid tokens fail closed."""
        if column_name not in df.columns:
            return df, f"ستون {column_name} یافت نشد."
        try:
            out = df.copy()
            out[column_name] = out[column_name].map(
                lambda value: self.cipher.decrypt(str(value).encode("utf-8")).decode("utf-8")
            )
            return out, None
        except InvalidToken:
            return df, "رمزگشایی ناموفق است: کلید یا داده معتبر نیست."
        except Exception as exc:
            return df, str(exc)

    def get_key(self) -> str:
        """Return the Fernet key for explicit caller-managed secure persistence."""
        return self.key.decode("utf-8")
