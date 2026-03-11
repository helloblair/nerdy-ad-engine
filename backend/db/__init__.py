"""
db/__init__.py
--------------
Factory module. Call get_db() to get the active database backend.
Controlled by DB_BACKEND env var: "sqlite" (default) or "supabase".
"""

import os
from db.interface import DatabaseInterface

_instance: DatabaseInterface | None = None


def get_db() -> DatabaseInterface:
    global _instance
    if _instance is not None:
        return _instance

    backend = os.getenv("DB_BACKEND", "sqlite").lower()

    if backend == "supabase":
        from db.supabase_db import SupabaseDatabase
        _instance = SupabaseDatabase()
    else:
        from db.sqlite_db import SQLiteDatabase
        _instance = SQLiteDatabase()

    return _instance
